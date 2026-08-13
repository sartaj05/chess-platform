# Google Play listing

## App name

Chess Platform

## Short description

Play chess offline, with friends, online, or against a levelled bot.

## Full description

Chess Platform is an offline-first chess companion connected to your own Chess Platform server. Play local games, improve through progressively harder Stockfish levels, join live rated matchmaking, invite friends by room code or deep link, solve puzzles, review completed games, and follow ratings and tournaments.

Highlights include live clocks and reconnection, bullet/blitz/rapid ratings, game replay and analysis, profiles and leaderboards, social challenges and chat, push notifications, themes, sounds, premoves, promotion, rematches, correspondence games, and accessible tablet-friendly layouts.

## Publishing checklist

- Replace `chess.example.com` in the Android app-link manifest with the production domain and host `/.well-known/assetlinks.json`.
- Replace the privacy-policy contact placeholder and publish the policy at a public HTTPS URL.
- Configure Firebase Dart defines and Android `google-services.json` for the production application ID.
- Upload at least two phone screenshots and, if tablet distribution is enabled, tablet screenshots to `screenshots/`.
- Complete Play Console Data safety for account data, gameplay, social content, diagnostics, and device tokens.
- Test notification permission, cold-start notification navigation, custom/HTTPS deep links, large text, TalkBack, landscape, and 7–10 inch screens.
- Build an Android App Bundle with the protected upload key for Play Console; retain the signed APK for direct installs.

## Screenshot plan

1. Home and play modes — “Chess your way”
2. Live online board — “Real-time games and clocks”
3. Puzzles — “Train every day”
4. Analysis and replay — “Understand every move”
5. Profile and leaderboard — “Track your progress”

Use portrait 1080×1920 or higher, avoid debug banners and personal account data, and capture from a release/profile build.
