from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import logging

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("New WebSocket connection")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info("WebSocket disconnected")

    async def broadcast(self, message: dict):
        # Convert dictionary to JSON string
        message_json = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logging.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Enforce connection limits
    if len(manager.active_connections) > 100:
        await websocket.close(code=1008, reason="Max connection capacity reached")
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages if any
            data = await websocket.receive_text()
            if len(data) > 65536:
                await websocket.close(code=1009, reason="Message payload too large")
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.info(f"WebSocket client disconnected/error: {e}")
    finally:
        manager.disconnect(websocket)

