# Module 4 - Stockfish Analysis, Game Review, and Opening Explorer

## Scope

Module 4 adds the offline chess intelligence layer:

- Local Stockfish UCI subprocess integration.
- Docker image installation of the `stockfish` binary.
- Engine profiles stored in the database.
- Auditable engine run logs.
- One-position analysis board.
- Full-game review jobs through Celery.
- Move classification: best, excellent, good, inaccuracy, mistake, blunder.
- Evaluation graph data.
- Opening explorer foundation with seeded local ECO lines.
- REST API endpoints for mobile clients.

## Web URLs

```text
/analysis/board/
/analysis/openings/
/analysis/openings.json
/analysis/jobs/<JOB_UUID>/
/analysis/jobs/<JOB_UUID>/state/
/games/<GAME_UUID>/review/
/games/<GAME_UUID>/review/start/
/stockfish/status/
```

## API URLs

```text
/api/analysis/games/<GAME_UUID>/start/
/api/analysis/jobs/<JOB_UUID>/
/api/analysis/position/
/api/analysis/openings/?moves=e2e4,e7e5
```

## Offline Stockfish

The Dockerfile installs Stockfish using apt. The default binary path is:

```text
/usr/games/stockfish
```

Override it in `.env` when installing manually:

```text
STOCKFISH_BINARY=/path/to/stockfish
```

## Game review flow

1. Open a game.
2. Click `Game Review`.
3. Choose depth.
4. Submit the review.
5. Celery runs Stockfish over every move.
6. The job page refreshes state through JSON polling and draws the evaluation graph.

## Git commit

```bash
git add .
git commit -m "Complete Stockfish analysis and game review module"
```
