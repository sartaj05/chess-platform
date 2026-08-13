from django.urls import path
from .api_views import SocialAPIView
urlpatterns=[path("social/",SocialAPIView.as_view(),name="social")]
