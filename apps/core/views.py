from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import RedirectView, TemplateView


class HomeView(TemplateView):
    template_name = "core/home.html"


class MemberHomeView(LoginRequiredMixin, RedirectView):
    pattern_name = "dashboard:home"
    permanent = False


def health_check(request):
    return JsonResponse({"status": "ok", "service": "chess-platform"})


class OfflineModeInfoView(View):
    def get(self, request):
        return render(request, "core/offline_mode.html")
