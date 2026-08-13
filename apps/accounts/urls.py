from django.urls import path

from .views import (
    ChessPasswordResetCompleteView,
    ChessPasswordResetConfirmView,
    ChessPasswordResetDoneView,
    ChessPasswordResetView,
    DisableTwoFactorView,
    EnableTwoFactorView,
    LoginView,
    LogoutView,
    ProfileView,
    PublicProfileView,
    GameHistoryView,
    ResendVerificationView,
    SecuritySettingsView,
    SignUpView,
    TwoFactorVerifyView,
    VerifyEmailLinkView,
    VerifyEmailView,
)

app_name = "accounts"
urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("verify-email-link/<str:token>/", VerifyEmailLinkView.as_view(), name="verify_email_link"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend_verification"),
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="two_factor_verify"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("players/<uuid:pk>/", PublicProfileView.as_view(), name="public_profile"),
    path("history/", GameHistoryView.as_view(), name="game_history"),
    path("security/", SecuritySettingsView.as_view(), name="security"),
    path("security/2fa/enable/", EnableTwoFactorView.as_view(), name="enable_2fa"),
    path("security/2fa/disable/", DisableTwoFactorView.as_view(), name="disable_2fa"),
    path("password-reset/", ChessPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", ChessPasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        ChessPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password-reset/complete/", ChessPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
