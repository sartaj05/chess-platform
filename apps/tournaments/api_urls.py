from django.urls import path
from .api_views import TournamentAPIView
urlpatterns=[path("tournaments/",TournamentAPIView.as_view()),path("tournaments/<int:pk>/",TournamentAPIView.as_view())]
