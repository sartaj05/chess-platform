from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MobileEmailVerificationSerializer, MobileRegistrationSerializer, UserSerializer
from .tasks import send_email_verification


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


class MobileRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_email_verification(
            str(user.id),
            request.get_host(),
            "https" if request.is_secure() else "http",
            request.META.get("REMOTE_ADDR"),
            request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            {"detail": "Account created. Enter the verification code sent to your email."},
            status=status.HTTP_201_CREATED,
        )


class MobileVerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        return Response({"detail": "Email verified. You can now log in."})


class MobileBotVictoryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            completed_level = int(request.data.get("level", 0))
        except (TypeError, ValueError):
            completed_level = 0
        user = request.user
        if completed_level == user.bot_level and user.bot_level < 10:
            user.bot_level += 1
            user.save(update_fields=["bot_level"])
        return Response({"bot_level": user.bot_level})
