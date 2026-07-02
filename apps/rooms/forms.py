from __future__ import annotations

from django import forms

from apps.rooms.models import Room


class BootstrapFormMixin:
    """Apply Bootstrap classes without external form rendering dependencies."""

    def _apply_bootstrap(self) -> None:
        for field in self.fields.values():
            css_class = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            if isinstance(field.widget, forms.Select):
                css_class = "form-select"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css_class}".strip()


class CreateRoomForm(BootstrapFormMixin, forms.Form):
    """Room creation form shared by internet and LAN modes."""

    name = forms.CharField(max_length=120, required=False, label="Room name")
    description = forms.CharField(max_length=240, required=False, widget=forms.Textarea(attrs={"rows": 2}))
    host_display_name = forms.CharField(max_length=80, required=False, label="Your display name")
    mode = forms.ChoiceField(choices=Room.Mode.choices, initial=Room.Mode.ONLINE)
    visibility = forms.ChoiceField(choices=Room.Visibility.choices, initial=Room.Visibility.PRIVATE)
    clock_initial_minutes = forms.IntegerField(min_value=0, max_value=10080, initial=5, label="Initial minutes")
    increment_seconds = forms.IntegerField(min_value=0, max_value=120, initial=0)
    delay_seconds = forms.IntegerField(min_value=0, max_value=120, initial=0)
    color_preference = forms.ChoiceField(choices=Room.ColorPreference.choices, initial=Room.ColorPreference.RANDOM)
    rated = forms.BooleanField(required=False, initial=False)
    allow_guests = forms.BooleanField(required=False, initial=True)
    spectator_enabled = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, user=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and getattr(user, "is_authenticated", False):
            self.fields["host_display_name"].required = False
            self.fields["host_display_name"].help_text = "Authenticated users use their profile name automatically."
        else:
            self.fields["host_display_name"].required = False
            self.fields["host_display_name"].help_text = "Leave blank to receive a guest name."
        self._apply_bootstrap()

    def clean(self) -> dict:
        cleaned = super().clean()
        initial = cleaned.get("clock_initial_minutes") or 0
        increment = cleaned.get("increment_seconds") or 0
        if initial == 0 and increment == 0:
            raise forms.ValidationError("A room needs a positive clock or increment.")
        if cleaned.get("rated") and not getattr(self.user, "is_authenticated", False):
            raise forms.ValidationError("Guest-created rooms must be unrated.")
        return cleaned


class JoinRoomForm(BootstrapFormMixin, forms.Form):
    """Join by code form for guests and registered players."""

    room_code = forms.CharField(max_length=12, label="Room code")
    display_name = forms.CharField(max_length=80, required=False, label="Your display name")
    as_spectator = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, user=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if user is not None and getattr(user, "is_authenticated", False):
            self.fields["display_name"].required = False
            self.fields["display_name"].help_text = "Authenticated users use their profile name automatically."
        self._apply_bootstrap()

    def clean_room_code(self) -> str:
        return self.cleaned_data["room_code"].strip().upper()
