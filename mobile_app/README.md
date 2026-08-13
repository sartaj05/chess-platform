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
- Play online games on an interactive board with live WebSocket moves, clocks,
  move history, reconnect handling, draw offers, resign, and abort actions.
- Store access and refresh tokens in Android encrypted storage, restore login on
  app restart, and automatically refresh expired access tokens.
- View and edit the signed-in player profile and browse server-backed game
  history from the app bar.
- Use the Django server's Stockfish engine for bot moves at the selected level,
  with a local fallback when the server or engine is unavailable.

For real Stockfish play, install Stockfish on the Django server and set
`STOCKFISH_BINARY` in `.env` to its executable path. On Windows this can be a
path such as `C:/stockfish/stockfish-windows-x86-64-avx2.exe`; restart Django
after changing it. The mobile APK does not need its own engine binary.

Next mobile screens should be local notifications, detailed PGN replay, and
full Stockfish game analysis.
