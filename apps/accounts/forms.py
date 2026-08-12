import pyotp
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import EmailOTP, User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    display_name = forms.CharField(
        required=False, max_length=80, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    accept_terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "display_name", "password1", "password2")

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account already exists with this email address."))
        return email

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.is_active = False
        user.is_email_verified = False
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"})
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    user_cache: User | None = None

    def clean(self) -> dict:
        data = super().clean()
        email = data.get("email", "").lower().strip()
        password = data.get("password")
        if not email or not password:
            return data
        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(password):
            raise ValidationError(_("Invalid email address or password."))
        self.user_cache = user
        if not user.is_email_verified:
            raise ValidationError(_("Email verification is required before login."))
        if not user.is_active:
            raise ValidationError(_("This account is not active."))
        return data

    def get_user(self) -> User:
        if self.user_cache is None:
            raise ValidationError(_("Authentication user was not loaded."))
        return self.user_cache


class EmailOTPForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}))
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={"class": "form-control", "inputmode": "numeric", "autocomplete": "one-time-code"}
        ),
    )

    def __init__(self, *args, purpose: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.purpose = purpose
        self.user = None

    def clean(self) -> dict:
        data = super().clean()
        email = data.get("email", "").lower().strip()
        code = data.get("code", "").strip()
        if not email or not code:
            return data
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise ValidationError(_("Invalid verification code."))
        otp = (
            EmailOTP.objects.filter(user=user, purpose=self.purpose, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if otp is None or not otp.verify(code):
            raise ValidationError(_("Invalid or expired verification code."))
        self.user = user
        return data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "display_name", "bio", "avatar", "country", "time_zone")


class EnableTwoFactorForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={"class": "form-control", "inputmode": "numeric", "autocomplete": "one-time-code"}
        ),
    )

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self) -> str:
        code = self.cleaned_data["code"].strip()
        secret = self.user.ensure_totp_secret()
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise ValidationError(_("Invalid authenticator code."))
        return code


class DisableTwoFactorForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"})
    )

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise ValidationError(_("Password is incorrect."))
        return password


class SetPasswordPolicyForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        password_validation.validate_password(password)
        return password
