# Module 3 - Realtime Chess Gameplay

Module 3 turns the room foundation into playable chess games.

## Completed

- Server-authoritative game state
- `python-chess` legal move validation
- Realtime WebSocket gameplay
- Drag/drop and click-to-move chessboard
- Move highlighting
- Captured pieces display
- Move history
- Game clocks with increment and simple delay support
- Resign
- Abort before both players move
- Draw offer, accept, and decline
- FEN export
- FEN import
- PGN generation and download
- Game REST API endpoints for mobile readiness
- Admin management for games, moves, and events
- Database migrations, indexes, constraints, and append-only event logging

## Run

```bash
docker compose up --build
docker compose exec web python manage.py migrate
```

## Test

```bash
docker compose exec web pytest apps/games
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

## Manual smoke test

1. Open `/rooms/create/`.
2. Create a guest room.
3. Open the invite URL in another browser/private window.
4. Click **Ready** from both clients.
5. Click **Start Game**.
6. Move `e2` to `e4` on the board.
7. Download PGN and export FEN.

## Commit

```bash
git add .
git commit -m "Complete realtime chess gameplay and server move validation"
```
