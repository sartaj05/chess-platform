import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.notifications.models import Notification


@pytest.mark.django_db
def test_mobile_notification_list_and_mark_read(client):
    user = User.objects.create_user(email="notify-mobile@example.com", password="StrongPass123!")
    notification = Notification.objects.create(recipient=user, title="Your move", message="A game is waiting.")
    headers = {"HTTP_AUTHORIZATION": f"Bearer {AccessToken.for_user(user)}"}
    response = client.get(reverse("api:notifications_api:list"), **headers)
    assert response.status_code == 200 and response.json()[0]["is_read"] is False
    response = client.post(reverse("api:notifications_api:read", args=[notification.pk]), **headers)
    assert response.status_code == 200 and response.json()["is_read"] is True
