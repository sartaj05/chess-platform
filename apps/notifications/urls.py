from django.urls import path

from .views import MarkAllNotificationsReadView, MarkNotificationReadView, NotificationListView

app_name = "notifications"
urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("read-all/", MarkAllNotificationsReadView.as_view(), name="read_all"),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(), name="read"),
]
