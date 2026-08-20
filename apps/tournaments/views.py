from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms import TournamentForm
from .models import Club, SimultaneousExhibition, TeamCompetition, Tournament, TournamentEntry, TournamentPairing
from .services import (
    cancel_tournament,
    create_club,
    create_simul,
    create_team_competition,
    join_club,
    join_simul,
    join_tournament,
    post_tournament_announcement,
    post_tournament_message,
    remove_tournament_player,
    report_pairing_result,
    start_simul,
    start_tournament,
    withdraw_from_tournament,
)


class TournamentListView(ListView):
    model = Tournament
    template_name = "tournaments/list.html"
    context_object_name = "tournaments"
    paginate_by = 20

    def get_queryset(self):
        return (
            Tournament.objects.filter(is_public=True)
            .select_related("organizer")
            .annotate(player_count=Count("entries"))
        )


class TournamentInviteView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        code = request.POST.get("invite_code", "").strip().upper()
        tournament = get_object_or_404(Tournament, invite_code=code)
        try:
            join_tournament(tournament=tournament, user=request.user)
            messages.success(request, f"You joined {tournament.name}.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect(tournament.get_absolute_url())


class TournamentCreateView(LoginRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "tournaments/create.html"

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        response = super().form_valid(form)
        join_tournament(tournament=self.object, user=self.request.user)
        messages.success(self.request, "Tournament created. You are registered as the organizer.")
        return response


class TournamentDetailView(DetailView):
    model = Tournament
    template_name = "tournaments/detail.html"
    context_object_name = "tournament"

    def get_queryset(self):
        queryset = Tournament.objects.select_related("organizer").prefetch_related(
            "entries__user",
            "rounds__pairings__white_entry__user",
            "rounds__pairings__black_entry__user",
        )
        if self.request.user.is_authenticated:
            return queryset.filter(
                models.Q(is_public=True)
                | models.Q(organizer=self.request.user)
                | models.Q(entries__user=self.request.user)
            ).distinct()
        return queryset.filter(is_public=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_registered"] = (
            self.request.user.is_authenticated and self.object.entries.filter(user=self.request.user).exists()
        )
        return context


class TournamentActionView(LoginRequiredMixin, View):
    action = ""

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        tournament = get_object_or_404(Tournament, pk=pk)
        try:
            if self.action == "join":
                join_tournament(tournament=tournament, user=request.user)
                messages.success(request, "You joined the tournament.")
            elif self.action == "withdraw":
                withdraw_from_tournament(tournament=tournament, user=request.user)
                messages.success(request, "You withdrew from the tournament.")
            else:
                start_tournament(tournament=tournament, actor=request.user)
                messages.success(request, "Tournament started.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect(tournament.get_absolute_url())


class JoinTournamentView(TournamentActionView):
    action = "join"


class WithdrawTournamentView(TournamentActionView):
    action = "withdraw"


class StartTournamentView(TournamentActionView):
    action = "start"


class ReportPairingResultView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int, pairing_pk: int) -> HttpResponse:
        tournament = get_object_or_404(Tournament, pk=pk)
        pairing = get_object_or_404(TournamentPairing, pk=pairing_pk)
        try:
            report_pairing_result(
                tournament=tournament,
                pairing=pairing,
                actor=request.user,
                result=request.POST.get("result", ""),
            )
            messages.success(request, "Pairing result recorded.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect(tournament.get_absolute_url())


class TournamentManageView(LoginRequiredMixin, View):
    action = ""

    def post(self, request, pk, entry_pk=None):
        tournament = get_object_or_404(Tournament, pk=pk)
        try:
            if self.action == "cancel":
                cancel_tournament(tournament=tournament, actor=request.user)
            elif self.action == "remove":
                remove_tournament_player(
                    tournament=tournament,
                    actor=request.user,
                    entry=get_object_or_404(TournamentEntry, pk=entry_pk, tournament=tournament),
                )
            elif self.action == "announce":
                post_tournament_announcement(
                    tournament=tournament, actor=request.user, body=request.POST.get("body", "")
                )
            else:
                post_tournament_message(tournament=tournament, actor=request.user, body=request.POST.get("body", ""))
            messages.success(request, "Tournament updated.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect(tournament.get_absolute_url())


class CancelTournamentView(TournamentManageView):
    action = "cancel"


class RemoveTournamentPlayerView(TournamentManageView):
    action = "remove"


class TournamentAnnouncementView(TournamentManageView):
    action = "announce"


class TournamentChatView(TournamentManageView):
    action = "chat"


class CompetitionHubView(LoginRequiredMixin, View):
    template_name = "tournaments/competition_hub.html"

    def get(self, request):
        return render(request, self.template_name, {
            "clubs": Club.objects.filter(members=request.user).distinct(),
            "competitions": TeamCompetition.objects.filter(entries__club__members=request.user).distinct(),
            "simuls": SimultaneousExhibition.objects.filter(
                models.Q(host=request.user) | models.Q(seats__opponent=request.user)
            ).distinct(),
        })

    def post(self, request):
        action = request.POST.get("action", "")
        try:
            if action == "create_club":
                create_club(owner=request.user, name=request.POST.get("name", ""),
                            slug=request.POST.get("slug", ""), description=request.POST.get("description", ""))
            elif action == "join_club":
                join_club(user=request.user, code=request.POST.get("invite_code", ""))
            elif action in {"create_simul", "create_team_competition"}:
                starts_at = parse_datetime(request.POST.get("starts_at", ""))
                if starts_at is None:
                    raise ValidationError("Enter a valid start date and time.")
                if action == "create_simul":
                    create_simul(host=request.user, name=request.POST.get("name", ""), starts_at=starts_at,
                                 max_opponents=request.POST.get("max_opponents", 20),
                                 host_color=request.POST.get("host_color", "white"))
                else:
                    create_team_competition(organizer=request.user, name=request.POST.get("name", ""),
                                            starts_at=starts_at,
                                            boards_per_team=request.POST.get("boards_per_team", 4))
            elif action == "join_simul":
                exhibition = get_object_or_404(
                    SimultaneousExhibition, invite_code=request.POST.get("invite_code", "").upper()
                )
                join_simul(exhibition=exhibition, opponent=request.user)
            elif action == "start_simul":
                start_simul(exhibition=get_object_or_404(SimultaneousExhibition, pk=request.POST.get("simul_id")),
                            actor=request.user)
            else:
                raise ValidationError("Unsupported competition action.")
            messages.success(request, "Competition workspace updated.")
        except (PermissionDenied, ValidationError, ValueError) as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("tournaments:competition_hub")
