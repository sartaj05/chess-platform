import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';

import 'offline_game_repository.dart';

class OfflineBoardPage extends StatefulWidget {
  const OfflineBoardPage({super.key});

  @override
  State<OfflineBoardPage> createState() => _OfflineBoardPageState();
}

class _OfflineBoardPageState extends State<OfflineBoardPage> {
  final _game = chess.Chess();
  final _repository = OfflineGameRepository();
  final _id = DateTime.now().microsecondsSinceEpoch.toString();
  String? _selected;

  void _tap(String square) {
    if (_selected == null) {
      if (_game.get(square) != null) setState(() => _selected = square);
      return;
    }
    final moved = _game.move({'from': _selected, 'to': square, 'promotion': 'q'});
    setState(() => _selected = moved ? null : square);
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
        appBar: AppBar(title: const Text('Offline same-device chess')),
        body: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Text('${_game.turn == chess.Chess.WHITE ? 'White' : 'Black'} to move'),
            const SizedBox(height: 12),
            AspectRatio(
              aspectRatio: 1,
              child: GridView.builder(
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 8),
                itemCount: 64,
                itemBuilder: (_, index) {
                  final file = index % 8;
                  final rank = 8 - index ~/ 8;
                  final square = '${String.fromCharCode(97 + file)}$rank';
                  final piece = _game.get(square);
                  final dark = (file + rank).isOdd;
                  return InkWell(
                    onTap: () => _tap(square),
                    child: Container(
                      color: _selected == square ? Colors.amber : (dark ? const Color(0xff769656) : const Color(0xffeeeed2)),
                      alignment: Alignment.center,
                      child: Text(_symbol(piece?.type.name, piece?.color == chess.Color.WHITE), style: const TextStyle(fontSize: 34)),
                    ),
                  );
                },
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
    const whitePieces = {'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔'};
    const blackPieces = {'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'};
    return (white ? whitePieces : blackPieces)[type] ?? '';
  }
}
