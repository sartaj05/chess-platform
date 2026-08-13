from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.games.api_views import FairPlayReviewAPIView, GameViewSet

router = DefaultRouter()
router.register("games", GameViewSet, basename="game")

urlpatterns = [path("fair-play/",FairPlayReviewAPIView.as_view()),path("fair-play/<int:pk>/",FairPlayReviewAPIView.as_view()),path("", include(router.urls))]
