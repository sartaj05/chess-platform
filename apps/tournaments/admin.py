from django.contrib import admin

from .models import Tournament, TournamentEntry


class TournamentEntryInline(admin.TabularInline):
    model = TournamentEntry
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "organizer", "format", "status", "starts_at", "max_players")
    list_filter = ("format", "status", "is_public")
    search_fields = ("name", "organizer__email")
    inlines = (TournamentEntryInline,)


@admin.register(TournamentEntry)
class TournamentEntryAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user", "seed", "score")
    search_fields = ("tournament__name", "user__email")
