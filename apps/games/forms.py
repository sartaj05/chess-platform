from __future__ import annotations

from django import forms

from apps.games.services import board_from_fen


class SamePcGameForm(forms.Form):
    white_name = forms.CharField(max_length=80, initial="White", widget=forms.TextInput(attrs={"class": "form-control"}))
    black_name = forms.CharField(max_length=80, initial="Black", widget=forms.TextInput(attrs={"class": "form-control"}))
    initial_minutes = forms.IntegerField(min_value=0, max_value=1440, initial=5, widget=forms.NumberInput(attrs={"class": "form-control"}))
    increment_seconds = forms.IntegerField(min_value=0, max_value=600, initial=0, widget=forms.NumberInput(attrs={"class": "form-control"}))
    delay_seconds = forms.IntegerField(min_value=0, max_value=600, initial=0, widget=forms.NumberInput(attrs={"class": "form-control"}))


class FenImportForm(forms.Form):
    fen = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}), help_text="Paste a complete FEN string.")
    white_name = forms.CharField(max_length=80, initial="White", widget=forms.TextInput(attrs={"class": "form-control"}))
    black_name = forms.CharField(max_length=80, initial="Black", widget=forms.TextInput(attrs={"class": "form-control"}))

    def clean_fen(self) -> str:
        value = self.cleaned_data["fen"].strip()
        board_from_fen(value)
        return value
