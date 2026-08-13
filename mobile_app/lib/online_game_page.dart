import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:chess/chess.dart' as chess;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class OnlineGamePage extends StatefulWidget {
  const OnlineGamePage({
    super.key,
    required this.serverUrl,
    required this.initialGame,
    required this.accessTokenProvider,
    this.sessionCookie,
    this.soundsEnabled = true,
  });

  final String serverUrl;
  final Map<String, dynamic> initialGame;
  final Future<String?> Function() accessTokenProvider;
  final String? sessionCookie;
  final bool soundsEnabled;

  @override
  State<OnlineGamePage> createState() => _OnlineGamePageState();
}

class _OnlineGamePageState extends State<OnlineGamePage> {
  WebSocket? _socket;
  Timer? _clockTimer;
  Timer? _reconnectTimer;
  late Map<String, dynamic> _game;
  String? _selected;
  String? _error;
  bool _connecting = true;
  bool _disposed = false;
  int _reconnectAttempt = 0;
  DateTime _stateReceivedAt = DateTime.now();

  String get _viewerColor =>
      ((_game['viewer'] as Map?)?['color'] as String?) ?? '';
  bool get _whiteView => _viewerColor != 'black';
  bool get _active => _game['status'] == 'active';

  @override
  void initState() {
    super.initState();
    _game = Map<String, dynamic>.from(widget.initialGame);
    _connect();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && _active) setState(() {});
    });
  }

  Future<void> _connect() async {
    if (_disposed) return;
    setState(() => _connecting = true);
    try {
      final token = await widget.accessTokenProvider();
      final base = Uri.parse(widget.serverUrl);
      final uri = base.replace(
        scheme: base.scheme == 'https' ? 'wss' : 'ws',
        path: '/ws/games/${_game['id']}/',
      );
      final headers = <String, dynamic>{};
      if (token != null) {
        headers[HttpHeaders.authorizationHeader] = 'Bearer $token';
      }
      if (widget.sessionCookie != null) {
        headers[HttpHeaders.cookieHeader] = widget.sessionCookie!;
      }
      final socket = await WebSocket.connect(
        uri.toString(),
        headers: headers.isEmpty ? null : headers,
      );
      if (_disposed) {
        await socket.close();
        return;
      }
      _socket = socket;
      _reconnectAttempt = 0;
      setState(() {
        _connecting = false;
        _error = null;
      });
      socket.listen(_receive, onDone: _connectionLost, onError: (_) => _connectionLost());
    } catch (_) {
      _connectionLost();
    }
  }

  void _receive(dynamic message) {
    final data = jsonDecode(message as String) as Map<String, dynamic>;
    if (data['game'] is Map) {
      final previousPly = (_game['ply_count'] as num?)?.toInt() ?? 0;
      final incoming = Map<String, dynamic>.from(data['game'] as Map);
      if (widget.soundsEnabled && ((incoming['ply_count'] as num?)?.toInt() ?? 0) > previousPly) {
        SystemSound.play(SystemSoundType.click);
      }
      setState(() {
        _game = incoming;
        _stateReceivedAt = DateTime.now();
        _selected = null;
        _error = null;
      });
    } else if (data['type'] == 'error') {
      setState(() => _error = data['message']?.toString() ?? 'Game action failed.');
    }
  }

  void _connectionLost() {
    if (_disposed || _reconnectTimer?.isActive == true) return;
    _socket = null;
    final delay = Duration(seconds: 1 << _reconnectAttempt.clamp(0, 4));
    _reconnectAttempt++;
    if (mounted) setState(() => _connecting = true);
    _reconnectTimer = Timer(delay, _connect);
  }

  void _tapSquare(String square) {
    if (!_active || _socket == null || _viewerColor != _game['turn']) return;
    final board = chess.Chess.fromFEN(_game['fen'] as String);
    if (_selected == null) {
      final piece = board.get(square);
      final viewerIsWhite = _viewerColor == 'white';
      if (piece != null && (piece.color == chess.Color.WHITE) == viewerIsWhite) {
        setState(() => _selected = square);
      }
      return;
    }
    final uci = '$_selected$square${_promotionSuffix(board, _selected!, square)}';
    final legal = ((_game['legal_moves'] as List?) ?? const []).map((move) {
      if (move is Map) return move['uci']?.toString() ?? '';
      return move.toString();
    });
    if (legal.contains(uci) || legal.contains('$_selected$square')) {
      _send('game.move', {'uci': uci, 'client_lag_ms': 0});
      setState(() => _selected = null);
    } else {
      setState(() => _selected = square);
    }
  }

  String _promotionSuffix(chess.Chess board, String from, String to) {
    final piece = board.get(from);
    if (piece?.type.name == 'p' && (to.endsWith('8') || to.endsWith('1'))) return 'q';
    return '';
  }

  void _send(String type, [Map<String, dynamic> values = const {}]) {
    _socket?.add(jsonEncode({'type': type, ...values}));
  }

  int _timeFor(String color) {
    final player = (_game[color] as Map?) ?? const {};
    var milliseconds = (player['time_ms'] as num?)?.toInt() ?? 0;
    if (_active && _game['turn'] == color) {
      milliseconds -= DateTime.now().difference(_stateReceivedAt).inMilliseconds;
    }
    return milliseconds.clamp(0, 1 << 31);
  }

  String _clock(int milliseconds) {
    final seconds = milliseconds ~/ 1000;
    final minutes = seconds ~/ 60;
    return '$minutes:${(seconds % 60).toString().padLeft(2, '0')}';
  }

  @override
  void dispose() {
    _disposed = true;
    _clockTimer?.cancel();
    _reconnectTimer?.cancel();
    _socket?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final top = _whiteView ? 'black' : 'white';
    final bottom = _whiteView ? 'white' : 'black';
    final moves = (_game['moves'] as List?) ?? const [];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Online Game'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(_connecting ? Icons.sync : Icons.cloud_done,
                color: _connecting ? Colors.orange : Colors.green),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            _PlayerBar(name: ((_game[top] as Map?)?['name'] ?? top).toString(), clock: _clock(_timeFor(top))),
            const SizedBox(height: 8),
            AspectRatio(aspectRatio: 1, child: _board()),
            const SizedBox(height: 8),
            _PlayerBar(name: ((_game[bottom] as Map?)?['name'] ?? bottom).toString(), clock: _clock(_timeFor(bottom))),
            if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
            if (!_active)
              Card(child: Padding(padding: const EdgeInsets.all(16), child: Text('Game finished · ${_game['result']} · ${_game['termination']}'))),
            SizedBox(
              height: 54,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: moves.length,
                separatorBuilder: (_, __) => const SizedBox(width: 6),
                itemBuilder: (_, index) => Chip(label: Text((moves[index] as Map)['san']?.toString() ?? '')),
              ),
            ),
            Wrap(spacing: 8, alignment: WrapAlignment.center, children: [
              OutlinedButton(onPressed: _active ? () => _send('game.draw') : null, child: const Text('Offer draw')),
              OutlinedButton(onPressed: _active ? () => _confirmAction('Resign game?', 'game.resign') : null, child: const Text('Resign')),
              OutlinedButton(onPressed: _active ? () => _confirmAction('Abort game?', 'game.abort') : null, child: const Text('Abort')),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _board() => GridView.builder(
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 8),
        itemCount: 64,
        itemBuilder: (_, index) {
          final displayFile = index % 8;
          final displayRank = index ~/ 8;
          final file = _whiteView ? displayFile : 7 - displayFile;
          final rank = _whiteView ? 8 - displayRank : displayRank + 1;
          final square = '${String.fromCharCode(97 + file)}$rank';
          final board = chess.Chess.fromFEN(_game['fen'] as String);
          final piece = board.get(square);
          final dark = (file + rank).isOdd;
          final lastMove = (_game['last_move_uci'] ?? '').toString();
          final highlighted = _selected == square ||
              (lastMove.length >= 4 && (lastMove.substring(0, 2) == square || lastMove.substring(2, 4) == square));
          return InkWell(
            onTap: () => _tapSquare(square),
            child: Container(
              color: highlighted ? Colors.amber.shade400 : (dark ? const Color(0xff769656) : const Color(0xffeeeed2)),
              alignment: Alignment.center,
              child: Text(_piece(piece?.type.name, piece?.color == chess.Color.WHITE), style: const TextStyle(fontSize: 34)),
            ),
          );
        },
      );

  Future<void> _confirmAction(String title, String event) async {
    final confirmed = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(title),
      actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirm'))],
    ));
    if (confirmed == true) _send(event);
  }

  String _piece(String? type, bool white) {
    const whitePieces = {'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔'};
    const blackPieces = {'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'};
    return (white ? whitePieces : blackPieces)[type] ?? '';
  }
}

class _PlayerBar extends StatelessWidget {
  const _PlayerBar({required this.name, required this.clock});
  final String name;
  final String clock;

  @override
  Widget build(BuildContext context) => Row(children: [
        const CircleAvatar(child: Icon(Icons.person)),
        const SizedBox(width: 10),
        Expanded(child: Text(name, style: Theme.of(context).textTheme.titleMedium)),
        Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), decoration: BoxDecoration(color: const Color(0xff173b2a), borderRadius: BorderRadius.circular(10)), child: Text(clock, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold))),
      ]);
}
