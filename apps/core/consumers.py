from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        await self.accept()
        await self.send_json({"type": "connection.accepted", "message": "connected"})

    async def receive_json(self, content: dict, **kwargs) -> None:
        if content.get("type") == "ping":
            await self.send_json({"type": "pong", "message": "pong"})
        else:
            await self.send_json({"type": "error", "message": "unsupported event"})
