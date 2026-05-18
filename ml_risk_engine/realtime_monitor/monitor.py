import asyncio
import json
import os
import sys
import websockets
import logging
from datetime import datetime
from predictor.predictor import RiskPredictor
from realtime_monitor.correlation import CorrelationEngine

logger = logging.getLogger("RiskMonitor")
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

class RealTimeMonitor:
    def __init__(self, backend_ws_url="ws://localhost:8765"):
        self.backend_url = backend_ws_url
        logger.info("RealTimeMonitor: Initializing RiskPredictor...")
        self.predictor = RiskPredictor()
        logger.info(f"RealTimeMonitor: RiskPredictor initialized. is_mock={self.predictor.is_mock}")
        self.correlation_engine = CorrelationEngine()
        
        # Async queue to buffer predictions for the FastAPI streamer
        self.prediction_queue = asyncio.Queue(maxsize=1000)
        
        # Keep track of recent predictions to serve via API polling
        self.recent_predictions = []
        
        # Track last processed time per session to avoid CPU hogging
        self.last_processed = {}
        
        # File logging — use absolute path next to exe (or repo root in dev)
        if getattr(sys, 'frozen', False):
            _base = os.path.dirname(sys.executable)
        else:
            _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _log_dir = os.path.join(_base, "logs")
        os.makedirs(_log_dir, exist_ok=True)
        self.log_file = os.path.join(_log_dir, "predictions.log")
        # Configurable minimum packet threshold before ML evaluates a session
        try:
            # Default minimal threshold lowered so portscans and small flows are evaluated
                # Use very low default so port-scans and short flows are evaluated during normal capture
                self.min_packet_threshold = int(os.getenv("ML_MIN_PKT_THRESHOLD", "1"))
        except Exception:
                self.min_packet_threshold = 1
        logger.info(f"ML min packet threshold: {self.min_packet_threshold}")
        
    async def run(self):
        """Main loop connecting to NetSentinel backend WS indefinitely."""
        logger.info(f"Connecting to NetSentinel Capture Engine at {self.backend_url}")
        while True:
            try:
                async with websockets.connect(self.backend_url) as ws:
                    logger.info("Connected to Capture Engine.")
                    await self._listen_loop(ws)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Capture Engine connection lost. Reconnecting in 3s...")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Capture Engine connection error: {e}")
                await asyncio.sleep(3)

    async def _listen_loop(self, ws):
        """Listen to incoming WS messages and filter for 'sessions'."""
        async for raw_msg in ws:
            try:
                msg = json.loads(raw_msg)
                
                if msg.get("type") == "sessions":
                    data = msg.get("data", {})
                    updated = data.get("updated", [])
                    closed = data.get("closed", [])
                    
                    # We predict on all flows that have had recent activity
                    for session in updated + closed:
                        await self._process_session(session)
                        
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    async def _process_session(self, session: dict):
        """Extract features, run ML prediction, run correlation, and broadcast result."""
        import time
        now = time.time()
        session_id = session.get("id")
        
        self.last_processed[session_id] = now
        
        # Cleanup old processed entries periodically to avoid memory leak
        if len(self.last_processed) > 5000:
            cutoff = now - 60
            self.last_processed = {k: v for k, v in self.last_processed.items() if v > cutoff}

        # 1. Minimum packet threshold: skip tiny sessions for ML
        # Also gives time for the session to accumulate meaningful stats before we evaluate.
        if session.get("packet_count", 0) < self.min_packet_threshold:
            logger.debug(f"Skipping session {session.get('id')} - packet count {session.get('packet_count')} below threshold {self.min_packet_threshold}")
            return
            
        # 2. Run ML prediction first so the UI is driven by the trained model.
        logger.debug(f"Processing session {session.get('id')} with {session.get('packet_count')} packets")
        result = self.predictor.predict(session)
        logger.info(f"Session {session.get('id')}: {result.get('prediction')} (risk={result.get('risk_score')})")

        alerts = self.correlation_engine.process_session(session)
        correlation_summary = self._build_correlation_summary(result, alerts)
        
        # Override ML prediction if a high-confidence correlation alert triggered
        final_prediction = result["prediction"]
        final_risk = result["risk_score"]
        final_explanation = result.get("explanation", "No explanation available")
        
        if correlation_summary:
            max_alert_risk = max([a.get("risk_score", 0.0) for a in correlation_summary])
            if max_alert_risk >= 0.9 and str(final_prediction).lower() in {"benign", "0"}:
                final_prediction = correlation_summary[0]["type"]
                final_risk = max_alert_risk
                final_explanation = correlation_summary[0]["explanation"]
            elif max_alert_risk > final_risk:
                final_risk = max_alert_risk
                final_explanation = final_explanation + f" | Also flagged: {correlation_summary[0]['explanation']}"

        # Build enriched payload
        payload = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session.get("id"),
            "src_ip": result["src_ip"],
            "dst_ip": result["dst_ip"],
            "src_port": session.get("src_port"),
            "dst_port": session.get("dst_port"),
            "protocol": session.get("protocol"),
            "packet_count": session.get("packet_count"),
            "bytes": session.get("bytes"),
            "duration": session.get("duration"),
            "prediction": final_prediction,
            "risk_score": final_risk,
            "explanation": final_explanation,
            "correlation_alerts": correlation_summary,
            "is_mock": result["is_mock"]
        }
        
        # 1. Log to file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(payload) + "\n")
            
        # 2. Maintain recent array
        self.recent_predictions.append(payload)
        if len(self.recent_predictions) > 100:
            self.recent_predictions.pop(0)
            
        # 3. Queue for live FastAPI websocket streamers
        # If queue is full, drop the oldest to keep up with real-time
        if self.prediction_queue.full():
            try:
                self.prediction_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        
        await self.prediction_queue.put(payload)

    def _build_correlation_summary(self, result: dict, alerts: list) -> list:
        """Keep rule output as supporting context instead of crowding the ML verdict."""
        if not alerts:
            return []

        filtered = []
        for alert in alerts:
            risk_score = float(alert.get("risk_score", 0.0) or 0.0)
            if risk_score < 0.9:
                continue

            explanation = alert.get("explanation", "")
            alert_type = explanation.split("]", 1)[0].lstrip("[") if explanation else "Rule"
            filtered.append(
                {
                    "type": alert_type,
                    "explanation": explanation,
                    "risk_score": risk_score,
                }
            )

        filtered.sort(key=lambda item: item["risk_score"], reverse=True)
        return filtered[:2]
