from __future__ import annotations

import pytest
from django.urls import reverse

from apps.rooms.models import Room, RoomParticipant


@pytest.mark.django_db
def test_room_model_generates_code() -> None:
    room = Room.objects.create(name="Test", host_display_name="Host")
    assert room.code
    assert room.time_control_label == "5+0"


@pytest.mark.django_db
def test_guest_can_create_room(client) -> None:
    response = client.post(
        reverse("rooms:create"),
        {
            "name": "LAN Match",
            "host_display_name": "Guest Host",
            "mode": Room.Mode.LAN,
            "visibility": Room.Visibility.PRIVATE,
            "clock_initial_minutes": 5,
            "increment_seconds": 3,
            "delay_seconds": 0,
            "color_preference": Room.ColorPreference.RANDOM,
            "allow_guests": "on",
            "spectator_enabled": "on",
        },
    )
    assert response.status_code == 302
    room = Room.objects.get(name="LAN Match")
    assert room.participants.filter(role=RoomParticipant.Role.HOST).exists()


@pytest.mark.django_db
def test_join_by_room_code(client) -> None:
    room = Room.objects.create(name="Join Test", host_display_name="Host")
    response = client.post(
        reverse("rooms:join"),
        {"room_code": room.code, "display_name": "Guest Two"},
    )
    assert response.status_code == 302
    assert room.participants.filter(display_name="Guest Two").exists()


@pytest.mark.django_db
def test_public_rooms_api(client) -> None:
    Room.objects.create(name="Public", host_display_name="Host", visibility=Room.Visibility.PUBLIC)
    response = client.get(reverse("api:rooms-api:room-list-create"))
    assert response.status_code == 200
    assert response.json()["count"] == 1
