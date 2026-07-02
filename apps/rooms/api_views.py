from __future__ import annotations

from rest_framework import generics, permissions, response, status, views

from apps.rooms.models import Room
from apps.rooms.serializers import CreateRoomSerializer, JoinRoomSerializer, RoomParticipantSerializer, RoomSerializer


class RoomListCreateAPIView(generics.ListCreateAPIView):
    """List public rooms or create a room for web/mobile clients."""

    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Room.objects.active().public().prefetch_related("participants").recently_active()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRoomSerializer
        return RoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        output = RoomSerializer(room, context={"request": request})
        return response.Response(output.data, status=status.HTTP_201_CREATED)


class RoomRetrieveAPIView(generics.RetrieveAPIView):
    """Retrieve room state by room code."""

    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "code"
    lookup_url_kwarg = "code"

    def get_queryset(self):
        return Room.objects.prefetch_related("participants")


class JoinRoomAPIView(views.APIView):
    """Join room by invite URL code using session, JWT, or guest identity."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, code: str):
        room = generics.get_object_or_404(Room, code=code.upper())
        serializer = JoinRoomSerializer(data=request.data, context={"request": request, "room": room})
        serializer.is_valid(raise_exception=True)
        participant = serializer.save()
        return response.Response(RoomParticipantSerializer(participant).data, status=status.HTTP_200_OK)
