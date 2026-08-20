from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, response, views

from .models import Club, SimultaneousExhibition, TeamCompetition, Tournament, TournamentEntry, TournamentPairing
from .services import (
    cancel_tournament,
    create_club,
    create_simul,
    create_team_competition,
    enter_club,
    join_club,
    join_simul,
    join_tournament,
    post_tournament_announcement,
    post_tournament_message,
    remove_tournament_player,
    report_pairing_result,
    start_simul,
    start_team_competition,
    start_tournament,
    withdraw_from_tournament,
)


def serialize_tournament(row, user):
    return {
        "id": row.pk,
        "name": row.name,
        "description": row.description,
        "format": row.format,
        "status": row.status,
        "starts_at": row.starts_at,
        "max_players": row.max_players,
        "player_count": row.entries.count(),
        "time_control": row.time_control,
        "invite_code": row.invite_code,
        "organizer_id": str(row.organizer_id),
        "organizer_name": row.organizer.display_name,
        "is_organizer": user.is_authenticated and row.organizer_id == user.pk,
        "joined": user.is_authenticated and row.entries.filter(user=user).exists(),
        "standings": [
            {
                "entry_id": e.pk,
                "user_id": str(e.user_id),
                "name": e.user.display_name,
                "score": str(e.score),
                "buchholz": str(e.buchholz),
                "sonneborn_berger": str(e.sonneborn_berger),
            }
            for e in row.entries.select_related("user").order_by("-score")
        ],
        "rounds": [
            {
                "number": rnd.number,
                "status": rnd.status,
                "pairings": [
                    {
                        "board": p.board_number,
                        "pairing_id": p.pk,
                        "white": p.white_entry.user.display_name,
                        "black": p.black_entry.user.display_name if p.black_entry_id else "Bye",
                        "result": p.result,
                        "game_id": str(p.game_id) if p.game_id else None,
                        "game_url": p.game.get_absolute_url() if p.game_id else None,
                    }
                    for p in rnd.pairings.select_related("white_entry__user", "black_entry__user").all()
                ],
            }
            for rnd in row.rounds.all()
        ],
        "announcements": [
            {"author": item.author.display_name, "body": item.body, "created_at": item.created_at}
            for item in row.announcements.select_related("author").all()[:20]
        ],
        "chat": [
            {"sender": item.sender.display_name, "body": item.body, "created_at": item.created_at}
            for item in row.chat_messages.select_related("sender").all()[:50]
        ],
    }


class TournamentAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            row = Tournament.objects.select_related("organizer").get(pk=pk)
            if (
                not row.is_public
                and row.organizer_id != request.user.pk
                and not row.entries.filter(user=request.user).exists()
            ):
                raise PermissionDenied("This tournament is private.")
            return response.Response(serialize_tournament(row, request.user))
        rows = Tournament.objects.filter(is_public=True).select_related("organizer").order_by("starts_at")[:50]
        return response.Response([serialize_tournament(row, request.user) for row in rows])

    def post(self, request, pk=None):
        try:
            action = request.data.get("action", "")
            if pk is None:
                if action == "join_code":
                    row = Tournament.objects.get(invite_code=str(request.data.get("invite_code", "")).upper())
                    join_tournament(tournament=row, user=request.user)
                else:
                    starts_at = parse_datetime(str(request.data.get("starts_at", "")))
                    if starts_at is None:
                        raise ValidationError("Enter a valid start date and time.")
                    name = str(request.data.get("name", "")).strip()[:120]
                    if not name:
                        raise ValidationError("Tournament name is required.")
                    tournament_format = request.data.get("format", Tournament.Format.SWISS)
                    if tournament_format not in Tournament.Format.values:
                        raise ValidationError("Select a valid tournament format.")
                    row = Tournament.objects.create(
                        name=name,
                        description=str(request.data.get("description", "")).strip()[:2000],
                        organizer=request.user,
                        format=tournament_format,
                        starts_at=starts_at,
                        max_players=max(2, min(int(request.data.get("max_players", 16)), 256)),
                        clock_initial_minutes=max(1, min(int(request.data.get("clock_initial_minutes", 10)), 1440)),
                        increment_seconds=max(0, min(int(request.data.get("increment_seconds", 0)), 60)),
                        is_public=bool(request.data.get("is_public", True)),
                    )
                    TournamentEntry.objects.create(tournament=row, user=request.user)
            else:
                row = Tournament.objects.select_related("organizer").get(pk=pk)
                if action == "join":
                    join_tournament(tournament=row, user=request.user)
                elif action == "withdraw":
                    withdraw_from_tournament(tournament=row, user=request.user)
                elif action == "start":
                    start_tournament(tournament=row, actor=request.user)
                elif action == "cancel":
                    cancel_tournament(tournament=row, actor=request.user)
                elif action == "remove_player":
                    remove_tournament_player(
                        tournament=row,
                        actor=request.user,
                        entry=TournamentEntry.objects.get(pk=request.data.get("entry_id"), tournament=row),
                    )
                elif action == "report_result":
                    report_pairing_result(
                        tournament=row,
                        actor=request.user,
                        pairing=TournamentPairing.objects.get(pk=request.data.get("pairing_id")),
                        result=request.data.get("result", ""),
                    )
                elif action == "announce":
                    post_tournament_announcement(tournament=row, actor=request.user, body=request.data.get("body", ""))
                elif action == "chat":
                    post_tournament_message(tournament=row, actor=request.user, body=request.data.get("body", ""))
                else:
                    raise ValidationError("Unsupported tournament action.")
        except (
            PermissionDenied,
            ValidationError,
            ValueError,
            Tournament.DoesNotExist,
            TournamentEntry.DoesNotExist,
            TournamentPairing.DoesNotExist,
        ) as exc:
            return response.Response({"detail": str(exc)}, status=400)
        return response.Response(
            serialize_tournament(Tournament.objects.select_related("organizer").get(pk=row.pk), request.user),
            status=201 if pk is None and action != "join_code" else 200,
        )


class CompetitionHubAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        clubs = Club.objects.filter(members=request.user).distinct()
        simuls = SimultaneousExhibition.objects.filter(
            models.Q(host=request.user) | models.Q(seats__opponent=request.user)
        ).distinct()
        return response.Response({
            "clubs": [{"id": c.pk, "name": c.name, "slug": c.slug, "invite_code": c.invite_code,
                       "members": c.memberships.count()} for c in clubs],
            "team_competitions": [{"id": c.pk, "name": c.name, "status": c.status,
                                   "clubs": c.entries.count(), "boards_per_team": c.boards_per_team}
                                  for c in TeamCompetition.objects.filter(entries__club__members=request.user).distinct()],
            "simuls": [{"id": s.pk, "name": s.name, "status": s.status, "invite_code": s.invite_code,
                        "host": s.host.display_name, "boards": s.seats.count()}
                       for s in simuls.select_related("host")],
        })

    def post(self, request):
        action = request.data.get("action", "")
        try:
            if action == "create_club":
                row = create_club(owner=request.user, name=request.data.get("name", ""),
                                  slug=request.data.get("slug", ""), description=request.data.get("description", ""))
                payload = {"id": row.pk, "invite_code": row.invite_code}
            elif action == "join_club":
                row = join_club(user=request.user, code=request.data.get("invite_code", ""))
                payload = {"club_id": row.club_id, "joined": True}
            elif action == "create_team_competition":
                starts_at = parse_datetime(str(request.data.get("starts_at", "")))
                if starts_at is None:
                    raise ValidationError("Enter a valid start date and time.")
                row = create_team_competition(organizer=request.user, name=request.data.get("name", ""),
                                              starts_at=starts_at,
                                              boards_per_team=request.data.get("boards_per_team", 4))
                payload = {"id": row.pk}
            elif action == "enter_club":
                row = enter_club(competition=TeamCompetition.objects.get(pk=request.data.get("competition_id")),
                                 club=Club.objects.get(pk=request.data.get("club_id")), captain=request.user)
                payload = {"entry_id": row.pk}
            elif action == "start_team_competition":
                row = start_team_competition(
                    competition=TeamCompetition.objects.get(pk=request.data.get("competition_id")),
                    actor=request.user,
                )
                payload = {"id": row.pk, "status": row.status,
                           "games": [str(board.game_id) for board in row.boards.all()]}
            elif action == "create_simul":
                starts_at = parse_datetime(str(request.data.get("starts_at", "")))
                if starts_at is None:
                    raise ValidationError("Enter a valid start date and time.")
                row = create_simul(host=request.user, name=request.data.get("name", ""), starts_at=starts_at,
                                   max_opponents=request.data.get("max_opponents", 20),
                                   host_color=request.data.get("host_color", "white"))
                payload = {"id": row.pk, "invite_code": row.invite_code}
            elif action == "join_simul":
                exhibition = SimultaneousExhibition.objects.get(invite_code=request.data.get("invite_code", "").upper())
                row = join_simul(exhibition=exhibition, opponent=request.user)
                payload = {"seat_id": row.pk, "board_number": row.board_number}
            elif action == "start_simul":
                row = start_simul(exhibition=SimultaneousExhibition.objects.get(pk=request.data.get("simul_id")),
                                  actor=request.user)
                payload = {"id": row.pk, "status": row.status,
                           "games": [str(seat.game_id) for seat in row.seats.all()]}
            else:
                raise ValidationError("Unsupported competition action.")
        except (PermissionDenied, ValidationError, ValueError, Club.DoesNotExist,
                TeamCompetition.DoesNotExist, SimultaneousExhibition.DoesNotExist) as exc:
            return response.Response({"detail": str(exc)}, status=400)
        return response.Response(payload, status=201)
