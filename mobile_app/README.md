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
- Join live rated matchmaking, poll while waiting, and open the matched room
  automatically on both mobile and web.
- Replay completed games move by move and request server-side Stockfish
  post-game analysis from the history screen.

For real Stockfish play, install Stockfish on the Django server and set
`STOCKFISH_BINARY` in `.env` to its executable path. On Windows this can be a
path such as `C:/stockfish/stockfish-windows-x86-64-avx2.exe`; restart Django
after changing it. The mobile APK does not need its own engine binary.
- Read and clear account notifications inside the app.
- Choose system, light, or dark appearance and persist the preference.
- Enable or disable move and game sounds.
- Select English, Hindi, Spanish, or follow the Android system language. The
  localization ARB files in `lib/l10n/` are the source of truth for translators.
- Detect offline sync-ID conflicts instead of silently overwriting either copy;
  callers can keep the server version or queue the device version as a new copy.

## Android integration testing

Run `flutter test integration_test/app_test.dart -d <device-id>` against any
booted emulator or USB-debugging phone. GitHub Actions runs the same smoke test
on an Android 35 Pixel emulator. The optional `physical-phone` job requires a
self-hosted runner labelled `android-phone` and repository variable
`ANDROID_DEVICE_ID`; start it manually from the workflow page when the phone is
connected and unlocked.

## Versioned releases and Play tracks

For a local versioned build run:

`powershell -ExecutionPolicy Bypass -File ..\scripts\build_mobile_release.ps1 -ServerUrl https://your-domain.example -Format appbundle`

By default the script uses the nearest Git tag as the version name and commit
count as the monotonically increasing version code. You can override both with
`-VersionName` and `-VersionCode`.

The `Play Store release` GitHub workflow builds a signed AAB and supports the
`internal`, `alpha`, `beta`, and `production` tracks. Configure its protected
environment with `CHESS_SERVER_URL` plus the Android signing, Firebase, and
`PLAY_SERVICE_ACCOUNT_JSON` secrets described in the workflow. Use environment
approval rules for production.

Production Android releases must be built with the real deployed server URL:
`flutter build appbundle --release --dart-define=CHESS_SERVER_URL=https://your-domain.example`.
