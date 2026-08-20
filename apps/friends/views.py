from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import UserPreference

from .forms import FriendRequestForm
from .models import FriendChallenge, Friendship
from .services import remove_friendship, respond_to_request, send_friend_request


class FriendListView(LoginRequiredMixin, TemplateView):
    template_name = "friends/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        relationships = Friendship.objects.select_related("requester", "addressee")
        context["friends"] = []
        for relationship in relationships.filter(
            Q(requester=self.request.user) | Q(addressee=self.request.user),
            status=Friendship.Status.ACCEPTED,
        ):
            other = relationship.other_user(self.request.user)
            preferences, _ = UserPreference.objects.get_or_create(user=other)
            context["friends"].append(
                {
                    "relationship": relationship,
                    "user": other,
                    "online": preferences.show_online_status and bool(cache.get(f"presence:user:{other.pk}")),
                }
            )
        context["incoming"] = relationships.filter(
            addressee=self.request.user,
            status=Friendship.Status.PENDING,
        )
        context["outgoing"] = relationships.filter(
            requester=self.request.user,
            status=Friendship.Status.PENDING,
        )
        context["request_form"] = FriendRequestForm()
        context["challenge_history"] = FriendChallenge.objects.filter(
            Q(challenger=self.request.user) | Q(challenged=self.request.user)
        ).select_related("challenger", "challenged", "room")[:10]
        return context


class SendFriendRequestView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        form = FriendRequestForm(request.POST)
        if form.is_valid():
            try:
                send_friend_request(requester=request.user, email=form.cleaned_data["email"])
                messages.success(request, "Friend request sent.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        else:
            messages.error(request, "Enter a valid email address.")
        return redirect("friends:list")


class FriendRequestActionView(LoginRequiredMixin, View):
    accept = False

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        friendship = get_object_or_404(Friendship, pk=pk)
        try:
            respond_to_request(friendship=friendship, actor=request.user, accept=self.accept)
            messages.success(request, "Friend request accepted." if self.accept else "Friend request declined.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect("friends:list")


class AcceptFriendRequestView(FriendRequestActionView):
    accept = True


class RemoveFriendView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        friendship = get_object_or_404(Friendship, pk=pk)
        try:
            remove_friendship(friendship=friendship, actor=request.user)
            messages.success(request, "Friend removed.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect("friends:list")
