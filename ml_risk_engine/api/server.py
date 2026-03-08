import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from realtime_monitor.monitor import RealTimeMonitor

app = FastAPI(title="NetSentinel ML Risk Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global monitor instance
monitor = RealTimeMonitor()

# Connected dashboard clients
connected_clients = set()

@app.on_event("startup")
async def startup_event():
    # Start the monitor loop in the background
    asyncio.create_task(monitor.run())
    # Start the broadcaster
    asyncio.create_task(broadcast_predictions())
    print("NetSentinel ML Engine started. Listening to Capture backend on ws://localhost:8765")

async def broadcast_predictions():
    """Reads from monitor's queue and sends to all connected dashboards."""
    while True:
        # Wait for a new prediction
        payload = await monitor.prediction_queue.get()
        
        # Dead clients collection
        dead_clients = set()
        
        for client in connected_clients:
            try:
                await client.send_json(payload)
            except WebSocketDisconnect:
                dead_clients.add(client)
            except Exception as e:
                print(f"Error sending to client: {e}")
                dead_clients.add(client)
                
        # Cleanup
        for c in dead_clients:
            connected_clients.discard(c)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ML Risk Engine"}

@app.get("/api/model-metrics")
async def get_metrics():
    """Returns training metrics if a model was trained."""
    import sys
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        metrics_path = os.path.join(base_path, "models", "saved", "training_metrics.json")
    else:
        metrics_path = "models/saved/training_metrics.json"

    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            return json.load(f)
    return {"message": "No trained model found. Using heuristic mock."}

@app.get("/api/recent-flows")
async def get_recent_flows():
    """Returns the last 100 predictions for dashboard initialization."""
    return monitor.recent_predictions

@app.post("/api/predict-session")
async def predict_single_session(session: dict):
    """Predict a single manually submitted session dictionary."""
    return monitor.predictor.predict(session)

@app.websocket("/ws/live-flows")
async def websocket_endpoint(websocket: WebSocket):
    """Dashboard connects here to receive live ML predictions."""
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"Dashboard connected. Total dashboards: {len(connected_clients)}")
    
    try:
        # Keep connection open; broadcaster handles sending
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("Dashboard disconnected.")
    finally:
        connected_clients.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    import multiprocessing
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000)
