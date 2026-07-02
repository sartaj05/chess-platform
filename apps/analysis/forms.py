from __future__ import annotations

from django import forms

from apps.analysis.models import GameAnalysisJob


class StartAnalysisForm(forms.Form):
    analysis_type = forms.ChoiceField(choices=GameAnalysisJob.AnalysisType.choices, initial=GameAnalysisJob.AnalysisType.QUICK)
    depth = forms.IntegerField(min_value=1, max_value=18, initial=10)


class PositionAnalysisForm(forms.Form):
    fen = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=180)
    depth = forms.IntegerField(min_value=1, max_value=18, initial=12)
    movetime_ms = forms.IntegerField(min_value=100, max_value=10000, initial=750)


class OpeningExplorerForm(forms.Form):
    moves = forms.CharField(required=False, help_text="UCI moves separated by spaces, for example: e2e4 e7e5 g1f3")
