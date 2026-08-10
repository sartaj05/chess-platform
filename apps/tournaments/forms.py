from __future__ import annotations

from django import forms
from django.utils import timezone

from .models import Tournament


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = (
            "name",
            "description",
            "format",
            "starts_at",
            "max_players",
            "clock_initial_minutes",
            "increment_seconds",
            "is_public",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"

    def clean_starts_at(self):
        starts_at = self.cleaned_data["starts_at"]
        if starts_at <= timezone.now():
            raise forms.ValidationError("The tournament must start in the future.")
        return starts_at
