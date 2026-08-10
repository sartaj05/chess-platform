from __future__ import annotations

from django import forms


class PuzzleMoveForm(forms.Form):
    move = forms.RegexField(
        regex=r"^[a-h][1-8][a-h][1-8][qrbn]?$",
        max_length=5,
        error_messages={"invalid": "Enter a move in UCI format, for example e2e4."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e2e4",
                "autocomplete": "off",
                "autocapitalize": "none",
            }
        ),
    )
