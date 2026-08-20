from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone

from .models import Conversation, Message
from .services import send_message


class DirectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.conversation_id = self.scope["url_route"]["kwargs"]["pk"]
        if not self.user or not self.user.is_authenticated or not await self._allowed():
            await self.close(code=4403)
            return
        self.group = f"direct_chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        cache.set(f"presence:user:{self.user.pk}", True, 75)
        await self._mark_delivered_and_read()
        await self.channel_layer.group_send(
            self.group, {"type": "presence.changed", "user_id": str(self.user.pk), "online": True}
        )

    async def disconnect(self, code):
        if getattr(self, "user", None) and self.user.is_authenticated:
            cache.set(f"presence:user:{self.user.pk}", False, 15)
            if hasattr(self, "group"):
                await self.channel_layer.group_send(
                    self.group,
                    {"type": "presence.changed", "user_id": str(self.user.pk), "online": False},
                )
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        cache.set(f"presence:user:{self.user.pk}", True, 75)
        if content.get("type") == "chat.send":
            try:
                payload = await self._send(content.get("body", ""))
            except Exception as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.channel_layer.group_send(self.group, {"type": "chat.message", "message": payload})
        elif content.get("type") == "chat.read":
            await self._mark_delivered_and_read()
            await self.channel_layer.group_send(self.group, {"type": "chat.read", "user_id": str(self.user.pk)})
        elif content.get("type") == "presence.ping":
            await self.send_json({"type": "presence.pong"})

    async def chat_message(self, event):
        await self.send_json({"type": "chat.message", "message": event["message"]})

    async def chat_read(self, event):
        await self.send_json({"type": "chat.read", "user_id": event["user_id"]})

    async def presence_changed(self, event):
        await self.send_json({"type": "presence", "user_id": event["user_id"], "online": event["online"]})

    @database_sync_to_async
    def _allowed(self):
        return (
            Conversation.objects.filter(pk=self.conversation_id).filter(first_user=self.user).exists()
            or Conversation.objects.filter(pk=self.conversation_id, second_user=self.user).exists()
        )

    @database_sync_to_async
    def _mark_delivered_and_read(self):
        now = timezone.now()
        Message.objects.filter(conversation_id=self.conversation_id).exclude(sender=self.user).filter(
            delivered_at__isnull=True
        ).update(delivered_at=now)
        Message.objects.filter(conversation_id=self.conversation_id).exclude(sender=self.user).filter(
            read_at__isnull=True
        ).update(read_at=now)

    @database_sync_to_async
    def _send(self, body):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        message = send_message(conversation=conversation, sender=self.user, body=body)
        return {
            "id": message.pk,
            "body": message.body,
            "sender_id": str(self.user.pk),
            "sender": self.user.display_name,
            "created_at": message.created_at.isoformat(),
        }
