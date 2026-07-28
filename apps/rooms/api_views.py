from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, pagination, permissions, response, status, views

from apps.api.throttles import RoomWriteAnonRateThrottle, RoomWriteUserRateThrottle
from apps.games.serializers import GameSerializer
from apps.games.services import create_game_from_room, serialize_game
from apps.rooms.models import Room
from apps.rooms.serializers import CreateRoomSerializer, JoinRoomSerializer, RoomParticipantSerializer, RoomSerializer


class PublicRoomPagination(pagination.PageNumberPagination):
    """Provide a stable, metadata-bearing response for public room discovery."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class RoomListCreateAPIView(generics.ListCreateAPIView):
    """List public rooms or create a room for web/mobile clients."""

    permission_classes = [permissions.AllowAny]
    pagination_class = PublicRoomPagination

    def get_throttles(self):
        if self.request.method == "POST":
            return [RoomWriteAnonRateThrottle(), RoomWriteUserRateThrottle()]
        return []

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
    throttle_classes = [RoomWriteAnonRateThrottle, RoomWriteUserRateThrottle]

    @extend_schema(request=JoinRoomSerializer, responses=RoomParticipantSerializer)
    def post(self, request, code: str):
        room = generics.get_object_or_404(Room, code=code.upper())
        serializer = JoinRoomSerializer(data=request.data, context={"request": request, "room": room})
        serializer.is_valid(raise_exception=True)
        participant = serializer.save()
        return response.Response(RoomParticipantSerializer(participant).data, status=status.HTTP_200_OK)


class StartRoomGameAPIView(views.APIView):
    """Start a room game for mobile and other API clients."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [RoomWriteAnonRateThrottle, RoomWriteUserRateThrottle]

    @extend_schema(request=None, responses={status.HTTP_201_CREATED: GameSerializer})
    def post(self, request, code: str):
        room = generics.get_object_or_404(Room.objects.prefetch_related("participants"), code=code.upper())
        game = create_game_from_room(room=room, request=request)
        return response.Response(serialize_game(game, request=request), status=status.HTTP_201_CREATED)
