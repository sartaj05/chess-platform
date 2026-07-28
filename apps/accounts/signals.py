from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import User


@receiver(pre_save, sender=User)
def normalize_user_email(sender, instance: User, **kwargs) -> None:
    if instance.email:
        instance.email = User.objects.normalize_email(instance.email).lower()
