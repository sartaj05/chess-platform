import 'dart:async';
import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';

class GameReplayPage extends StatefulWidget {
  const GameReplayPage(
      {super.key,
      required this.game,
      required this.startAnalysis,
      required this.analysisStatus,
      required this.retryAnalysis});
  final Map<String, dynamic> game;
  final Future<Map<String, dynamic>> Function(String gameId) startAnalysis;
  final Future<Map<String, dynamic>> Function(String jobId) analysisStatus;
  final Future<Map<String, dynamic>> Function(String jobId) retryAnalysis;
  @override
  State<GameReplayPage> createState() => _GameReplayPageState();
}

class _GameReplayPageState extends State<GameReplayPage> {
  int _ply = 0;
  Map<String, dynamic>? _analysis;
  bool _analysing = false;
  String? _error;
  List get _moves => widget.game['moves'] as List? ?? const [];
  chess.Chess _position() {
    final game = chess.Chess.fromFEN(
        widget.game['initial_fen']?.toString() ?? chess.Chess.DEFAULT_POSITION);
    for (var i = 0; i < _ply && i < _moves.length; i++) {
      game.move((_moves[i] as Map)['uci']?.toString());
    }
    return game;
  }

  Future<void> _analyse() async {
    setState(() {
      _analysing = true;
      _error = null;
    });
    try {
      final job = await widget.startAnalysis(widget.game['id'].toString());
      final id = job['id'].toString();
      for (var i = 0; i < 60; i++) {
        final state = await widget.analysisStatus(id);
        if (!mounted) return;
        setState(() => _analysis = state);
        if (state['status'] == 'completed' || state['status'] == 'failed') {
          break;
        }
        await Future<void>.delayed(const Duration(seconds: 2));
      }
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _analysing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final board = _position();
    final reviewRows = _analysis?['reviews'] as List? ?? const [];
    return Scaffold(
        appBar: AppBar(title: const Text('Game Replay')),
        body: ListView(padding: const EdgeInsets.all(12), children: [
          Text(
              '${widget.game['white_display_name']} vs ${widget.game['black_display_name']}',
              style: Theme.of(context).textTheme.titleLarge),
          Text('Move $_ply of ${_moves.length}'),
          const SizedBox(height: 10),
          AspectRatio(
              aspectRatio: 1,
              child: GridView.builder(
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 8),
                  itemCount: 64,
                  itemBuilder: (_, index) {
                    final file = index % 8,
                        rank = 7 - index ~/ 8,
                        square = '${String.fromCharCode(97 + file)}${rank + 1}',
                        piece = board.get(square),
                        dark = (file + rank).isOdd;
                    return Container(
                        color: dark
                            ? const Color(0xff769656)
                            : const Color(0xffeeeed2),
                        alignment: Alignment.center,
                        child: Text(
                            _symbol(piece?.type.name,
                                piece?.color == chess.Color.WHITE),
                            style: const TextStyle(fontSize: 34)));
                  })),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            IconButton(
                onPressed: _ply > 0 ? () => setState(() => _ply--) : null,
                icon: const Icon(Icons.chevron_left)),
            IconButton(
                onPressed:
                    _ply < _moves.length ? () => setState(() => _ply++) : null,
                icon: const Icon(Icons.chevron_right))
          ]),
          FilledButton.icon(
              onPressed: _analysing ? null : _analyse,
              icon: const Icon(Icons.analytics),
              label: Text(
                  _analysing ? 'Analysing with Stockfish...' : 'Analyse game')),
          if (_analysis?['status'] == 'failed')
            OutlinedButton.icon(
                onPressed: () async {
                  final id = _analysis?['id']?.toString();
                  if (id != null) {
                    await widget.retryAnalysis(id);
                    await _analyseStatus(id);
                  }
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Retry analysis')),
          if ((_analysis?['summary'] as Map?)?['accuracy'] is Map)
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(
                        'Accuracy · White ${(_analysis!['summary'] as Map)['accuracy']['white']}% · Black ${(_analysis!['summary'] as Map)['accuracy']['black']}%'))),
          if (((_analysis?['summary'] as Map?)?['evaluation'] as List?)
                  ?.isNotEmpty ==
              true)
            SizedBox(
                height: 150,
                child: CustomPaint(
                    painter: _EvaluationPainter(((_analysis!['summary']
                        as Map)['evaluation'] as List)))),
          if (_error != null)
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ...reviewRows.map((row) => ListTile(
              title: Text('${row['ply_number']}. ${row['move_san']}'),
              subtitle: Text(
                  '${row['comment'] ?? ''}\nBest: ${row['bestmove_san'] ?? row['bestmove_uci'] ?? ''} · Line: ${((row['best_line'] as List?) ?? const []).take(6).join(' ')}'),
              trailing:
                  Chip(label: Text(row['classification']?.toString() ?? ''))))
        ]));
  }

  String _symbol(String? type, bool white) {
    const w = {'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔'},
        b = {'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'};
    return (white ? w : b)[type] ?? '';
  }

  Future<void> _analyseStatus(String id) async {
    for (var i = 0; i < 60; i++) {
      final state = await widget.analysisStatus(id);
      if (!mounted) return;
      setState(() => _analysis = state);
      if (state['status'] == 'completed' || state['status'] == 'failed') return;
      await Future<void>.delayed(const Duration(seconds: 2));
    }
  }
}

class _EvaluationPainter extends CustomPainter {
  _EvaluationPainter(this.points);
  final List points;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawLine(Offset(0, size.height / 2),
        Offset(size.width, size.height / 2), Paint()..color = Colors.grey);
    if (points.length < 2) return;
    final path = Path();
    for (var i = 0; i < points.length; i++) {
      final value =
          ((points[i] as Map)['score_white_cp'] as num?)?.toDouble() ?? 0;
      final x = i * size.width / (points.length - 1);
      final y = size.height / 2 -
          (value.clamp(-1000, 1000) / 1000) * (size.height / 2 - 8);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(
        path,
        Paint()
          ..color = Colors.green
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke);
  }

  @override
  bool shouldRepaint(covariant _EvaluationPainter oldDelegate) =>
      oldDelegate.points != points;
}
