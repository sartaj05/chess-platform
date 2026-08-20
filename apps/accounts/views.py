import base64
import json
from io import BytesIO

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView
from django_ratelimit.decorators import ratelimit
from kombu.exceptions import OperationalError

from apps.games.models import Game

from .forms import (
    DeleteAccountForm,
    DisableTwoFactorForm,
    EmailLoginForm,
    EmailOTPForm,
    EnableTwoFactorForm,
    ProfileForm,
    SignUpForm,
    UserPreferenceForm,
)
from .models import EmailOTP, User, UserPreference
from .tasks import send_email_verification
from .tokens import read_email_verification_token

EMAIL_AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _client_ip(request: HttpRequest) -> str | None:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


def _send_verification(request: HttpRequest, user: User) -> None:
    args = (
        str(user.id),
        request.get_host(),
        "https" if request.is_secure() else "http",
        _client_ip(request),
        request.META.get("HTTP_USER_AGENT", ""),
    )
    try:
        send_email_verification.delay(*args)
    except OperationalError:
        # Authentication and verification must remain available during a
        # temporary broker outage. Production still uses Celery normally.
        send_email_verification.apply(args=args, throw=True)


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="post")
class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("accounts:verify_email")

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        user = form.save()
        _send_verification(self.request, user)
        messages.success(self.request, _("Account created. Check your email for the verification code."))
        self.request.session["verification_email"] = user.email
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True), name="post")
class LoginView(FormView):
    template_name = "accounts/login.html"
    form_class = EmailLoginForm
    success_url = reverse_lazy("dashboard:home")

    def form_valid(self, form: EmailLoginForm) -> HttpResponse:
        user = form.get_user()
        if user.two_factor_enabled:
            self.request.session["pre_2fa_user_id"] = str(user.id)
            self.request.session.set_expiry(300)
            return redirect("accounts:two_factor_verify")
        login(self.request, user, backend=EMAIL_AUTH_BACKEND)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        messages.success(self.request, _("Welcome back."))
        return super().form_valid(form)

    def form_invalid(self, form: EmailLoginForm) -> HttpResponse:
        email = getattr(form, "cleaned_data", {}).get("email")
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.is_email_verified:
                _send_verification(self.request, user)
                self.request.session["verification_email"] = user.email
                messages.warning(self.request, _("Email verification is required. A fresh code has been sent."))
                return redirect("accounts:verify_email")
        return super().form_invalid(form)


class LogoutView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        logout(request)
        messages.info(request, _("You have been logged out."))
        return redirect("core:home")


@method_decorator(ratelimit(key="ip", rate="15/m", method="POST", block=True), name="post")
class VerifyEmailView(FormView):
    template_name = "accounts/verify_email.html"
    form_class = EmailOTPForm
    success_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["purpose"] = EmailOTP.Purpose.VERIFY_EMAIL
        return kwargs

    def get_initial(self) -> dict:
        initial = super().get_initial()
        email = self.request.session.get("verification_email")
        if email:
            initial["email"] = email
        return initial

    def form_valid(self, form: EmailOTPForm) -> HttpResponse:
        user = form.user
        if user is None:
            raise ValidationError("Verification failed.")
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        self.request.session.pop("verification_email", None)
        messages.success(self.request, _("Email verified. You can now log in."))
        return super().form_valid(form)


class VerifyEmailLinkView(View):
    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        try:
            user_id = read_email_verification_token(token)
        except Exception:
            messages.error(request, _("Verification link is invalid or expired."))
            return redirect("accounts:verify_email")
        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        messages.success(request, _("Email verified. You can now log in."))
        return redirect("accounts:login")


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class ResendVerificationView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        email = request.POST.get("email") or request.session.get("verification_email")
        user = User.objects.filter(email__iexact=email or "").first()
        if user and not user.is_email_verified:
            _send_verification(request, user)
            request.session["verification_email"] = user.email
        messages.info(request, _("If the account needs verification, a fresh code has been sent."))
        return redirect("accounts:verify_email")


class TwoFactorVerifyView(FormView):
    template_name = "accounts/two_factor_verify.html"
    form_class = EnableTwoFactorForm
    success_url = reverse_lazy("dashboard:home")

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.pending_user = User.objects.filter(id=request.session.get("pre_2fa_user_id"), is_active=True).first()
        if self.pending_user is None:
            messages.error(request, _("Two-factor session expired. Please login again."))
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.pending_user
        return kwargs

    def form_valid(self, form: EnableTwoFactorForm) -> HttpResponse:
        login(self.request, self.pending_user, backend=EMAIL_AUTH_BACKEND)
        self.request.session.pop("pre_2fa_user_id", None)
        messages.success(self.request, _("Two-factor verification successful."))
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form: ProfileForm) -> HttpResponse:
        messages.success(self.request, _("Profile updated."))
        return super().form_valid(form)


class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"
    context_object_name = "player"

    def get_object(self, queryset=None):
        player = super().get_object(queryset)
        preferences, _ = UserPreference.objects.get_or_create(user=player)
        if preferences.profile_visibility == UserPreference.ProfileVisibility.PRIVATE and self.request.user != player:
            raise Http404
        if (
            preferences.profile_visibility == UserPreference.ProfileVisibility.PLAYERS
            and not self.request.user.is_authenticated
        ):
            raise Http404
        return player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.object
        games = Game.objects.filter(Q(white_user=player) | Q(black_user=player))
        finished = games.filter(status=Game.Status.FINISHED)
        context.update(
            total_games=games.count(),
            wins=finished.filter(Q(white_user=player, result="1-0") | Q(black_user=player, result="0-1")).count(),
            draws=finished.filter(result="1/2-1/2").count(),
            recent_games=games[:10],
        )
        return context


class PlayerComparisonView(TemplateView):
    template_name = "accounts/player_comparison.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        first = get_object_or_404(User, pk=self.request.GET.get("first"))
        second = get_object_or_404(User, pk=self.request.GET.get("second"))

        def stats(player):
            games = Game.objects.filter(Q(white_user=player) | Q(black_user=player), status=Game.Status.FINISHED)
            wins = games.filter(
                Q(white_user=player, result=Game.Result.WHITE_WIN) | Q(black_user=player, result=Game.Result.BLACK_WIN)
            ).count()
            return {
                "player": player,
                "games": games.count(),
                "wins": wins,
                "draws": games.filter(result=Game.Result.DRAW).count(),
                "win_rate": round(wins * 100 / games.count()) if games.exists() else 0,
            }

        context.update(first=stats(first), second=stats(second))
        return context


class GameHistoryView(LoginRequiredMixin, ListView):
    model = Game
    template_name = "accounts/game_history.html"
    context_object_name = "games"
    paginate_by = 25

    def get_queryset(self):
        return Game.objects.filter(Q(white_user=self.request.user) | Q(black_user=self.request.user)).select_related(
            "white_user", "black_user"
        )


class SecuritySettingsView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/security.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        secret = user.ensure_totp_secret()
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Chess Platform")
        qr = qrcode.make(uri)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        context.update(
            {
                "totp_secret": secret,
                "totp_qr_data": base64.b64encode(buf.getvalue()).decode("ascii"),
                "enable_form": EnableTwoFactorForm(user=user),
                "disable_form": DisableTwoFactorForm(user=user),
            }
        )
        return context


class PrivacySettingsView(LoginRequiredMixin, FormView):
    template_name = "accounts/privacy.html"
    form_class = UserPreferenceForm
    success_url = reverse_lazy("accounts:privacy")

    def get_object(self):
        return UserPreference.objects.get_or_create(user=self.request.user)[0]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Privacy and notification preferences updated."))
        return super().form_valid(form)


class PersonalDataExportView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        games = Game.objects.filter(Q(white_user=user) | Q(black_user=user))
        payload = {
            "exported_at": timezone.now(),
            "account": {
                "id": user.pk,
                "email": user.email,
                "display_name": user.display_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "bio": user.bio,
                "country": user.country,
                "date_joined": user.date_joined,
                "ratings": {"bullet": user.bullet_rating, "blitz": user.blitz_rating, "rapid": user.rapid_rating},
            },
            "preferences": list(
                UserPreference.objects.filter(user=user).values(
                    "profile_visibility",
                    "show_online_status",
                    "allow_friend_requests",
                    "allow_direct_messages",
                    "allow_challenges",
                    "notify_friend_activity",
                    "notify_messages",
                    "notify_tournaments",
                    "notify_system",
                    "push_enabled",
                )
            ),
            "games": list(
                games.values("id", "white_display_name", "black_display_name", "status", "result", "created_at")
            ),
            "notifications": list(user.notifications.values("kind", "title", "message", "created_at", "read_at")),
            "tournaments": list(user.tournament_entries.values("tournament__name", "score", "created_at")),
        }
        response = HttpResponse(
            json.dumps(payload, cls=DjangoJSONEncoder, indent=2), content_type="application/json; charset=utf-8"
        )
        response["Content-Disposition"] = 'attachment; filename="chess-platform-data.json"'
        return response


class DeleteAccountView(LoginRequiredMixin, FormView):
    template_name = "accounts/delete_account.html"
    form_class = DeleteAccountForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        logout(self.request)
        user.delete()
        messages.success(self.request, _("Your account and personal data were deleted."))
        return redirect("core:home")


class EnableTwoFactorView(LoginRequiredMixin, FormView):
    form_class = EnableTwoFactorForm
    success_url = reverse_lazy("accounts:security")

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: EnableTwoFactorForm) -> HttpResponse:
        self.request.user.two_factor_enabled = True
        self.request.user.save(update_fields=["two_factor_enabled"])
        messages.success(self.request, _("Two-factor authentication enabled."))
        return super().form_valid(form)

    def form_invalid(self, form: EnableTwoFactorForm) -> HttpResponse:
        messages.error(self.request, form.errors.as_text())
        return redirect("accounts:security")


class DisableTwoFactorView(LoginRequiredMixin, FormView):
    form_class = DisableTwoFactorForm
    success_url = reverse_lazy("accounts:security")

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: DisableTwoFactorForm) -> HttpResponse:
        self.request.user.two_factor_enabled = False
        self.request.user.save(update_fields=["two_factor_enabled"])
        messages.success(self.request, _("Two-factor authentication disabled."))
        return super().form_valid(form)

    def form_invalid(self, form: DisableTwoFactorForm) -> HttpResponse:
        messages.error(self.request, form.errors.as_text())
        return redirect("accounts:security")


class ChessPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class ChessPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class ChessPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class ChessPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
