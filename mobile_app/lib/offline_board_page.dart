import 'dart:math';

import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';

import 'offline_game_repository.dart';

enum OfflinePlayMode { friend, bot }

enum BoardSide { white, black, random }

class OfflineBoardPage extends StatefulWidget {
  const OfflineBoardPage({
    super.key,
    this.mode = OfflinePlayMode.friend,
    this.preferredSide = BoardSide.white,
    this.botLevel = 1,
    this.onBotVictory,
  });

  final OfflinePlayMode mode;
  final BoardSide preferredSide;
  final int botLevel;
  final Future<int> Function(int level)? onBotVictory;

  @override
  State<OfflineBoardPage> createState() => _OfflineBoardPageState();
}

class _OfflineBoardPageState extends State<OfflineBoardPage> {
  final _game = chess.Chess();
  final _repository = OfflineGameRepository();
  final _id = DateTime.now().microsecondsSinceEpoch.toString();
  String? _selected;
  bool _reportedVictory = false;
  late final bool _playerIsWhite = switch (widget.preferredSide) {
    BoardSide.white => true,
    BoardSide.black => false,
    BoardSide.random => Random().nextBool(),
  };

  @override
  void initState() {
    super.initState();
    if (widget.mode == OfflinePlayMode.bot && !_playerIsWhite) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _playBotMove());
    }
  }

  void _tap(String square) {
    if (widget.mode == OfflinePlayMode.bot &&
        (_game.turn == chess.Chess.WHITE) != _playerIsWhite) {
      return;
    }
    if (_selected == null) {
      final piece = _game.get(square);
      if (piece != null && piece.color == _game.turn) {
        setState(() => _selected = square);
      }
      return;
    }
    final moved =
        _game.move({'from': _selected, 'to': square, 'promotion': 'q'});
    setState(() => _selected = moved ? null : square);
    if (moved && widget.mode == OfflinePlayMode.bot) {
      _checkResult();
      Future<void>.delayed(const Duration(milliseconds: 350), _playBotMove);
    }
  }

  void _playBotMove() {
    if (!mounted || _game.game_over) return;
    final moves = _game.moves({'verbose': true});
    if (moves.isEmpty) return;
    final move = _chooseBotMove(moves.cast<Map>());
    setState(() => _game.move(move));
    _checkResult();
  }

  dynamic _chooseBotMove(List<Map> moves) {
    if (widget.botLevel <= 1) return moves[Random().nextInt(moves.length)];
    const values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0};
    moves.sort((a, b) {
      final aScore = (values[a['captured']] ?? 0) * 10 +
          (a['san']?.toString().contains('+') == true ? widget.botLevel : 0);
      final bScore = (values[b['captured']] ?? 0) * 10 +
          (b['san']?.toString().contains('+') == true ? widget.botLevel : 0);
      return bScore.compareTo(aScore);
    });
    final pool = max(1, 5 - widget.botLevel ~/ 2);
    return moves[Random().nextInt(min(pool, moves.length))];
  }

  Future<void> _checkResult() async {
    if (!_game.in_checkmate || _reportedVictory) return;
    final playerWon = (_game.turn == chess.Chess.BLACK) == _playerIsWhite;
    if (!playerWon) return;
    _reportedVictory = true;
    final unlocked = await widget.onBotVictory?.call(widget.botLevel);
    if (mounted) {
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          icon: const Icon(Icons.emoji_events, size: 42),
          title: const Text('You won!'),
          content: Text(unlocked != null && unlocked > widget.botLevel
              ? 'Level $unlocked is now unlocked.'
              : 'Great game. Sign in to save your progress.'),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Continue'))
          ],
        ),
      );
    }
  }

  Future<void> _save() async {
    try {
      final now = DateTime.now();
      await _repository.save(OfflineGame(
        id: _id,
        initialFen: chess.Chess.DEFAULT_POSITION,
        currentFen: _game.fen,
        pgn: _game.pgn(),
        mode: 'same_device',
        createdAt: now,
        updatedAt: now,
      ));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Game saved on this device.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save the offline game.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(widget.mode == OfflinePlayMode.bot
              ? 'Bot · Level ${widget.botLevel}'
              : 'Play with Friend'),
        ),
        body: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Text(
                '${_game.turn == chess.Chess.WHITE ? 'White' : 'Black'} to move'),
            const SizedBox(height: 12),
            Expanded(
              child: Center(
                child: AspectRatio(
                  aspectRatio: 1,
                  child: GridView.builder(
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 8),
                    itemCount: 64,
                    itemBuilder: (_, index) {
                      final displayFile = index % 8;
                      final displayRank = index ~/ 8;
                      final blackView = !_playerIsWhite;
                      final file = blackView ? 7 - displayFile : displayFile;
                      final rank =
                          blackView ? displayRank + 1 : 8 - displayRank;
                      final square = '${String.fromCharCode(97 + file)}$rank';
                      final piece = _game.get(square);
                      final dark = (file + rank).isOdd;
                      return InkWell(
                        onTap: () => _tap(square),
                        child: Container(
                          color: _selected == square
                              ? Colors.amber
                              : (dark
                                  ? const Color(0xff769656)
                                  : const Color(0xffeeeed2)),
                          alignment: Alignment.center,
                          child: Text(
                            _symbol(piece?.type.name,
                                piece?.color == chess.Color.WHITE),
                            style: const TextStyle(fontSize: 34),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _save,
              child: const Text('Save offline game'),
            ),
          ]),
        ),
      );

  String _symbol(String? type, bool white) {
    const whitePieces = {
      'p': '♙',
      'n': '♘',
      'b': '♗',
      'r': '♖',
      'q': '♕',
      'k': '♔'
    };
    const blackPieces = {
      'p': '♟',
      'n': '♞',
      'b': '♝',
      'r': '♜',
      'q': '♛',
      'k': '♚'
    };
    return (white ? whitePieces : blackPieces)[type] ?? '';
  }
}
