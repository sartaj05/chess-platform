import base64
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
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView
from django_ratelimit.decorators import ratelimit

from .forms import DisableTwoFactorForm, EmailLoginForm, EmailOTPForm, EnableTwoFactorForm, ProfileForm, SignUpForm
from .models import EmailOTP, User
from .tasks import send_email_verification
from .tokens import read_email_verification_token


def _client_ip(request: HttpRequest) -> str | None:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


def _send_verification(request: HttpRequest, user: User) -> None:
    send_email_verification.delay(
        str(user.id),
        request.get_host(),
        "https" if request.is_secure() else "http",
        _client_ip(request),
        request.META.get("HTTP_USER_AGENT", ""),
    )


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
    success_url = reverse_lazy("core:member_home")

    def form_valid(self, form: EmailLoginForm) -> HttpResponse:
        user = form.get_user()
        if user.two_factor_enabled:
            self.request.session["pre_2fa_user_id"] = str(user.id)
            self.request.session.set_expiry(300)
            return redirect("accounts:two_factor_verify")
        login(self.request, user)
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
    success_url = reverse_lazy("core:member_home")

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
        login(self.request, self.pending_user)
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
