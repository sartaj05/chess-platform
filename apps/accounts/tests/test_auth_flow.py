import pytest
from django.urls import reverse

from apps.accounts.models import EmailOTP, User


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email="PLAYER@example.com", password="StrongPass123!")
    assert user.email == "player@example.com"
    assert user.check_password("StrongPass123!")


@pytest.mark.django_db
def test_signup_creates_inactive_user_and_otp(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "email": "newplayer@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "accept_terms": "on",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="newplayer@example.com")
    assert user.is_active is False
    assert EmailOTP.objects.filter(user=user, purpose=EmailOTP.Purpose.VERIFY_EMAIL).exists()


@pytest.mark.django_db
def test_me_api_requires_authentication(client):
    response = client.get(reverse("api:accounts_api:me"))
    assert response.status_code in {401, 403}
