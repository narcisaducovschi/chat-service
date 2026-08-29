from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, dict[WebSocket, str]] = {}

    async def connect(self, websocket: WebSocket, room: str, email: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = {}
        self.rooms[room][websocket] = email

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms and websocket in self.rooms[room]:
            del self.rooms[room][websocket]
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast_to_room(self, room: str, message: str, exclude: WebSocket = None):
        if room not in self.rooms:
            return
        for connection in self.rooms[room]:
            if connection != exclude:
                await connection.send_text(message)

    def get_users_in_room(self, room: str) -> list[str]:
        return list(self.rooms.get(room, {}).values())


manager = ConnectionManager()