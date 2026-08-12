from collections import defaultdict

from fastapi import WebSocket

#用于管理WebSocket连接的类，允许在不同任务之间进行通信和数据传输。
#比如，`connect` 方法用于建立WebSocket连接，`disconnect` 方法用于断开连接，`publish` 方法用于向特定任务的所有连接发送消息。
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
