from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer
class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request): return Response(UserSerializer(request.user, context={"request": request}).data)
    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True, context={"request": request}); ser.is_valid(raise_exception=True); ser.save(); return Response(ser.data)
