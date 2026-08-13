from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, ListView, TemplateView, View

from apps.rooms.forms import CreateRoomForm, JoinRoomForm
from apps.rooms.models import Room, RoomEvent, RoomParticipant
from apps.rooms.services import absolute_invite_url, create_room, ensure_guest_identity, enter_matchmaking, join_room, serialize_room


class RoomListView(ListView):
    """List public rooms that can be joined or watched."""

    model = Room
    template_name = "rooms/room_list.html"
    context_object_name = "rooms"
    paginate_by = 20

    def get_queryset(self):
        return Room.objects.active().public().select_related("host").prefetch_related("participants").recently_active()


class CreateRoomView(FormView):
    """Create an online, LAN, offline, or same-computer room."""

    template_name = "rooms/create_room.html"
    form_class = CreateRoomForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self) -> dict:
        initial = super().get_initial()
        mode = self.request.GET.get("mode")
        if mode in Room.Mode.values:
            initial["mode"] = mode
        return initial

    def form_valid(self, form: CreateRoomForm) -> HttpResponse:
        room = create_room(request=self.request, cleaned_data=form.cleaned_data)
        messages.success(self.request, f"Room {room.code} created. Share the invite URL with your opponent.")
        return redirect(room.get_absolute_url())


class JoinRoomByCodeView(FormView):
    """Join a room using only the room code."""

    template_name = "rooms/join_room.html"
    form_class = JoinRoomForm
    success_url = reverse_lazy("rooms:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: JoinRoomForm) -> HttpResponse:
        room = get_object_or_404(Room, code=form.cleaned_data["room_code"])
        try:
            join_room(
                request=self.request,
                room=room,
                display_name=form.cleaned_data.get("display_name"),
                as_spectator=bool(form.cleaned_data.get("as_spectator")),
            )
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc.messages[0] if hasattr(exc, "messages") else str(exc))
            return self.form_invalid(form)
        return redirect(room.get_absolute_url())


class RoomDetailView(View):
    """Room lobby page and automatic invite URL join."""

    template_name = "rooms/room_detail.html"

    def get_room(self, code: str) -> Room:
        return get_object_or_404(
            Room.objects.select_related("host").prefetch_related(
                Prefetch("participants", queryset=RoomParticipant.objects.order_by("role", "joined_at")),
            ),
            code=code.upper(),
        )

    def get(self, request: HttpRequest, code: str) -> HttpResponse:
        room = self.get_room(code)
        display_name = request.GET.get("name") or None
        as_spectator = request.GET.get("spectator") == "1"
        try:
            participant = join_room(request=request, room=room, display_name=display_name, as_spectator=as_spectator)
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
            participant = None
        room = self.get_room(room.code)
        identity = ensure_guest_identity(request)
        context = {
            "room": room,
            "participant": participant,
            "room_state": serialize_room(room, request=request),
            "invite_url": absolute_invite_url(request, room),
            "guest_key_present": bool(identity.guest_key),
            "recent_events": RoomEvent.objects.filter(room=room).order_by("-created_at")[:25],
        }
        return render(request, self.template_name, context)


class RoomStateView(View):
    """JSON state endpoint used by HTMX/AJAX and reconnect recovery."""

    def get(self, request: HttpRequest, code: str) -> JsonResponse:
        room = get_object_or_404(Room.objects.prefetch_related("participants"), code=code.upper())
        return JsonResponse(serialize_room(room, request=request))


class LeaveRoomView(View):
    """Leave a room from the web UI."""

    def post(self, request: HttpRequest, code: str) -> HttpResponse:
        room = get_object_or_404(Room, code=code.upper())
        identity = ensure_guest_identity(request)
        participant = None
        if identity.user is not None:
            participant = room.participants.filter(user=identity.user).first()
        elif identity.guest_key:
            participant = room.participants.filter(guest_key=identity.guest_key).first()
        if participant is None:
            raise Http404("Participant not found.")
        participant.leave()
        RoomEvent.objects.create(
            room=room,
            event_type=RoomEvent.EventType.PARTICIPANT_LEFT,
            actor_user=identity.user,
            actor_guest_key=identity.guest_key,
            actor_display_name=identity.display_name,
            payload={"source": "web"},
        )
        messages.info(request, f"You left room {room.code}.")
        return redirect("rooms:list")


class LanModeView(TemplateView):
    """Instruction page for offline LAN play."""

    template_name = "rooms/lan_mode.html"


class MatchmakingView(LoginRequiredMixin, View):
    template_name = "rooms/matchmaking.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        room, matched = enter_matchmaking(request=request)
        if matched:
            messages.success(request, f"Matched with {room.host_display_name}.")
            return redirect(room.get_absolute_url())
        messages.info(request, "You are in the queue. Keep this lobby open while an opponent joins.")
        return redirect(room.get_absolute_url())
