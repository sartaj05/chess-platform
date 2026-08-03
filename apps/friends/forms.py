from __future__ import annotations

from django import forms


class FriendRequestForm(forms.Form):
    email = forms.EmailField(
        label="Friend's email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "friend@example.com"}),
    )
