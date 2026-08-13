import 'dart:async';
import 'package:flutter/material.dart';

class MatchmakingPage extends StatefulWidget {
  const MatchmakingPage(
      {super.key,
      required this.enter,
      required this.status,
      required this.cancel,
      required this.openRoom});
  final Future<Map<String, dynamic>> Function(String category) enter;
  final Future<Map<String, dynamic>> Function(String category) status;
  final Future<void> Function() cancel;
  final Future<void> Function(Map<String, dynamic> room) openRoom;
  @override
  State<MatchmakingPage> createState() => _MatchmakingPageState();
}

class _MatchmakingPageState extends State<MatchmakingPage> {
  Timer? _timer;
  String _message = 'Searching for a close-rated opponent...';
  bool _opening = false;
  bool _searching = false;
  String _category = 'blitz';

  Future<void> _start() async {
    try {
      setState(() => _searching = true);
      final result = await widget.enter(_category);
      await _handle(result);
      _timer = Timer.periodic(const Duration(seconds: 2), (_) => _poll());
    } catch (e) {
      if (mounted) setState(() => _message = '$e');
    }
  }

  Future<void> _poll() async {
    try {
      await _handle(await widget.status(_category));
    } catch (_) {}
  }

  Future<void> _handle(Map<String, dynamic> result) async {
    if (_opening) return;
    final room = result['room'];
    if (result['wait_seconds'] != null && mounted) {
      setState(() => _message =
          'Searching · ${result['wait_seconds']}s · rating range ±${result['rating_window']}');
    }
    if (result['matched'] == true && room is Map) {
      _opening = true;
      _timer?.cancel();
      await widget.openRoom(Map<String, dynamic>.from(room));
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Rated Matchmaking')),
      body: Center(
          child: Padding(
              padding: const EdgeInsets.all(28),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                if (!_searching)
                  SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(value: 'bullet', label: Text('Bullet')),
                        ButtonSegment(value: 'blitz', label: Text('Blitz')),
                        ButtonSegment(value: 'rapid', label: Text('Rapid')),
                      ],
                      selected: {
                        _category
                      },
                      onSelectionChanged: (value) =>
                          setState(() => _category = value.first)),
                if (!_searching) const SizedBox(height: 18),
                if (!_searching)
                  FilledButton.icon(
                      onPressed: _start,
                      icon: const Icon(Icons.search),
                      label: const Text('Find opponent')),
                if (!_searching) const SizedBox(height: 18),
                if (_searching)
                  const SizedBox(
                      width: 70,
                      height: 70,
                      child: CircularProgressIndicator(strokeWidth: 7)),
                const SizedBox(height: 28),
                Text(_message,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                const Text('10 minute rated game · search updates live',
                    textAlign: TextAlign.center),
                const SizedBox(height: 28),
                OutlinedButton(
                    onPressed: () async {
                      await widget.cancel();
                      if (context.mounted) Navigator.pop(context);
                    },
                    child: const Text('Cancel search'))
              ]))));
}
