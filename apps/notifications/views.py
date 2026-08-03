from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_read()
        if notification.target_url.startswith("/") and not notification.target_url.startswith("//"):
            return redirect(notification.target_url)
        return redirect("notifications:list")


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        from django.utils import timezone

        Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return redirect("notifications:list")
