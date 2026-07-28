from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from celery import shared_task

from .models import EmailOTP, User
from .tokens import make_email_verification_token


@shared_task(name="accounts.send_email_verification")
def send_email_verification(
    user_id: str, request_host: str, scheme: str, ip_address: str | None = None, user_agent: str = ""
) -> None:
    user = User.objects.get(id=user_id)
    _, code = EmailOTP.create_code(
        user=user, purpose=EmailOTP.Purpose.VERIFY_EMAIL, ip_address=ip_address, user_agent=user_agent
    )
    token = make_email_verification_token(str(user.id))
    verify_url = f"{scheme}://{request_host}/accounts/verify-email-link/{token}/"
    message = render_to_string(
        "accounts/emails/verify_email.txt",
        {"user": user, "code": code, "verify_url": verify_url, "ttl_minutes": settings.OTP_CODE_TTL_MINUTES},
    )
    send_mail(
        "Verify your Chess Platform account", message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False
    )


@shared_task(name="accounts.cleanup_expired_otps")
def cleanup_expired_otps() -> int:
    deleted_count, _ = EmailOTP.objects.filter(expires_at__lt=timezone.now()).delete()
    return deleted_count
