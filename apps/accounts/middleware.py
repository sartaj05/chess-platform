from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
class UserActivityMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request); user = getattr(request, "user", None)
        if user and user.is_authenticated:
            key = f"user-last-seen-written:{user.pk}"
            if not cache.get(key):
                user.last_seen_at = timezone.now(); user.save(update_fields=["last_seen_at"]); cache.set(key, True, getattr(settings, "USER_ACTIVITY_CACHE_TTL", 180))
        return response
