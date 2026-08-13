from celery import shared_task
from django.conf import settings


@shared_task(ignore_result=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def send_push_notification(notification_id: int) -> int:
    from .models import Notification, PushDevice
    notification = Notification.objects.filter(pk=notification_id).first()
    credentials_file = getattr(settings, "FIREBASE_CREDENTIALS_FILE", "")
    if notification is None or not credentials_file:
        return 0
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_file))
        tokens = list(PushDevice.objects.filter(user=notification.recipient, active=True).values_list("token", flat=True))
        if not tokens:
            return 0
        result = messaging.send_each_for_multicast(messaging.MulticastMessage(notification=messaging.Notification(title=notification.title, body=notification.message), data={"target_url": notification.target_url, "notification_id": str(notification.pk)}, tokens=tokens))
        return result.success_count
    except (ValueError, OSError):
        return 0
