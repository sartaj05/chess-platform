from __future__ import annotations

from django.contrib import admin

from apps.rooms.models import Room, RoomEvent, RoomParticipant


class RoomParticipantInline(admin.TabularInline):
    model = RoomParticipant
    extra = 0
    fields = ("display_name", "user", "guest_key", "role", "status", "side", "is_connected", "last_seen_at")
    readonly_fields = ("last_seen_at",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "mode",
        "visibility",
        "status",
        "time_control_label",
        "rated",
        "host_display_name",
        "last_activity_at",
    )
    list_filter = ("mode", "visibility", "status", "time_category", "rated", "allow_guests")
    search_fields = ("code", "name", "host_display_name", "host__email")
    readonly_fields = ("id", "created_at", "updated_at", "last_activity_at")
    inlines = [RoomParticipantInline]


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = ("display_name", "room", "role", "status", "side", "is_connected", "last_seen_at")
    list_filter = ("role", "status", "side", "is_connected")
    search_fields = ("display_name", "room__code", "user__email", "guest_key")
    readonly_fields = ("id", "created_at", "updated_at", "joined_at", "left_at", "last_seen_at")


@admin.register(RoomEvent)
class RoomEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "room", "actor_display_name", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("room__code", "actor_display_name", "actor_user__email")
    readonly_fields = ("id", "created_at", "updated_at")
