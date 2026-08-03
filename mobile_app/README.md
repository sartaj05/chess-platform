# Chess Platform Mobile (Android / Flutter)

This is the separate, free, offline-first Android companion app. It uses no paid service, no Firebase, no analytics SDK, and no payment SDK.

## Run on a local network

1. Start the Django server so it listens on your LAN interface, for example: `python manage.py runserver 0.0.0.0:8000`.
2. Find the computer's LAN address, for example `192.168.1.10`.
3. Add that address to `DJANGO_ALLOWED_HOSTS` in `.env` and restart Django.
4. Run `flutter pub get` then `flutter run` inside this directory.
5. In the app, enter `http://192.168.1.10:8000` and refresh public rooms.

The first Flutter build needs the Android SDK and locally cached Flutter artifacts. After the app is built, gameplay can remain entirely on your local network with the Django server, PostgreSQL/SQLite, Redis, and Stockfish running locally.

## Current mobile scope

- Configure a LAN server address.
- Sign in using Django's existing JWT endpoint.
- List public rooms, create a public LAN room, and join any room by its code.
- Join as either a player or spectator; guest session identity is retained for later room requests.
- Play a legal same-device chess game offline and save it locally for later synchronization.

Next mobile screens should be WebSocket game play, account profile, local notifications, PGN history, and Stockfish analysis.
