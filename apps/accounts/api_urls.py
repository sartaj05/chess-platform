from django.urls import path

from .api_views import MeAPIView, MobileBotVictoryAPIView, MobileRegisterAPIView, MobileVerifyEmailAPIView

app_name = "accounts_api"
urlpatterns = [
    path("me/", MeAPIView.as_view(), name="me"),
    path("register/", MobileRegisterAPIView.as_view(), name="register"),
    path("verify-email/", MobileVerifyEmailAPIView.as_view(), name="verify-email"),
    path("bot-victory/", MobileBotVictoryAPIView.as_view(), name="bot-victory"),
]
