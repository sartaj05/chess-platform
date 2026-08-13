from django.urls import path

from apps.notifications.api_views import MobileNotificationListAPIView, MobileNotificationReadAllAPIView, MobileNotificationReadAPIView

app_name = "notifications_api"
urlpatterns = [
    path("notifications/", MobileNotificationListAPIView.as_view(), name="list"),
    path("notifications/read-all/", MobileNotificationReadAllAPIView.as_view(), name="read-all"),
    path("notifications/<int:pk>/read/", MobileNotificationReadAPIView.as_view(), name="read"),
]
