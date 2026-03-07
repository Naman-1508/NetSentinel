import asyncio
import json
import websockets
import logging
from datetime import datetime
from predictor.predictor import RiskPredictor

logger = logging.getLogger("RiskMonitor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

class RealTimeMonitor:
    def __init__(self, backend_ws_url="ws://localhost:8765"):
        self.backend_url = backend_ws_url
        self.predictor = RiskPredictor()
        
        # Async queue to buffer predictions for the FastAPI streamer
        self.prediction_queue = asyncio.Queue(maxsize=1000)
        
        # Keep track of recent predictions to serve via API polling
        self.recent_predictions = []
        
        # File logging
        self.log_file = "logs/predictions.log"
        import os
        os.makedirs("logs", exist_ok=True)
        
    async def run(self):
        """Main loop connecting to DeepShark backend WS indefinitely."""
        logger.info(f"Connecting to DeepShark Capture Engine at {self.backend_url}")
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
        """Extract features, run ML prediction, and broadcast result."""
        # Minimum packet threshold to avoid predicting on single empty SYN packets
        if session.get("packet_count", 0) < 3:
            return
            
        # Run prediction
        result = self.predictor.predict(session)
        
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
            "prediction": result["prediction"],
            "risk_score": result["risk_score"],
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
