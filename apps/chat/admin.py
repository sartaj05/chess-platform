from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("first_user", "second_user", "updated_at")
    search_fields = ("first_user__email", "second_user__email")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "read_at", "created_at")
    search_fields = ("sender__email", "body")
    list_filter = ("read_at",)
