from rest_framework import permissions, serializers, views
from rest_framework.response import Response

from apps.notifications.models import Notification, PushDevice


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "message", "target_url", "is_read", "created_at"]
        read_only_fields = fields


class MobileNotificationListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = Notification.objects.filter(recipient=request.user)[:50]
        return Response(NotificationSerializer(rows, many=True).data)


class MobileNotificationReadAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            return Response({"detail": "Notification not found."}, status=404)
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)


class MobileNotificationReadAllAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.utils import timezone

        count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": count})


class PushDeviceAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        token = str(request.data.get("token", "")).strip()
        if not token:
            return Response({"detail": "A device token is required."}, status=400)
        device, _ = PushDevice.objects.update_or_create(token=token, defaults={"user": request.user, "platform": request.data.get("platform", "android"), "active": True, "last_seen_at": timezone.now()})
        return Response({"id": device.pk, "registered": True})

    def delete(self, request):
        PushDevice.objects.filter(token=request.data.get("token"), user=request.user).update(active=False)
        return Response(status=204)
