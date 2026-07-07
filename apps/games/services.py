from __future__ import annotations

import io
import random
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import chess
import chess.pgn
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.rooms.services import GUEST_NAME_SESSION_KEY, GUEST_SESSION_KEY, ParticipantIdentity, ensure_guest_identity, identity_from_scope


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


def actor_from_request(request: HttpRequest, game: Any) -> GameActor:
    identity = ensure_guest_identity(request)
    color = color_for_identity(game, identity)
    return GameActor(identity=identity, color=color, display_name=identity.display_name)


def actor_from_scope(scope: dict[str, Any], game: Any) -> GameActor:
    identity = identity_from_scope(scope)

    metadata = getattr(game, "metadata", None) or {}

    if metadata.get("mode") == "same_pc" or metadata.get("source") == "fen_import":
        board = board_from_fen(game.current_fen)
        color = color_from_board(board)
        return GameActor(
            identity=identity,
            color=color,
            display_name=identity.display_name,
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


def display_for_color(game: Any, color: str) -> str:
    return game.white_display_name if color == "white" else game.black_display_name


def user_for_color(game: Any, color: str):
    return game.white_user if color == "white" else game.black_user


def guest_key_for_color(game: Any, color: str) -> str:
    return game.white_guest_key if color == "white" else game.black_guest_key


def legal_moves_for_fen(fen: str) -> list[dict[str, str]]:
    board = board_from_fen(fen)
    moves: list[dict[str, str]] = []
    for move in board.legal_moves:
        moves.append({"uci": move.uci(), "san": board.san(move), "from": chess.square_name(move.from_square), "to": chess.square_name(move.to_square)})
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
                    "color": "white" if piece and piece.color == chess.WHITE else "black" if piece else "",
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
        for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]:
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
    if game.initial_fen != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":
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
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return pgn_game.accept(exporter)


def update_cached_pgn(game: Any) -> None:
    game.cached_pgn = generate_pgn(game)
    game.save(update_fields=["cached_pgn", "updated_at"])


def _participants_for_game(room: Any) -> tuple[Any, Any]:
    from apps.rooms.models import RoomParticipant

    players = list(
        room.participants.filter(
            role__in=[RoomParticipant.Role.HOST, RoomParticipant.Role.PLAYER],
            status__in=[RoomParticipant.Status.JOINED, RoomParticipant.Status.READY],
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
def create_game_from_room(*, room: Any, request: HttpRequest | None = None):
    from apps.games.models import Game, GameEvent
    from apps.rooms.models import Room

    existing_game = getattr(room, "game", None)
    if existing_game is not None:
        return existing_game

    player_a, player_b = _participants_for_game(room)
    white, black = _assign_colors(room, player_a, player_b)
    initial_ms = int(room.clock_initial_seconds) * 1000
    increment_ms = int(room.increment_seconds) * 1000
    delay_ms = int(room.delay_seconds) * 1000
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
    )
    room.status = Room.Status.IN_PROGRESS
    room.save(update_fields=["status", "updated_at"])
    GameEvent.objects.create(game=game, event_type=GameEvent.EventType.CREATED, payload={"room_code": room.code})
    GameEvent.objects.create(game=game, event_type=GameEvent.EventType.STARTED, payload={"source": "room"})
    update_cached_pgn(game)
    return game


@transaction.atomic
def create_same_pc_game(*, white_name: str, black_name: str, initial_minutes: int = 5, increment_seconds: int = 0, delay_seconds: int = 0):
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
    GameEvent.objects.create(game=game, event_type=GameEvent.EventType.CREATED, payload={"mode": "same_pc"})
    GameEvent.objects.create(game=game, event_type=GameEvent.EventType.STARTED, payload={"mode": "same_pc"})
    update_cached_pgn(game)
    return game


def _apply_clock_before_move(game: Any, mover_color: str) -> None:
    if game.clock_started_at is None or game.status != game.Status.ACTIVE:
        return
    now = timezone.now()
    elapsed_ms = int((now - game.clock_started_at).total_seconds() * 1000)
    charged_ms = max(elapsed_ms - game.delay_ms, 0)
    if mover_color == "white":
        game.white_time_ms = max(int(game.white_time_ms) - charged_ms, 0)
    else:
        game.black_time_ms = max(int(game.black_time_ms) - charged_ms, 0)


def _add_increment_after_move(game: Any, mover_color: str) -> None:
    if mover_color == "white":
        game.white_time_ms += game.increment_ms
    else:
        game.black_time_ms += game.increment_ms


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
def play_uci_move(*, game: Any, actor: GameActor, uci: str, client_lag_ms: int = 0):
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
    game_move = GameMove.objects.create(
        game=game,
        ply_number=game.ply_count,
        move_number=board.fullmove_number if mover_color == "black" else board.fullmove_number,
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
        payload={"uci": move.uci(), "san": san, "fen": game.current_fen, "ply": game.ply_count},
    )
    update_cached_pgn(game)
    return game_move, game


def _timeout_game(game: Any, loser_color: str) -> None:
    game.status = game.Status.FINISHED
    game.result = game.Result.BLACK_WIN if loser_color == "white" else game.Result.WHITE_WIN
    game.winner_color = opponent(loser_color)
    game.termination = game.Termination.TIMEOUT
    game.ended_at = timezone.now()
    game.clock_started_at = None
    game.save(update_fields=["status", "result", "winner_color", "termination", "ended_at", "clock_started_at", "white_time_ms", "black_time_ms", "updated_at"])


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
    game.finish(result=result, termination=game.Termination.RESIGNATION, winner_color=winner)
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
    game.finish(result=game.Result.ONGOING, termination=game.Termination.ABORTED)
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
        game.finish(result=game.Result.DRAW, termination=game.Termination.AGREEMENT)
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
def import_game_from_fen(*, request: HttpRequest, fen: str, white_name: str = "White", black_name: str = "Black"):
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
    return {"white": white_ms, "black": black_ms}


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


def serialize_game(game: Any, *, request: HttpRequest | None = None, include_legal_moves: bool = True) -> dict[str, Any]:
    game_moves = list(game.moves.all().order_by("ply_number"))
    payload = {
        "id": str(game.id),
        "url": game.get_absolute_url(),
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
        "white": {"name": game.white_display_name, "time_ms": _clock_preview(game)["white"]},
        "black": {"name": game.black_display_name, "time_ms": _clock_preview(game)["black"]},
        "clock": {"initial_ms": game.clock_initial_ms, "increment_ms": game.increment_ms, "delay_ms": game.delay_ms},
        "draw_offer_by": game.draw_offer_by,
        "takeback_offer_by": game.takeback_offer_by,
        "captured": captured_pieces(game),
        "board": board_matrix(game.current_fen),
        "moves": [serialize_move(move) for move in game_moves],
        "is_live": game.is_live,
        "started_at": game.started_at.isoformat() if game.started_at else None,
        "ended_at": game.ended_at.isoformat() if game.ended_at else None,
    }
    if include_legal_moves and game.status == game.Status.ACTIVE:
        payload["legal_moves"] = legal_moves_for_fen(game.current_fen)
    else:
        payload["legal_moves"] = []
    if request is not None:
        actor = actor_from_request(request, game)
        payload["viewer"] = {"color": actor.color, "name": actor.display_name, "can_move": actor.color == game.turn}
    return payload


def pgn_response_text(game: Any) -> str:
    if not game.cached_pgn:
        update_cached_pgn(game)
    return game.cached_pgn
