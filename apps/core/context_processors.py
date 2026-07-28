from django.conf import settings


def site_context(request):
    return {
        "site_name": "Chess Platform",
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@localhost"),
    }
