from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        if websocket in self.connections.get(task_id, []):
            self.connections[task_id].remove(websocket)

    async def publish(self, task_id: str, payload: dict) -> None:
        for connection in list(self.connections.get(task_id, [])):
            await connection.send_json(payload)
