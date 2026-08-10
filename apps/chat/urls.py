from django.urls import path

from .views import ConversationDetailView, ConversationListView, StartConversationView

app_name = "chat"
urlpatterns = [
    path("", ConversationListView.as_view(), name="list"),
    path("start/<uuid:user_id>/", StartConversationView.as_view(), name="start"),
    path("<int:pk>/", ConversationDetailView.as_view(), name="thread"),
]
