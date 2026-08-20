import 'package:flutter/material.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key, required this.onComplete});
  final Future<void> Function() onComplete;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  static const _lessons = [
    ('Your first move', 'Move the highlighted pawn from e2 to e4.', 'e2', 'e4'),
    (
      'Castle safely',
      'Tap the king, then its highlighted castling square.',
      'e1',
      'g1'
    ),
    (
      'Promote a pawn',
      'Guide the pawn to the last rank and choose a queen.',
      'a7',
      'a8'
    ),
    (
      'Deliver checkmate',
      'Move the queen to the highlighted mating square.',
      'h5',
      'f7'
    ),
  ];
  int _lesson = 0;
  String? _selected;
  final Set<int> _completed = {};

  Future<void> _tap(String square) async {
    final lesson = _lessons[_lesson];
    if (_selected == null) {
      if (square == lesson.$3) setState(() => _selected = square);
      return;
    }
    if (square != lesson.$4) {
      setState(() => _selected = null);
      return;
    }
    _completed.add(_lesson);
    if (_lesson == _lessons.length - 1) {
      await widget.onComplete();
    } else {
      setState(() {
        _lesson++;
        _selected = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final lesson = _lessons[_lesson];
    return Scaffold(
      bottomNavigationBar: SafeArea(
        child: TextButton(
            onPressed: widget.onComplete, child: const Text('Skip tutorial')),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(padding: const EdgeInsets.all(24), children: [
              const Icon(Icons.sports_esports, size: 54),
              const SizedBox(height: 12),
              Text('Learn by playing',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium),
              const Text('Four quick lessons before your first real game.',
                  textAlign: TextAlign.center),
              const SizedBox(height: 22),
              LinearProgressIndicator(value: (_lesson + 1) / _lessons.length),
              const SizedBox(height: 20),
              Text('Step ${_lesson + 1} of ${_lessons.length}',
                  style: Theme.of(context).textTheme.labelLarge),
              Text(lesson.$1, style: Theme.of(context).textTheme.titleLarge),
              Text(lesson.$2),
              const SizedBox(height: 16),
              Center(
                child: SizedBox.square(
                  dimension: (MediaQuery.sizeOf(context).height * .48)
                      .clamp(260.0, 380.0),
                  child: _LessonBoard(
                      source: lesson.$3,
                      target: lesson.$4,
                      selected: _selected,
                      onTap: _tap),
                ),
              ),
              const SizedBox(height: 18),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.workspace_premium),
                  title: const Text('First Steps reward'),
                  subtitle: Text(
                      '${_completed.length}/${_lessons.length} lessons · Complete all to unlock your badge'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _LessonBoard extends StatelessWidget {
  const _LessonBoard(
      {required this.source,
      required this.target,
      required this.selected,
      required this.onTap});
  final String source;
  final String target;
  final String? selected;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 1,
        child: GridView.builder(
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 8),
          itemCount: 64,
          itemBuilder: (_, index) {
            final file = index % 8;
            final rank = 7 - index ~/ 8;
            final square = '${String.fromCharCode(97 + file)}${rank + 1}';
            final highlighted = square == source || square == target;
            final piece = square == source ? _lessonPiece(source) : '';
            return InkWell(
              key: ValueKey('lesson-square-$square'),
              onTap: () => onTap(square),
              child: Container(
                color: selected == square
                    ? const Color(0xffffd166)
                    : highlighted
                        ? const Color(0xffa7d78b)
                        : (file + rank).isOdd
                            ? const Color(0xff769656)
                            : const Color(0xffeeeed2),
                alignment: Alignment.center,
                child: Text(piece, style: const TextStyle(fontSize: 30)),
              ),
            );
          },
        ),
      );

  static String _lessonPiece(String square) => switch (square) {
        'e1' => '♔',
        'h5' => '♕',
        _ => '♙',
      };
}
