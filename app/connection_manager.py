from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # cada sala (str) mapea a una lista de conexiones activas en esa sala
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            if not self.rooms[room]:
                del self.rooms[room]  # limpiamos salas vacías

    async def broadcast_to_room(self, room: str, message: str):
        if room not in self.rooms:
            return
        for connection in self.rooms[room]:
            await connection.send_text(message)

    def users_in_room(self, room: str) -> int:
        return len(self.rooms.get(room, []))


manager = ConnectionManager()