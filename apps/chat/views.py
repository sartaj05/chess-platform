from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User

from .forms import MessageForm
from .models import Conversation, Message
from .services import delete_message_for_sender, edit_message, get_or_create_conversation, send_message, unsend_message


class ConversationListView(LoginRequiredMixin, TemplateView):
    template_name = "chat/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversations = Conversation.objects.filter(
            Q(first_user=self.request.user) | Q(second_user=self.request.user)
        ).select_related("first_user", "second_user")
        context["conversations"] = [
            {
                "conversation": conversation,
                "other": conversation.other_user(self.request.user),
                "unread": conversation.messages.exclude(sender=self.request.user).filter(read_at__isnull=True).count(),
                "latest": conversation.messages.order_by("-created_at").first(),
            }
            for conversation in conversations
        ]
        return context


class StartConversationView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, user_id) -> HttpResponse:
        other = get_object_or_404(User, pk=user_id, is_active=True)
        try:
            conversation = get_or_create_conversation(actor=request.user, other=other)
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
            return redirect("friends:list")
        return redirect("chat:thread", pk=conversation.pk)


class ConversationDetailView(LoginRequiredMixin, TemplateView):
    template_name = "chat/thread.html"

    def _conversation(self) -> Conversation:
        conversation = get_object_or_404(
            Conversation.objects.select_related("first_user", "second_user"), pk=self.kwargs["pk"]
        )
        if not conversation.involves(self.request.user):
            raise Http404
        return conversation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = self._conversation()
        Message.objects.filter(conversation=conversation, read_at__isnull=True).exclude(sender=self.request.user).update(
            read_at=timezone.now()
        )
        context.update(
            conversation=conversation,
            other=conversation.other_user(self.request.user),
            chat_messages=conversation.messages.select_related("sender").exclude(
                sender=self.request.user, deleted_for_sender=True
            ),
            message_form=MessageForm(),
        )
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        conversation = self._conversation()
        form = MessageForm(request.POST)
        if form.is_valid():
            try:
                send_message(conversation=conversation, sender=request.user, body=form.cleaned_data["body"])
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Enter a message of 2,000 characters or fewer.")
        return redirect("chat:thread", pk=conversation.pk)


class MessageActionView(LoginRequiredMixin, View):
    action = ""

    def post(self, request: HttpRequest, pk: int, message_pk: int) -> HttpResponse:
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.involves(request.user):
            raise Http404
        message = get_object_or_404(Message, pk=message_pk, conversation=conversation)
        try:
            if self.action == "edit":
                edit_message(message=message, actor=request.user, body=request.POST.get("body", ""))
                messages.success(request, "Message updated.")
            elif self.action == "delete":
                delete_message_for_sender(message=message, actor=request.user)
                messages.success(request, "Message deleted for you.")
            else:
                unsend_message(message=message, actor=request.user)
                messages.success(request, "Message unsent for everyone.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("chat:thread", pk=conversation.pk)


class EditMessageView(MessageActionView):
    action = "edit"


class DeleteMessageView(MessageActionView):
    action = "delete"


class UnsendMessageView(MessageActionView):
    action = "unsend"
