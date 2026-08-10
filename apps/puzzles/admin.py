from django.contrib import admin

from .models import Puzzle, PuzzleAttempt


@admin.register(Puzzle)
class PuzzleAdmin(admin.ModelAdmin):
    list_display = ("title", "rating", "difficulty", "is_published", "created_at")
    list_filter = ("difficulty", "is_published")
    search_fields = ("title", "themes")


@admin.register(PuzzleAttempt)
class PuzzleAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "puzzle", "status", "mistakes", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email", "puzzle__title")
