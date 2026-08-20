from django.urls import path

from .views import ConversationDetailView, ConversationListView, DeleteMessageView, EditMessageView, StartConversationView, UnsendMessageView

app_name = "chat"
urlpatterns = [
    path("", ConversationListView.as_view(), name="list"),
    path("start/<uuid:user_id>/", StartConversationView.as_view(), name="start"),
    path("<int:pk>/", ConversationDetailView.as_view(), name="thread"),
    path("<int:pk>/messages/<int:message_pk>/edit/", EditMessageView.as_view(), name="edit_message"),
    path("<int:pk>/messages/<int:message_pk>/delete/", DeleteMessageView.as_view(), name="delete_message"),
    path("<int:pk>/messages/<int:message_pk>/unsend/", UnsendMessageView.as_view(), name="unsend_message"),
]
