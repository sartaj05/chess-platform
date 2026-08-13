from django.core.exceptions import ValidationError
from django.db.models import Count
from rest_framework import permissions, response, views
from .models import Tournament
from .services import join_tournament, withdraw_from_tournament

def serialize_tournament(row,user):
    return {"id":row.pk,"name":row.name,"description":row.description,"format":row.format,"status":row.status,"starts_at":row.starts_at,"max_players":row.max_players,"player_count":row.entries.count(),"time_control":row.time_control,"joined":user.is_authenticated and row.entries.filter(user=user).exists(),"standings":[{"name":e.user.display_name,"score":str(e.score)} for e in row.entries.select_related("user").order_by("-score")],"rounds":[{"number":rnd.number,"status":rnd.status,"pairings":[{"board":p.board_number,"white":p.white_entry.user.display_name,"black":p.black_entry.user.display_name if p.black_entry_id else "Bye","result":p.result} for p in rnd.pairings.select_related("white_entry__user","black_entry__user").all()]} for rnd in row.rounds.all()]}

class TournamentAPIView(views.APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request,pk=None):
        if pk: return response.Response(serialize_tournament(Tournament.objects.get(pk=pk,is_public=True),request.user))
        rows=Tournament.objects.filter(is_public=True).select_related("organizer").order_by("starts_at")[:50]
        return response.Response([serialize_tournament(row,request.user) for row in rows])
    def post(self,request,pk=None):
        row=Tournament.objects.get(pk=pk,is_public=True)
        try:
            join_tournament(tournament=row,user=request.user) if request.data.get("action")=="join" else withdraw_from_tournament(tournament=row,user=request.user)
        except ValidationError as exc: return response.Response({"detail":str(exc)},status=400)
        return response.Response(serialize_tournament(row,request.user))
