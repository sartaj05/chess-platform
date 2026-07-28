from rest_framework import serializers

from .models import User


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
        )
        read_only_fields = ("id", "email", "is_email_verified", "two_factor_enabled", "date_joined", "last_seen_at")

    def get_avatar_url(self, obj) -> str | None:
        request = self.context.get("request")
        if not obj.avatar:
            return None
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
