from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.analysis.api_views import run_game_analysis_job
from apps.api.throttles import AnalysisAnonRateThrottle, AnalysisUserRateThrottle
from apps.games.models import STARTING_FEN, Game
from apps.rooms.models import Room


def room_payload(name: str) -> dict:
    return {
        "name": name,
        "host_display_name": "Host",
        "mode": Room.Mode.LAN,
        "visibility": Room.Visibility.PRIVATE,
        "clock_initial_minutes": 5,
        "increment_seconds": 0,
        "delay_seconds": 0,
        "color_preference": Room.ColorPreference.RANDOM,
        "allow_guests": True,
        "spectator_enabled": True,
    }


@pytest.mark.django_db
def test_only_guest_host_session_can_start_room_game():
    cache.clear()
    host_client = Client()
    joiner_client = Client()

    create_response = host_client.post(
        reverse("api:rooms-api:room-list-create"),
        room_payload("Protected LAN room"),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    room_code = create_response.json()["code"]

    join_response = joiner_client.post(
        reverse("api:rooms-api:room-join", kwargs={"code": room_code}),
        {"display_name": "Guest Two"},
        content_type="application/json",
    )
    assert join_response.status_code == 200

    start_url = reverse("api:rooms-api:room-start", kwargs={"code": room_code})
    assert joiner_client.post(start_url).status_code == 403
    assert host_client.post(start_url).status_code == 201


@pytest.mark.django_db
def test_offline_sync_requires_login_and_is_scoped_to_owner(client):
    cache.clear()
    sync_id = str(uuid.uuid4())
    payload = {
        "sync_id": sync_id,
        "initial_fen": STARTING_FEN,
        "current_fen": STARTING_FEN,
        "pgn": "",
        "mode": "same_device",
        "metadata": {
            "source": "untrusted",
            "offline_sync_id": "untrusted",
            "mode": "local_ai",
        },
    }
    url = reverse("api:games-api:game-sync-offline")

    assert client.post(url, payload, content_type="application/json").status_code in {401, 403}

    user = get_user_model().objects.create_user(email="sync@example.com", password="StrongPass123!")
    client.force_login(user)

    first_response = client.post(url, payload, content_type="application/json")
    duplicate_response = client.post(url, payload, content_type="application/json")

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["created"] is False
    game = Game.objects.get(white_user=user, offline_sync_id=sync_id)
    assert game.metadata["source"] == "offline_sync"
    assert game.metadata["mode"] == "same_device"
    assert Game.objects.filter(white_user=user, offline_sync_id=sync_id).count() == 1

    conflicting = {**payload, "current_fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", "pgn": "1. e4"}
    conflict_response = client.post(url, conflicting, content_type="application/json")
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == "offline_sync_conflict"


@pytest.mark.django_db
def test_game_api_hides_private_and_local_games_from_other_callers(client):
    public_room = Room.objects.create(
        name="Public",
        host_display_name="Public Host",
        visibility=Room.Visibility.PUBLIC,
    )
    public_game = Game.objects.create(
        room=public_room,
        white_display_name="White",
        black_display_name="Black",
    )
    owner = get_user_model().objects.create_user(email="owner@example.com", password="StrongPass123!")
    owned_game = Game.objects.create(
        white_user=owner,
        white_display_name="Owner",
        black_display_name="Opponent",
    )
    hidden_game = Game.objects.create(
        white_display_name="Local White",
        black_display_name="Local Black",
    )

    list_url = reverse("api:games-api:game-list")
    anonymous_ids = {item["id"] for item in client.get(list_url).json()}
    assert anonymous_ids == {str(public_game.id)}
    assert client.get(reverse("api:games-api:game-detail", kwargs={"pk": hidden_game.id})).status_code == 404

    client.force_login(owner)
    owner_ids = {item["id"] for item in client.get(list_url).json()}
    assert owner_ids == {str(public_game.id), str(owned_game.id)}


@pytest.mark.django_db
def test_anonymous_analysis_start_is_rate_limited(client, monkeypatch):
    cache.clear()
    monkeypatch.setattr(AnalysisAnonRateThrottle, "rate", "2/minute", raising=False)
    monkeypatch.setattr(AnalysisUserRateThrottle, "rate", "20/minute", raising=False)
    monkeypatch.setattr(run_game_analysis_job, "delay", lambda _job_id: None)

    room = Room.objects.create(
        name="Public analysis",
        host_display_name="Host",
        visibility=Room.Visibility.PUBLIC,
    )
    game = Game.objects.create(
        room=room,
        white_display_name="White",
        black_display_name="Black",
    )
    url = reverse("api:analysis-game-start", kwargs={"pk": game.id})

    assert client.post(url, {}, content_type="application/json").status_code == 202
    assert client.post(url, {}, content_type="application/json").status_code == 202
    assert client.post(url, {}, content_type="application/json").status_code == 429
    cache.clear()
