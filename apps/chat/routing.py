from django.urls import path

from .consumers import DirectChatConsumer

websocket_urlpatterns = [path("ws/chat/<int:pk>/", DirectChatConsumer.as_asgi())]
