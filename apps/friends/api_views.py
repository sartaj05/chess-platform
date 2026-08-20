from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from rest_framework import permissions, response, views

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.chat.models import Conversation, Message
from apps.chat.services import (
    delete_message_for_sender,
    edit_message,
    get_or_create_conversation,
    send_message,
    unsend_message,
)
from apps.friends.models import FriendChallenge, Friendship, UserBlock, UserReport
from apps.friends.services import respond_to_request, send_friend_request
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.rooms.models import Room
from apps.rooms.services import create_room


class SocialAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friendships = Friendship.objects.filter(Q(requester=request.user) | Q(addressee=request.user)).select_related(
            "requester", "addressee"
        )
        rows = []
        for item in friendships:
            other = item.other_user(request.user)
            rows.append(
                {
                    "id": item.pk,
                    "status": item.status,
                    "incoming": item.addressee_id == request.user.pk,
                    "player": UserSerializer(other, context={"request": request}).data,
                }
            )
        conversations = []
        for chat in Conversation.objects.filter(
            Q(first_user=request.user) | Q(second_user=request.user)
        ).select_related("first_user", "second_user"):
            messages = chat.messages.all().order_by("-created_at")[:50]
            conversations.append(
                {
                    "id": chat.pk,
                    "player": UserSerializer(chat.other_user(request.user), context={"request": request}).data,
                    "messages": [
                        {
                            "id": m.pk,
                            "body": "" if m.unsent_at else m.body,
                            "mine": m.sender_id == request.user.pk,
                            "created_at": m.created_at,
                            "edited_at": m.edited_at,
                            "delivered_at": m.delivered_at,
                            "read_at": m.read_at,
                            "delivery_state": "read" if m.read_at else "delivered" if m.delivered_at else "sent",
                            "unsent": m.unsent_at is not None,
                            "can_edit": m.sender_id == request.user.pk and m.can_edit,
                            "can_delete": m.sender_id == request.user.pk and m.can_delete,
                            "can_unsend": m.sender_id == request.user.pk and m.unsent_at is None,
                        }
                        for m in messages
                        if not (m.sender_id == request.user.pk and m.deleted_for_sender)
                    ],
                }
            )
        return response.Response({"friendships": rows, "conversations": conversations})

    def post(self, request):
        action = request.data.get("action")
        try:
            if action in {"edit_message", "delete_message", "unsend_message"}:
                chat = Conversation.objects.get(pk=request.data.get("conversation_id"))
                if not chat.involves(request.user):
                    raise PermissionDenied("You are not part of this conversation.")
                message = Message.objects.get(pk=request.data.get("message_id"), conversation=chat)
                if action == "edit_message":
                    edit_message(message=message, actor=request.user, body=request.data.get("body", ""))
                elif action == "delete_message":
                    delete_message_for_sender(message=message, actor=request.user)
                else:
                    unsend_message(message=message, actor=request.user)
                return response.Response({"status": "ok"})
            if action == "request":
                item = send_friend_request(requester=request.user, email=request.data.get("email", ""))
                return response.Response({"id": item.pk}, status=201)
            if action in {"accept", "decline"}:
                item = Friendship.objects.get(pk=request.data.get("friendship_id"))
                respond_to_request(friendship=item, actor=request.user, accept=action == "accept")
                return response.Response({"status": item.status})
            other = User.objects.get(pk=request.data.get("user_id"))
            if action == "message":
                chat = get_or_create_conversation(actor=request.user, other=other)
                message = send_message(conversation=chat, sender=request.user, body=request.data.get("body", ""))
                return response.Response({"id": message.pk}, status=201)
            if action == "challenge":
                room = create_room(
                    request=request,
                    cleaned_data={
                        "name": f"{request.user.display_name} vs {other.display_name}",
                        "host_display_name": request.user.display_name,
                        "mode": Room.Mode.ONLINE,
                        "visibility": Room.Visibility.INVITE_ONLY,
                        "clock_initial_minutes": int(request.data.get("minutes", 10)),
                        "increment_seconds": int(request.data.get("increment", 0)),
                        "delay_seconds": 0,
                        "color_preference": Room.ColorPreference.RANDOM,
                        "rated": False,
                        "allow_guests": False,
                        "spectator_enabled": True,
                    },
                )
                FriendChallenge.objects.create(challenger=request.user, challenged=other, room=room)
                notify(
                    recipient=other,
                    kind=Notification.Kind.SYSTEM,
                    title=f"Challenge from {request.user.display_name}",
                    message=room.time_control_label,
                    target_url=room.get_absolute_url(),
                )
                return response.Response({"room_code": room.code, "invite_url": room.get_absolute_url()}, status=201)
            if action == "block":
                UserBlock.objects.get_or_create(blocker=request.user, blocked=other)
                Friendship.objects.filter(
                    Q(requester=request.user, addressee=other) | Q(requester=other, addressee=request.user)
                ).delete()
                return response.Response({"blocked": True})
            if action == "report":
                report = UserReport.objects.create(
                    reporter=request.user,
                    reported=other,
                    reason=request.data.get("reason", "other"),
                    details=request.data.get("details", "")[:1000],
                )
                return response.Response({"id": report.pk}, status=201)
        except (User.DoesNotExist, Friendship.DoesNotExist, Conversation.DoesNotExist, Message.DoesNotExist):
            return response.Response({"detail": "Item not found."}, status=404)
        except (ValidationError, PermissionDenied) as exc:
            return response.Response({"detail": str(exc)}, status=400)
        return response.Response({"detail": "Unsupported action."}, status=400)
