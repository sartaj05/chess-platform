from django.urls import path

from .api_views import PresenceAPIView, RetentionHubAPIView

urlpatterns = [
    path("retention/", RetentionHubAPIView.as_view(), name="retention-hub"),
    path("presence/heartbeat/", PresenceAPIView.as_view(), name="presence-heartbeat"),
]
