from django.urls import path

from .views import HomeView, MemberHomeView, OfflineModeInfoView, health_check

app_name = "core"
urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("app/", MemberHomeView.as_view(), name="member_home"),
    path("offline-mode/", OfflineModeInfoView.as_view(), name="offline_mode"),
    path("health/", health_check, name="health"),
]
