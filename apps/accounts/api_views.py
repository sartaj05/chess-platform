from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
