from __future__ import annotations

from rest_framework import serializers

from apps.rooms.models import Room, RoomEvent, RoomParticipant
from apps.rooms.services import absolute_invite_url, create_room, join_room


class RoomParticipantSerializer(serializers.ModelSerializer):
    is_authenticated = serializers.SerializerMethodField()

    class Meta:
        model = RoomParticipant
        fields = ["id", "display_name", "role", "status", "side", "is_connected", "is_authenticated", "last_seen_at"]
        read_only_fields = fields

    def get_is_authenticated(self, obj: RoomParticipant) -> bool:
        return obj.user_id is not None


class RoomEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomEvent
        fields = ["id", "event_type", "actor_display_name", "payload", "created_at"]
        read_only_fields = fields


class RoomSerializer(serializers.ModelSerializer):
    participants = RoomParticipantSerializer(many=True, read_only=True)
    invite_url = serializers.SerializerMethodField()
    time_control = serializers.CharField(source="time_control_label", read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "code",
            "name",
            "description",
            "mode",
            "visibility",
            "status",
            "rated",
            "allow_guests",
            "spectator_enabled",
            "max_players",
            "time_category",
            "time_control",
            "clock_initial_seconds",
            "increment_seconds",
            "delay_seconds",
            "color_preference",
            "host_display_name",
            "participants",
            "invite_url",
            "last_activity_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "code",
            "status",
            "time_category",
            "participants",
            "invite_url",
            "last_activity_at",
            "created_at",
        ]

    def get_invite_url(self, obj: Room) -> str:
        request = self.context.get("request")
        if request is None:
            return obj.invite_path
        return absolute_invite_url(request, obj)


class CreateRoomSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    description = serializers.CharField(max_length=240, required=False, allow_blank=True)
    host_display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    mode = serializers.ChoiceField(choices=Room.Mode.choices, default=Room.Mode.ONLINE)
    visibility = serializers.ChoiceField(choices=Room.Visibility.choices, default=Room.Visibility.PRIVATE)
    clock_initial_minutes = serializers.IntegerField(min_value=0, max_value=10080, default=5)
    increment_seconds = serializers.IntegerField(min_value=0, max_value=120, default=0)
    delay_seconds = serializers.IntegerField(min_value=0, max_value=120, default=0)
    color_preference = serializers.ChoiceField(
        choices=Room.ColorPreference.choices, default=Room.ColorPreference.RANDOM
    )
    rated = serializers.BooleanField(default=False)
    allow_guests = serializers.BooleanField(default=True)
    spectator_enabled = serializers.BooleanField(default=True)

    def validate(self, attrs: dict) -> dict:
        if attrs.get("clock_initial_minutes", 0) == 0 and attrs.get("increment_seconds", 0) == 0:
            raise serializers.ValidationError("A room needs a positive clock or increment.")
        request = self.context.get("request")
        if attrs.get("rated") and (request is None or not request.user.is_authenticated):
            raise serializers.ValidationError("Guest-created rooms must be unrated.")
        return attrs

    def create(self, validated_data: dict) -> Room:
        return create_room(request=self.context["request"], cleaned_data=validated_data)


class JoinRoomSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    as_spectator = serializers.BooleanField(default=False)

    def create(self, validated_data: dict) -> RoomParticipant:
        room = self.context["room"]
        request = self.context["request"]
        return join_room(
            request=request,
            room=room,
            display_name=validated_data.get("display_name"),
            as_spectator=validated_data.get("as_spectator", False),
        )
