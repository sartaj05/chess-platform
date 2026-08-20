import 'dart:math';

import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'offline_game_repository.dart';
import 'game_result_dialog.dart';

enum OfflinePlayMode { friend, bot }

enum BoardSide { white, black, random }

class OfflineBoardPage extends StatefulWidget {
  const OfflineBoardPage({
    super.key,
    this.mode = OfflinePlayMode.friend,
    this.preferredSide = BoardSide.white,
    this.botLevel = 1,
    this.botPersonality = 'balanced',
    this.onBotVictory,
    this.stockfishMove,
    this.soundsEnabled = true,
    this.boardTheme = 'forest',
    this.soundPack = 'wood',
  });

  final OfflinePlayMode mode;
  final BoardSide preferredSide;
  final int botLevel;
  final String botPersonality;
  final Future<int> Function(int level)? onBotVictory;
  final Future<String?> Function(String fen, int level)? stockfishMove;
  final bool soundsEnabled;
  final String boardTheme;
  final String soundPack;

  @override
  State<OfflineBoardPage> createState() => _OfflineBoardPageState();
}

class _OfflineBoardPageState extends State<OfflineBoardPage> {
  final _game = chess.Chess();
  final _repository = OfflineGameRepository();
  final _id = DateTime.now().microsecondsSinceEpoch.toString();
  String? _selected;
  bool _reportedVictory = false;
  bool _botThinking = false;
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

  Future<void> _tap(String square) async {
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
    var promotion = 'q';
    final piece = _game.get(_selected!);
    if (piece?.type.name == 'p' &&
        (square.endsWith('8') || square.endsWith('1'))) {
      promotion = await showDialog<String>(
              context: context,
              builder: (_) => AlertDialog(
                    title: const Text('Promote pawn to'),
                    content: Wrap(
                        spacing: 8,
                        children: ['q', 'r', 'b', 'n']
                            .map((value) => ActionChip(
                                label: Text({
                                  'q': 'Queen',
                                  'r': 'Rook',
                                  'b': 'Bishop',
                                  'n': 'Knight'
                                }[value]!),
                                onPressed: () => Navigator.pop(context, value)))
                            .toList()),
                  )) ??
          '';
      if (promotion.isEmpty || !mounted) return;
    }
    final moved =
        _game.move({'from': _selected, 'to': square, 'promotion': promotion});
    setState(() => _selected = moved ? null : square);
    if (moved && widget.soundsEnabled && widget.soundPack != 'silent') {
      SystemSound.play(widget.soundPack == 'soft'
          ? SystemSoundType.alert
          : SystemSoundType.click);
    }
    if (moved) {
      await _checkResult();
    }
    if (moved && widget.mode == OfflinePlayMode.bot && !_game.game_over) {
      Future<void>.delayed(const Duration(milliseconds: 350), _playBotMove);
    }
  }

  Future<void> _playBotMove() async {
    if (!mounted || _game.game_over) return;
    final moves = _game.moves({'verbose': true});
    if (moves.isEmpty) return;
    setState(() => _botThinking = true);
    dynamic move;
    try {
      final uci = await widget.stockfishMove?.call(_game.fen, widget.botLevel);
      if (uci != null && uci.length >= 4) {
        move = {
          'from': uci.substring(0, 2),
          'to': uci.substring(2, 4),
          if (uci.length > 4) 'promotion': uci.substring(4, 5),
        };
      }
    } catch (_) {
      // The local fallback keeps bot games playable when the server is offline.
    }
    move ??= _chooseBotMove(moves.cast<Map>());
    if (!mounted) return;
    setState(() {
      _game.move(move);
      _botThinking = false;
    });
    if (widget.soundsEnabled && widget.soundPack != 'silent') {
      SystemSound.play(widget.soundPack == 'soft'
          ? SystemSoundType.alert
          : SystemSoundType.click);
    }
    _checkResult();
  }

  dynamic _chooseBotMove(List<Map> moves) {
    if (widget.botLevel <= 1 || widget.botPersonality == 'unpredictable') {
      return moves[Random().nextInt(moves.length)];
    }
    const values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0};
    moves.sort((a, b) {
      int score(Map move) {
        var value = (values[move['captured']] ?? 0) * 10;
        final san = move['san']?.toString() ?? '';
        if (san.contains('+')) {
          value += widget.botPersonality == 'aggressive'
              ? widget.botLevel * 3
              : widget.botLevel;
        }
        if (widget.botPersonality == 'defensive' && san.contains('O-O')) {
          value += 10;
        }
        if (widget.botPersonality == 'positional' &&
            ['d4', 'e4', 'd5', 'e5'].contains(move['to'])) {
          value += 6;
        }
        return value;
      }
      final aScore = score(a);
      final bScore = score(b);
      return bScore.compareTo(aScore);
    });
    final pool = max(1, 5 - widget.botLevel ~/ 2);
    return moves[Random().nextInt(min(pool, moves.length))];
  }

  Future<void> _checkResult() async {
    if (!_game.game_over || _reportedVictory) return;
    _reportedVictory = true;
    final whiteWon = _game.turn == chess.Chess.BLACK;
    final playerWon = whiteWon == _playerIsWhite;
    final isDraw = !_game.in_checkmate;
    final unlocked = playerWon && widget.mode == OfflinePlayMode.bot
        ? await widget.onBotVictory?.call(widget.botLevel)
        : null;
    if (!mounted) return;
    final action = await showGameResultDialog(context,
        outcome: isDraw
            ? PlayerGameOutcome.draw
            : widget.mode == OfflinePlayMode.friend
                ? PlayerGameOutcome.complete
                : playerWon
                    ? PlayerGameOutcome.win
                    : PlayerGameOutcome.loss,
        score: isDraw
            ? '½ – ½'
            : whiteWon
                ? '1 – 0'
                : '0 – 1',
        message: unlocked != null && unlocked > widget.botLevel
            ? 'Level $unlocked is now unlocked. Your next challenge is ready.'
            : null);
    if (!mounted) return;
    if (action == GameResultAction.home) {
      Navigator.of(context).popUntil((route) => route.isFirst);
    } else if (action == GameResultAction.newGame) {
      Navigator.of(context).pushReplacement(MaterialPageRoute(
          builder: (_) => OfflineBoardPage(
              mode: widget.mode,
              preferredSide: widget.preferredSide,
              botLevel: widget.botLevel,
              botPersonality: widget.botPersonality,
              onBotVictory: widget.onBotVictory,
              stockfishMove: widget.stockfishMove,
              soundsEnabled: widget.soundsEnabled,
              boardTheme: widget.boardTheme,
              soundPack: widget.soundPack)));
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
            Text(_botThinking
                ? 'Stockfish is thinking...'
                : '${_game.turn == chess.Chess.WHITE ? 'White' : 'Black'} to move'),
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
                      final palette = switch (widget.boardTheme) {
                        'classic' => dark
                            ? const Color(0xff765f40)
                            : const Color(0xffeee2cd),
                        'midnight' => dark
                            ? const Color(0xff374653)
                            : const Color(0xffb8c1c8),
                        _ => dark
                            ? const Color(0xff63845d)
                            : const Color(0xffe8efd9),
                      };
                      final pieceName = piece == null
                          ? 'empty'
                          : '${piece.color == chess.Color.WHITE ? 'white' : 'black'} ${piece.type.name}';
                      return Semantics(
                          button: true,
                          selected: _selected == square,
                          label: '$square, $pieceName',
                          hint: piece == null
                              ? 'Empty square'
                              : 'Double tap to select or move',
                          child: InkWell(
                            key: ValueKey('board-square-$square'),
                            onTap: () => _tap(square),
                            child: Container(
                              color:
                                  _selected == square ? Colors.amber : palette,
                              alignment: Alignment.center,
                              child: ExcludeSemantics(
                                  child: LayoutBuilder(
                                builder: (_, box) => Text(
                                  _symbol(piece?.type.name,
                                      piece?.color == chess.Color.WHITE),
                                  style:
                                      TextStyle(fontSize: box.maxWidth * .58),
                                ),
                              )),
                            ),
                          ));
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
