from django.urls import path

from .views import PuzzleDetailView, PuzzleListView, PuzzleResetView

app_name = "puzzles"
urlpatterns = [
    path("", PuzzleListView.as_view(), name="list"),
    path("<int:pk>/", PuzzleDetailView.as_view(), name="detail"),
    path("<int:pk>/reset/", PuzzleResetView.as_view(), name="reset"),
]
