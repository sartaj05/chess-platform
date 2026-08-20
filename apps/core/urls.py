from django.urls import path

from .views import GlobalSearchView, HomeView, OfflineModeInfoView, PlayView, health_check

app_name = "core"
urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("play/", PlayView.as_view(), name="play"),
    path("offline-mode/", OfflineModeInfoView.as_view(), name="offline_mode"),
    path("health/", health_check, name="health"),
    path("search/", GlobalSearchView.as_view(), name="search"),
]
