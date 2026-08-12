from .base import *  # noqa: F403

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

# Development clients can arrive through Android's emulator gateway (10.0.2.2)
# or through a changing private LAN address when testing on a physical phone.
# Production settings continue to require an explicit DJANGO_ALLOWED_HOSTS list.
ALLOWED_HOSTS = ["*"]
