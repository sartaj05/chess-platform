from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import EmailOTP, User


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "bio",
            "avatar_url",
            "country",
            "time_zone",
            "is_email_verified",
            "two_factor_enabled",
            "date_joined",
            "last_seen_at",
            "bot_level",
            "rating",
            "peak_rating",
            "rated_games",
        )
        read_only_fields = (
            "id",
            "email",
            "is_email_verified",
            "two_factor_enabled",
            "date_joined",
            "last_seen_at",
            "bot_level",
            "rating",
            "peak_rating",
            "rated_games",
        )

    def get_avatar_url(self, obj) -> str | None:
        request = self.context.get("request")
        if not obj.avatar:
            return None
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url


class MobileRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account already exists with this email address.")
        return email

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=validated_data.get("display_name", ""),
            is_active=False,
            is_email_verified=False,
        )


class MobileEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs: dict) -> dict:
        user = User.objects.filter(email__iexact=attrs["email"].strip()).first()
        otp = None
        if user is not None:
            otp = (
                EmailOTP.objects.filter(
                    user=user,
                    purpose=EmailOTP.Purpose.VERIFY_EMAIL,
                    used_at__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )
        if user is None or otp is None or not otp.verify(attrs["code"].strip()):
            raise serializers.ValidationError("Invalid or expired verification code.")
        attrs["user"] = user
        return attrs
