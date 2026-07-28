from django.conf import settings
from django.core import signing

EMAIL_VERIFY_SALT = "accounts.email.verify"


def make_email_verification_token(user_id: str) -> str:
    return signing.dumps({"uid": str(user_id)}, salt=EMAIL_VERIFY_SALT)


def read_email_verification_token(token: str) -> str:
    return str(
        signing.loads(token, salt=EMAIL_VERIFY_SALT, max_age=getattr(settings, "OTP_CODE_TTL_MINUTES", 10) * 60)["uid"]
    )
