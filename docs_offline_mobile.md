# Free offline website and Android app

The website remains Django-based and can run locally or on a LAN. The Android client lives independently in `mobile_app/` and talks only to the local Django API; it does not require a paid service or internet connection during normal use.

## What stays local

- Website/API: Django on the host computer.
- Data: PostgreSQL (or SQLite for a small local installation).
- Realtime rooms/games: Redis and Django Channels on the same LAN.
- Game analysis: the locally installed Stockfish binary.
- Android app: Flutter APK installed directly on Android devices.

## No-charge policy

There is no payment gateway, subscription flow, advertising SDK, cloud analytics, or cloud push service in the mobile foundation. The existing `payments` Django app remains unused and is not routed.

## LAN configuration

Set `DJANGO_ALLOWED_HOSTS` to the host machine's LAN hostname/IP plus `localhost`, then run Django on `0.0.0.0:8000`. Android devices must be connected to the same Wi-Fi network and use the host computer's LAN IP, not `localhost`.
