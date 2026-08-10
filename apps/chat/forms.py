from __future__ import annotations

from django import forms


class MessageForm(forms.Form):
    body = forms.CharField(
        max_length=2000,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Write a message...",
                "aria-label": "Message",
            }
        ),
    )
