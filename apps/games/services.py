from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import chess
import chess.pgn
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone

from apps.rooms.services import (
    GUEST_SESSION_KEY,
    ParticipantIdentity,
    ensure_guest_identity,
    identity_from_scope,
    require_room_host,
)

PIECE_SYMBOLS = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}


@dataclass(frozen=True)
class GameActor:
    """Resolved identity and color for an actor interacting with a game."""

    identity: ParticipantIdentity
    color: str | None
    display_name: str


def board_from_fen(fen: str) -> chess.Board:
    """Create a python-chess board from validated FEN."""

    try:
        return chess.Board(fen)
    except ValueError as exc:
        raise ValidationError(f"Invalid FEN: {exc}") from exc


def color_from_board(board: chess.Board) -> str:
    return "white" if board.turn == chess.WHITE else "black"


def opponent(color: str) -> str:
    return "black" if color == "white" else "white"


def display_for_color(game: Any, color: str) -> str:
    return game.white_display_name if color == "white" else game.black_display_name


def is_same_browser_game(game: Any) -> bool:
    """
    Same PC and FEN import games are played from one browser/session,
    so the current browser must be allowed to move both white and black.
    """

    metadata = getattr(game, "metadata", None) or {}
    return metadata.get("mode") in {"same_pc", "local_ai"} or metadata.get("source") == "fen_import"


def play_local_bot_reply(*, game: Any, actor: GameActor) -> None:
    """Play a Stockfish reply, with a legal local fallback if unavailable."""

    metadata = game.metadata or {}
    if metadata.get("mode") != "local_ai" or game.status != game.Status.ACTIVE:
        return
    if game.turn == metadata.get("player_color"):
        return
    board = board_from_fen(game.current_fen)
    legal_moves = list(board.legal_moves)
    if legal_moves:
        level = max(1, min(int(metadata.get("bot_level", 1)), 10))
        move = None
        try:
            from apps.stockfish.services import analyse_fen_with_stockfish

            result = analyse_fen_with_stockfish(
                fen=board.fen(),
                game=game,
                skill_level=min(20, level * 2),
                depth=min(16, 6 + level),
                movetime_ms=100 + level * 75,
                command_type="website_bot_move",
            )
            candidate = chess.Move.from_uci(result.bestmove)
            if candidate in legal_moves:
                move = candidate
                metadata["bot_engine"] = "stockfish"
        except Exception:
            metadata["bot_engine"] = "built_in_fallback"
        game.metadata = metadata
        game.save(update_fields=["metadata", "updated_at"])
        if move is None:
            move = choose_bot_move(board, legal_moves, level)
        play_uci_move(game=game, actor=actor, uci=move.uci())


def choose_bot_move(board: chess.Board, legal_moves: list[chess.Move], level: int) -> chess.Move:
    """Choose increasingly tactical moves without requiring an engine binary."""

    if level <= 1:
        return random.choice(legal_moves)
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    scored: list[tuple[float, chess.Move]] = []
    for move in legal_moves:
        captured = board.piece_at(move.to_square)
        mover = board.piece_at(move.from_square)
        score = float(piece_values.get(captured.piece_type, 0) * 10 if captured else 0)
        if mover and captured:
            score -= piece_values.get(mover.piece_type, 0)
        board.push(move)
        if board.is_checkmate():
            score += 10000
        elif board.is_check():
            score += 3 + level
        if level >= 4:
            score += len(list(board.legal_moves)) * 0.03
        board.pop()
        score += random.random() * max(0.2, 3 - level * 0.25)
        scored.append((score, move))
    scored.sort(key=lambda item: item[0], reverse=True)
    return random.choice(scored[: max(1, 5 - level // 2)])[1]


def award_bot_level_if_won(game: Any) -> None:
    metadata = game.metadata or {}
    player_color = metadata.get("player_color")
    if metadata.get("mode") != "local_ai" or metadata.get("progress_awarded") or game.winner_color != player_color:
        return
    user = game.white_user if player_color == "white" else game.black_user
    played_level = int(metadata.get("bot_level", 1))
    if user is not None and user.bot_level <= played_level and user.bot_level < 10:
        user.bot_level = played_level + 1
        user.save(update_fields=["bot_level"])
        metadata["level_unlocked"] = user.bot_level
    metadata["progress_awarded"] = user is not None
    game.metadata = metadata
    game.save(update_fields=["metadata", "updated_at"])


def apply_elo_ratings(game: Any) -> None:
    """Apply a standard K=32 Elo update once for a finished rated game."""
    if game.ratings_applied or not game.rated or game.status != game.Status.FINISHED:
        return
    if game.white_user_id is None or game.black_user_id is None:
        return
    white = game.white_user
    black = game.black_user
    category = getattr(getattr(game, "room", None), "time_category", "blitz")
    if category not in {"bullet", "blitz", "rapid"}:
        category = "rapid"
    rating_field = f"{category}_rating"
    games_field = f"{category}_games"
    white_before, black_before = getattr(white, rating_field), getattr(black, rating_field)
    white_score = 1.0 if game.result == game.Result.WHITE_WIN else 0.0 if game.result == game.Result.BLACK_WIN else 0.5
    expected_white = 1 / (1 + 10 ** ((black_before - white_before) / 400))
    white_change = round(32 * (white_score - expected_white))
    black_change = -white_change
    setattr(white, rating_field, max(100, white_before + white_change))
    setattr(black, rating_field, max(100, black_before + black_change))
    setattr(white, games_field, getattr(white, games_field) + 1)
    setattr(black, games_field, getattr(black, games_field) + 1)
    # Keep the legacy rating aligned with the player's most recently used pool.
    white.rating = getattr(white, rating_field)
    black.rating = getattr(black, rating_field)
    white.peak_rating = max(white.peak_rating, getattr(white, rating_field))
    black.peak_rating = max(black.peak_rating, getattr(black, rating_field))
    white.rated_games += 1
    black.rated_games += 1
    white.save(update_fields=["rating", "peak_rating", "rated_games", rating_field, games_field])
    black.save(update_fields=["rating", "peak_rating", "rated_games", rating_field, games_field])
    game.white_rating_before = white_before
    game.black_rating_before = black_before
    game.white_rating_change = white_change
    game.black_rating_change = black_change
    game.ratings_applied = True
    game.save(update_fields=["white_rating_before", "black_rating_before", "white_rating_change", "black_rating_change", "ratings_applied", "updated_at"])
    from apps.games.tasks import evaluate_fair_play
    transaction.on_commit(lambda: evaluate_fair_play.delay(str(game.pk)))
    from apps.games.tasks import evaluate_fair_play
    transaction.on_commit(lambda: evaluate_fair_play.delay(str(game.pk)))


@transaction.atomic
def request_rematch(*, game: Any, actor: GameActor):
    """Record a rematch offer and create a color-swapped game when both players accept."""
    from apps.games.models import Game
    if game.status not in {Game.Status.FINISHED, Game.Status.ABORTED} or actor.color not in {"white", "black"}:
        raise ValidationError("Rematch is available after the game finishes.")
    metadata = dict(game.metadata or {})
    offers = set(metadata.get("rematch_offers", []))
    offers.add(actor.color)
    metadata["rematch_offers"] = sorted(offers)
    if offers == {"white", "black"} and not metadata.get("rematch_game_id"):
        rematch = Game.objects.create(
            rated=game.rated, allow_spectators=game.allow_spectators,
            white_user=game.black_user, black_user=game.white_user,
            white_guest_key=game.black_guest_key, black_guest_key=game.white_guest_key,
            white_display_name=game.black_display_name, black_display_name=game.white_display_name,
            clock_initial_ms=game.clock_initial_ms, increment_ms=game.increment_ms,
            white_time_ms=game.clock_initial_ms, black_time_ms=game.clock_initial_ms,
            metadata={"rematch_of": str(game.pk), "time_category": (game.metadata or {}).get("time_category", "blitz")},
        )
        rematch.start()
        metadata["rematch_game_id"] = str(rematch.pk)
    game.metadata = metadata
    game.save(update_fields=["metadata", "updated_at"])
    return game


def actor_from_request(request: HttpRequest, game: Any) -> GameActor:
    identity = ensure_guest_identity(request)

    if is_same_browser_game(game):
        board = board_from_fen(game.current_fen)
        color = color_from_board(board)

        return GameActor(
            identity=identity,
            color=color,
            display_name=display_for_color(game, color),
        )

    color = color_for_identity(game, identity)

    return GameActor(
        identity=identity,
        color=color,
        display_name=identity.display_name,
    )


def actor_from_scope(scope: dict[str, Any], game: Any) -> GameActor:
    identity = identity_from_scope(scope)

    if is_same_browser_game(game):
        board = board_from_fen(game.current_fen)
        color = color_from_board(board)

        return GameActor(
            identity=identity,
            color=color,
            display_name=display_for_color(game, color),
        )

    color = color_for_identity(game, identity)

    return GameActor(
        identity=identity,
        color=color,
        display_name=identity.display_name,
    )


def color_for_identity(game: Any, identity: ParticipantIdentity) -> str | None:
    if identity.user is not None:
        if game.white_user_id == identity.user.id:
            return "white"
        if game.black_user_id == identity.user.id:
            return "black"
    else:
        if game.white_guest_key and game.white_guest_key == identity.guest_key:
            return "white"
        if game.black_guest_key and game.black_guest_key == identity.guest_key:
            return "black"

    return None


def visible_games_for_request(request: HttpRequest):
    """Return games the caller may discover or retrieve through the API."""

    from apps.games.models import Game
    from apps.rooms.models import Room

    visibility = Q(room__visibility=Room.Visibility.PUBLIC, allow_spectators=True)
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        visibility |= Q(white_user=user) | Q(black_user=user)

    session = getattr(request, "session", None)
    guest_key = session.get(GUEST_SESSION_KEY, "") if session is not None else ""
    if guest_key:
        visibility |= Q(white_guest_key=guest_key) | Q(black_guest_key=guest_key)

    return Game.objects.filter(visibility).distinct()


def user_for_color(game: Any, color: str):
    return game.white_user if color == "white" else game.black_user


def guest_key_for_color(game: Any, color: str) -> str:
    return game.white_guest_key if color == "white" else game.black_guest_key


def legal_moves_for_fen(fen: str) -> list[dict[str, str]]:
    board = board_from_fen(fen)
    moves: list[dict[str, str]] = []

    for move in board.legal_moves:
        moves.append(
            {
                "uci": move.uci(),
                "san": board.san(move),
                "from": chess.square_name(move.from_square),
                "to": chess.square_name(move.to_square),
            }
        )

    return moves


def board_matrix(fen: str) -> list[list[dict[str, Any]]]:
    board = board_from_fen(fen)
    rows: list[list[dict[str, Any]]] = []

    for rank in range(7, -1, -1):
        row: list[dict[str, Any]] = []

        for file_index in range(8):
            square = chess.square(file_index, rank)
            piece = board.piece_at(square)

            row.append(
                {
                    "square": chess.square_name(square),
                    "piece": piece.symbol() if piece else "",
                    "symbol": PIECE_SYMBOLS.get(piece.symbol(), "") if piece else "",
                    "color": ("white" if piece and piece.color == chess.WHITE else "black" if piece else ""),
                    "file": file_index,
                    "rank": rank + 1,
                }
            )

        rows.append(row)

    return rows


def captured_pieces(game: Any) -> dict[str, list[str]]:
    start_board = board_from_fen(game.initial_fen)
    current_board = board_from_fen(game.current_fen)

    result = {"white": [], "black": []}

    for color_bool, color_name in [(chess.WHITE, "white"), (chess.BLACK, "black")]:
        for piece_type in [
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]:
            start_count = len(start_board.pieces(piece_type, color_bool))
            current_count = len(current_board.pieces(piece_type, color_bool))

            for _ in range(max(start_count - current_count, 0)):
                symbol = chess.Piece(piece_type, color_bool).symbol()
                result[color_name].append(PIECE_SYMBOLS[symbol])

    return result


def generate_pgn(game: Any) -> str:
    pgn_game = chess.pgn.Game()

    pgn_game.headers["Event"] = "Chess Platform Game"
    pgn_game.headers["Site"] = "Chess Platform"
    pgn_game.headers["White"] = game.white_display_name
    pgn_game.headers["Black"] = game.black_display_name
    pgn_game.headers["Result"] = game.result
    pgn_game.headers["TimeControl"] = f"{game.clock_initial_ms // 1000}+{game.increment_ms // 1000}"

    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    if game.initial_fen != starting_fen:
        pgn_game.headers["SetUp"] = "1"
        pgn_game.headers["FEN"] = game.initial_fen

    board = board_from_fen(game.initial_fen)
    node = pgn_game

    for item in game.moves.all().order_by("ply_number"):
        move = chess.Move.from_uci(item.uci)

        if move not in board.legal_moves:
            break

        node = node.add_variation(move)
        board.push(move)

    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=False,
        comments=False,
    )

    return pgn_game.accept(exporter)


def update_cached_pgn(game: Any) -> None:
    game.cached_pgn = generate_pgn(game)
    game.save(update_fields=["cached_pgn", "updated_at"])


def _participants_for_game(room: Any) -> tuple[Any, Any]:
    from apps.rooms.models import RoomParticipant

    players = list(
        room.participants.filter(
            role__in=[
                RoomParticipant.Role.HOST,
                RoomParticipant.Role.PLAYER,
            ],
            status__in=[
                RoomParticipant.Status.JOINED,
                RoomParticipant.Status.READY,
            ],
        ).order_by("role", "joined_at")[:2]
    )

    if len(players) < 2:
        raise ValidationError("Two players are required before starting a game.")

    return players[0], players[1]


def _assign_colors(room: Any, player_a: Any, player_b: Any) -> tuple[Any, Any]:
    if room.color_preference == room.ColorPreference.WHITE:
        return player_a, player_b

    if room.color_preference == room.ColorPreference.BLACK:
        return player_b, player_a

    return (player_a, player_b) if random.choice([True, False]) else (player_b, player_a)


@transaction.atomic
def create_game_from_room(*, room: Any, request: HttpRequest):
    from apps.games.models import Game, GameEvent
    from apps.rooms.models import Room

    require_room_host(request, room)

    existing_game = getattr(room, "game", None)

    if existing_game is not None:
        return existing_game

    player_a, player_b = _participants_for_game(room)
    white, black = _assign_colors(room, player_a, player_b)

    initial_ms = int(room.clock_initial_seconds) * 1000
    increment_ms = int(room.increment_seconds) * 1000
    delay_ms = int(room.delay_seconds) * 1000
    grace = {"bullet":30,"blitz":90,"rapid":180,"classical":300,"daily":86400}.get(room.time_category,120)

    game = Game.objects.create(
        room=room,
        status=Game.Status.ACTIVE,
        rated=room.rated,
        allow_spectators=room.spectator_enabled,
        white_user=white.user,
        black_user=black.user,
        white_guest_key=white.guest_key,
        black_guest_key=black.guest_key,
        white_display_name=white.display_name,
        black_display_name=black.display_name,
        clock_initial_ms=initial_ms,
        increment_ms=increment_ms,
        delay_ms=delay_ms,
        white_time_ms=initial_ms,
        black_time_ms=initial_ms,
        started_at=timezone.now(),
        last_move_at=timezone.now(),
        clock_started_at=timezone.now(),
        reconnect_grace_seconds=grace,
    )

    room.status = Room.Status.IN_PROGRESS
    room.save(update_fields=["status", "updated_at"])

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.CREATED,
        payload={"room_code": room.code},
    )

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.STARTED,
        payload={"source": "room"},
    )

    update_cached_pgn(game)

    return game


@transaction.atomic
def create_same_pc_game(
    *,
    white_name: str,
    black_name: str,
    initial_minutes: int = 5,
    increment_seconds: int = 0,
    delay_seconds: int = 0,
):
    from apps.games.models import Game, GameEvent

    initial_ms = max(int(initial_minutes), 0) * 60 * 1000

    game = Game.objects.create(
        status=Game.Status.ACTIVE,
        white_display_name=white_name.strip()[:80] or "White",
        black_display_name=black_name.strip()[:80] or "Black",
        clock_initial_ms=initial_ms,
        increment_ms=max(int(increment_seconds), 0) * 1000,
        delay_ms=max(int(delay_seconds), 0) * 1000,
        white_time_ms=initial_ms,
        black_time_ms=initial_ms,
        started_at=timezone.now(),
        last_move_at=timezone.now(),
        clock_started_at=timezone.now(),
        metadata={"mode": "same_pc"},
    )

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.CREATED,
        payload={"mode": "same_pc"},
    )

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.STARTED,
        payload={"mode": "same_pc"},
    )

    update_cached_pgn(game)

    return game


def _apply_clock_before_move(game: Any, mover_color: str) -> None:
    if game.clock_started_at is None or game.status != game.Status.ACTIVE:
        return

    now = timezone.now()
    elapsed_ms = int((now - game.clock_started_at).total_seconds() * 1000)
    charged_ms = max(elapsed_ms - int(game.delay_ms), 0)

    if mover_color == "white":
        game.white_time_ms = max(int(game.white_time_ms) - charged_ms, 0)
    else:
        game.black_time_ms = max(int(game.black_time_ms) - charged_ms, 0)


def _add_increment_after_move(game: Any, mover_color: str) -> None:
    if mover_color == "white":
        game.white_time_ms += int(game.increment_ms)
    else:
        game.black_time_ms += int(game.increment_ms)


def _finish_if_terminal(game: Any, board: chess.Board) -> None:
    if board.is_checkmate():
        winner = "black" if board.turn == chess.WHITE else "white"

        game.result = game.Result.WHITE_WIN if winner == "white" else game.Result.BLACK_WIN
        game.winner_color = winner
        game.termination = game.Termination.CHECKMATE
        game.status = game.Status.FINISHED
        game.ended_at = timezone.now()
        game.clock_started_at = None

        return

    if board.is_stalemate():
        game.result = game.Result.DRAW
        game.termination = game.Termination.STALEMATE
    elif board.is_insufficient_material():
        game.result = game.Result.DRAW
        game.termination = game.Termination.INSUFFICIENT_MATERIAL
    elif board.is_seventyfive_moves():
        game.result = game.Result.DRAW
        game.termination = game.Termination.SEVENTYFIVE_MOVES
    elif board.is_fivefold_repetition():
        game.result = game.Result.DRAW
        game.termination = game.Termination.FIVEFOLD_REPETITION
    else:
        return

    game.status = game.Status.FINISHED
    game.ended_at = timezone.now()
    game.clock_started_at = None


@transaction.atomic
def play_uci_move(
    *,
    game: Any,
    actor: GameActor,
    uci: str,
    client_lag_ms: int = 0,
):
    from apps.games.models import GameEvent, GameMove

    game = game.__class__.objects.select_for_update().get(pk=game.pk)

    if game.status != game.Status.ACTIVE:
        raise ValidationError("This game is not active.")

    board = board_from_fen(game.current_fen)
    mover_color = color_from_board(board)

    if actor.color is None:
        raise PermissionDenied("Only players can move pieces in this game.")

    if actor.color != mover_color:
        raise ValidationError("It is not your turn.")

    clean_uci = str(uci).strip().lower()

    try:
        move = chess.Move.from_uci(clean_uci)
    except ValueError as exc:
        raise ValidationError("Invalid move format.") from exc

    if move not in board.legal_moves:
        raise ValidationError("Illegal move for the current board position.")

    san = board.san(move)
    fen_before = board.fen()
    move_number_before = board.fullmove_number

    _apply_clock_before_move(game, mover_color)

    if mover_color == "white" and game.white_time_ms <= 0:
        _timeout_game(game, "white")
        raise ValidationError("White lost on time.")

    if mover_color == "black" and game.black_time_ms <= 0:
        _timeout_game(game, "black")
        raise ValidationError("Black lost on time.")

    board.push(move)

    _add_increment_after_move(game, mover_color)

    game.current_fen = board.fen()
    game.turn = color_from_board(board)
    game.fullmove_number = board.fullmove_number
    game.ply_count += 1
    game.last_move_uci = move.uci()
    game.last_move_san = san
    game.last_move_at = timezone.now()
    game.clock_started_at = timezone.now() if game.status == game.Status.ACTIVE else None
    game.draw_offer_by = ""
    game.draw_offer_at = None
    game.takeback_offer_by = ""
    game.takeback_offer_at = None

    _finish_if_terminal(game, board)

    game.save(
        update_fields=[
            "current_fen",
            "turn",
            "fullmove_number",
            "ply_count",
            "last_move_uci",
            "last_move_san",
            "last_move_at",
            "clock_started_at",
            "white_time_ms",
            "black_time_ms",
            "draw_offer_by",
            "draw_offer_at",
            "takeback_offer_by",
            "takeback_offer_at",
            "status",
            "result",
            "termination",
            "winner_color",
            "ended_at",
            "updated_at",
        ]
    )
    award_bot_level_if_won(game)
    apply_elo_ratings(game)

    game_move = GameMove.objects.create(
        game=game,
        ply_number=game.ply_count,
        move_number=move_number_before,
        color=mover_color,
        uci=move.uci(),
        san=san,
        from_square=chess.square_name(move.from_square),
        to_square=chess.square_name(move.to_square),
        promotion=chess.piece_symbol(move.promotion) if move.promotion else "",
        fen_before=fen_before,
        fen_after=board.fen(),
        white_time_ms=game.white_time_ms,
        black_time_ms=game.black_time_ms,
        played_by_user=actor.identity.user,
        played_by_guest_key=actor.identity.guest_key,
        played_by_display_name=actor.display_name,
        client_lag_ms=max(int(client_lag_ms), 0),
    )

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.MOVE,
        actor_user=actor.identity.user,
        actor_guest_key=actor.identity.guest_key,
        actor_display_name=actor.display_name,
        actor_color=mover_color,
        payload={
            "uci": move.uci(),
            "san": san,
            "fen": game.current_fen,
            "ply": game.ply_count,
        },
    )

    update_cached_pgn(game)

    # Persisted notifications back mobile background delivery through FCM;
    # local reminders cover the running clock while the app is suspended.
    if game.status == game.Status.ACTIVE:
        next_player = game.white_user if game.turn == "white" else game.black_user
        if next_player is not None and next_player != actor.identity.user:
            from apps.notifications.models import Notification
            from apps.notifications.services import notify

            notify(
                recipient=next_player,
                kind=Notification.Kind.SYSTEM,
                title="Your move",
                message=f"{actor.display_name} played {san}.",
                target_url=f"/games/{game.pk}/",
            )

    return game_move, game


def _timeout_game(game: Any, loser_color: str) -> None:
    game.status = game.Status.FINISHED
    game.result = game.Result.BLACK_WIN if loser_color == "white" else game.Result.WHITE_WIN
    game.winner_color = opponent(loser_color)
    game.termination = game.Termination.TIMEOUT
    game.ended_at = timezone.now()
    game.clock_started_at = None

    game.save(
        update_fields=[
            "status",
            "result",
            "winner_color",
            "termination",
            "ended_at",
            "clock_started_at",
            "white_time_ms",
            "black_time_ms",
            "updated_at",
        ]
    )


@transaction.atomic
def resign_game(*, game: Any, actor: GameActor):
    from apps.games.models import GameEvent

    game = game.__class__.objects.select_for_update().get(pk=game.pk)

    if game.status != game.Status.ACTIVE:
        raise ValidationError("Only active games can be resigned.")

    if actor.color not in {"white", "black"}:
        raise PermissionDenied("Only players can resign.")

    winner = opponent(actor.color)
    result = game.Result.WHITE_WIN if winner == "white" else game.Result.BLACK_WIN

    game.finish(
        result=result,
        termination=game.Termination.RESIGNATION,
        winner_color=winner,
    )
    apply_elo_ratings(game)

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.RESIGN,
        actor_user=actor.identity.user,
        actor_guest_key=actor.identity.guest_key,
        actor_display_name=actor.display_name,
        actor_color=actor.color,
        payload={"winner": winner},
    )

    update_cached_pgn(game)

    return game


@transaction.atomic
def abort_game(*, game: Any, actor: GameActor):
    from apps.games.models import GameEvent

    game = game.__class__.objects.select_for_update().get(pk=game.pk)

    if game.status not in {game.Status.ACTIVE, game.Status.CREATED}:
        raise ValidationError("This game cannot be aborted.")

    if actor.color not in {"white", "black"}:
        raise PermissionDenied("Only players can abort a game.")

    if game.ply_count > 1:
        raise ValidationError("A game can only be aborted before both players have made a move.")

    game.finish(
        result=game.Result.ONGOING,
        termination=game.Termination.ABORTED,
    )

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.ABORT,
        actor_user=actor.identity.user,
        actor_guest_key=actor.identity.guest_key,
        actor_display_name=actor.display_name,
        actor_color=actor.color,
        payload={"ply_count": game.ply_count},
    )

    update_cached_pgn(game)

    return game


@transaction.atomic
def offer_or_accept_draw(*, game: Any, actor: GameActor):
    from apps.games.models import GameEvent

    game = game.__class__.objects.select_for_update().get(pk=game.pk)

    if game.status != game.Status.ACTIVE:
        raise ValidationError("Only active games can have draw offers.")

    if actor.color not in {"white", "black"}:
        raise PermissionDenied("Only players can offer or accept draws.")

    if game.draw_offer_by and game.draw_offer_by != actor.color:
        game.finish(
            result=game.Result.DRAW,
            termination=game.Termination.AGREEMENT,
        )
        apply_elo_ratings(game)

        GameEvent.objects.create(
            game=game,
            event_type=GameEvent.EventType.DRAW_ACCEPT,
            actor_user=actor.identity.user,
            actor_guest_key=actor.identity.guest_key,
            actor_display_name=actor.display_name,
            actor_color=actor.color,
            payload={"accepted_offer_from": opponent(actor.color)},
        )

        update_cached_pgn(game)

        return game, "accepted"

    game.draw_offer_by = actor.color
    game.draw_offer_at = timezone.now()
    game.save(update_fields=["draw_offer_by", "draw_offer_at", "updated_at"])

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.DRAW_OFFER,
        actor_user=actor.identity.user,
        actor_guest_key=actor.identity.guest_key,
        actor_display_name=actor.display_name,
        actor_color=actor.color,
        payload={"offered_by": actor.color},
    )

    return game, "offered"


@transaction.atomic
def claim_rule_draw(*, game: Any, actor: GameActor, rule: str):
    """Claim a server-verified threefold repetition or fifty-move draw."""
    from apps.games.models import GameEvent
    game = game.__class__.objects.select_for_update().prefetch_related("moves").get(pk=game.pk)
    if game.status != game.Status.ACTIVE or actor.color not in {"white", "black"}:
        raise PermissionDenied("Only a player in an active game can claim a draw.")
    board = chess.Board(game.initial_fen)
    for row in game.moves.all().order_by("ply_number"):
        board.push_uci(row.uci)
    if rule == "threefold" and board.can_claim_threefold_repetition():
        termination = game.Termination.THREEFOLD_REPETITION
    elif rule == "fifty_move" and board.can_claim_fifty_moves():
        termination = game.Termination.FIFTY_MOVE_RULE
    else:
        raise ValidationError("This draw cannot currently be claimed.")
    game.finish(result=game.Result.DRAW, termination=termination)
    apply_elo_ratings(game)
    GameEvent.objects.create(game=game, event_type=GameEvent.EventType.DRAW_ACCEPT, actor_user=actor.identity.user, actor_display_name=actor.display_name, actor_color=actor.color, payload={"rule": rule})
    update_cached_pgn(game)
    return game


@transaction.atomic
def offer_or_accept_takeback(*, game: Any, actor: GameActor):
    from apps.games.models import GameEvent
    game = game.__class__.objects.select_for_update().prefetch_related("moves").get(pk=game.pk)
    if game.rated:
        raise ValidationError("Takebacks are disabled in rated games.")
    if game.status != game.Status.ACTIVE or actor.color not in {"white", "black"} or game.ply_count == 0:
        raise ValidationError("A takeback is not available.")
    if game.takeback_offer_by and game.takeback_offer_by != actor.color:
        last = game.moves.order_by("-ply_number").first()
        game.current_fen = last.fen_before
        game.turn = last.color
        game.ply_count -= 1
        game.fullmove_number = last.move_number
        last.delete()
        previous = game.moves.order_by("-ply_number").first()
        game.white_time_ms = previous.white_time_ms if previous else game.clock_initial_ms
        game.black_time_ms = previous.black_time_ms if previous else game.clock_initial_ms
        game.last_move_uci = previous.uci if previous else ""
        game.last_move_san = previous.san if previous else ""
        game.takeback_offer_by = ""
        game.takeback_offer_at = None
        game.clock_started_at = timezone.now()
        game.save(update_fields=["current_fen", "turn", "ply_count", "fullmove_number", "white_time_ms", "black_time_ms", "last_move_uci", "last_move_san", "takeback_offer_by", "takeback_offer_at", "clock_started_at", "updated_at"])
        event_type, result = GameEvent.EventType.TAKEBACK_ACCEPT, "accepted"
        update_cached_pgn(game)
    else:
        game.takeback_offer_by = actor.color
        game.takeback_offer_at = timezone.now()
        game.save(update_fields=["takeback_offer_by", "takeback_offer_at", "updated_at"])
        event_type, result = GameEvent.EventType.TAKEBACK_OFFER, "offered"
    GameEvent.objects.create(game=game, event_type=event_type, actor_user=actor.identity.user, actor_display_name=actor.display_name, actor_color=actor.color)
    return game, result


@transaction.atomic
def decline_takeback(*, game: Any, actor: GameActor):
    if not game.takeback_offer_by or game.takeback_offer_by == actor.color:
        raise ValidationError("There is no opponent takeback offer to decline.")
    game.takeback_offer_by = ""
    game.takeback_offer_at = None
    game.save(update_fields=["takeback_offer_by", "takeback_offer_at", "updated_at"])
    return game


@transaction.atomic
def decline_draw(*, game: Any, actor: GameActor):
    from apps.games.models import GameEvent

    game = game.__class__.objects.select_for_update().get(pk=game.pk)

    if not game.draw_offer_by:
        raise ValidationError("There is no draw offer to decline.")

    if actor.color == game.draw_offer_by:
        raise ValidationError("The player who offered the draw cannot decline it.")

    game.draw_offer_by = ""
    game.draw_offer_at = None
    game.save(update_fields=["draw_offer_by", "draw_offer_at", "updated_at"])

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.DRAW_DECLINE,
        actor_user=actor.identity.user,
        actor_guest_key=actor.identity.guest_key,
        actor_display_name=actor.display_name,
        actor_color=actor.color or "",
    )

    return game


@transaction.atomic
def import_game_from_fen(
    *,
    request: HttpRequest,
    fen: str,
    white_name: str = "White",
    black_name: str = "Black",
):
    from apps.games.models import Game, GameEvent

    board = board_from_fen(fen.strip())
    initial_ms = 10 * 60 * 1000

    game = Game.objects.create(
        status=Game.Status.ACTIVE,
        white_display_name=white_name.strip()[:80] or "White",
        black_display_name=black_name.strip()[:80] or "Black",
        initial_fen=board.fen(),
        current_fen=board.fen(),
        turn=color_from_board(board),
        fullmove_number=board.fullmove_number,
        clock_initial_ms=initial_ms,
        white_time_ms=initial_ms,
        black_time_ms=initial_ms,
        started_at=timezone.now(),
        last_move_at=timezone.now(),
        clock_started_at=timezone.now(),
        termination=Game.Termination.IMPORTED,
        metadata={"source": "fen_import"},
    )

    identity = ensure_guest_identity(request)

    GameEvent.objects.create(
        game=game,
        event_type=GameEvent.EventType.CREATED,
        actor_user=identity.user,
        actor_guest_key=identity.guest_key,
        actor_display_name=identity.display_name,
        payload={"source": "fen_import"},
    )

    update_cached_pgn(game)

    return game


def _clock_preview(game: Any) -> dict[str, int]:
    white_ms = int(game.white_time_ms)
    black_ms = int(game.black_time_ms)

    if game.status == game.Status.ACTIVE and game.clock_started_at:
        elapsed_ms = int((timezone.now() - game.clock_started_at).total_seconds() * 1000)
        charged_ms = max(elapsed_ms - int(game.delay_ms), 0)

        if game.turn == "white":
            white_ms = max(white_ms - charged_ms, 0)
        else:
            black_ms = max(black_ms - charged_ms, 0)

    return {
        "white": white_ms,
        "black": black_ms,
    }


def serialize_move(move: Any) -> dict[str, Any]:
    return {
        "id": str(move.id),
        "ply": move.ply_number,
        "move_number": move.move_number,
        "color": move.color,
        "uci": move.uci,
        "san": move.san,
        "from": move.from_square,
        "to": move.to_square,
        "promotion": move.promotion,
        "white_time_ms": move.white_time_ms,
        "black_time_ms": move.black_time_ms,
        "played_by": move.played_by_display_name,
        "played_at": move.created_at.isoformat(),
    }


def serialize_game(
    game: Any,
    *,
    request: HttpRequest | None = None,
    include_legal_moves: bool = True,
) -> dict[str, Any]:
    game_moves = list(game.moves.all().order_by("ply_number"))
    clock_preview = _clock_preview(game)
    metadata = getattr(game, "metadata", None) or {}

    payload = {
        "id": str(game.id),
        "url": game.get_absolute_url(),
        "mode": metadata.get("mode", ""),
        "source": metadata.get("source", ""),
        "bot_level": metadata.get("bot_level"),
        "player_color": metadata.get("player_color"),
        "level_unlocked": metadata.get("level_unlocked"),
        "bot_engine": metadata.get("bot_engine", ""),
        "progress_awarded": metadata.get("progress_awarded", False),
        "rematch_offers": metadata.get("rematch_offers", []),
        "rematch_game_id": metadata.get("rematch_game_id"),
        "ratings": {
            "white_before": game.white_rating_before,
            "black_before": game.black_rating_before,
            "white_change": game.white_rating_change,
            "black_change": game.black_rating_change,
            "applied": game.ratings_applied,
        },
        "room_code": game.room.code if game.room_id else "",
        "status": game.status,
        "rated": game.rated,
        "result": game.result,
        "termination": game.termination,
        "winner_color": game.winner_color,
        "turn": game.turn,
        "fen": game.current_fen,
        "initial_fen": game.initial_fen,
        "pgn": game.cached_pgn,
        "ply_count": game.ply_count,
        "fullmove_number": game.fullmove_number,
        "last_move_uci": game.last_move_uci,
        "last_move_san": game.last_move_san,
        "white": {
            "name": game.white_display_name,
            "time_ms": clock_preview["white"],
        },
        "black": {
            "name": game.black_display_name,
            "time_ms": clock_preview["black"],
        },
        "clock": {
            "initial_ms": game.clock_initial_ms,
            "increment_ms": game.increment_ms,
            "delay_ms": game.delay_ms,
        },
        "draw_offer_by": game.draw_offer_by,
        "takeback_offer_by": game.takeback_offer_by,
        "captured": captured_pieces(game),
        "board": board_matrix(game.current_fen),
        "moves": [serialize_move(move) for move in game_moves],
        "is_live": game.is_live,
        "started_at": game.started_at.isoformat() if game.started_at else None,
        "ended_at": game.ended_at.isoformat() if game.ended_at else None,
        "reconnection": {"grace_seconds":game.reconnect_grace_seconds,"white_disconnected_at":game.white_disconnected_at.isoformat() if game.white_disconnected_at else None,"black_disconnected_at":game.black_disconnected_at.isoformat() if game.black_disconnected_at else None},
        "chat": [{"id":str(row.pk),"sender":row.sender_name,"role":row.sender_role,"body":"Message removed by moderator" if row.is_removed else row.body,"audience":row.audience,"created_at":row.created_at.isoformat(),"removed":row.is_removed} for row in game.chat_messages.all().order_by("-created_at")[:50][::-1]] if hasattr(game, "chat_messages") else [],
    }

    if include_legal_moves and game.status == game.Status.ACTIVE:
        payload["legal_moves"] = legal_moves_for_fen(game.current_fen)
    else:
        payload["legal_moves"] = []

    if request is not None:
        actor = actor_from_request(request, game)
        payload["viewer"] = {
            "color": actor.color,
            "name": actor.display_name,
            "can_move": actor.color == game.turn,
        }

    return payload


def pgn_response_text(game: Any) -> str:
    if not game.cached_pgn:
        update_cached_pgn(game)

    return game.cached_pgn
