from django.urls import path

from .views import (
    AcceptFriendRequestView,
    ChallengeReminderView,
    FriendListView,
    FriendRequestActionView,
    RemoveFriendView,
    SendFriendRequestView,
)

app_name = "friends"
urlpatterns = [
    path("", FriendListView.as_view(), name="list"),
    path("request/", SendFriendRequestView.as_view(), name="send"),
    path("<int:pk>/accept/", AcceptFriendRequestView.as_view(), name="accept"),
    path("<int:pk>/decline/", FriendRequestActionView.as_view(), name="decline"),
    path("<int:pk>/remove/", RemoveFriendView.as_view(), name="remove"),
    path("challenges/<int:pk>/remind/", ChallengeReminderView.as_view(), name="challenge_remind"),
]
