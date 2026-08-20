import 'package:flutter/material.dart';

enum GameResultAction { close, newGame, home }

enum PlayerGameOutcome { win, loss, draw, complete }

Future<GameResultAction?> showGameResultDialog(
  BuildContext context, {
  required PlayerGameOutcome outcome,
  required String score,
  String? message,
}) {
  final win = outcome == PlayerGameOutcome.win;
  final loss = outcome == PlayerGameOutcome.loss;
  final title = win
      ? 'Brilliant. You won!'
      : loss
          ? 'Tough game'
          : outcome == PlayerGameOutcome.draw
              ? 'Game drawn'
              : 'Game complete';
  final color = win
      ? Colors.green.shade700
      : loss
          ? Colors.brown.shade600
          : Colors.blueGrey.shade600;
  return showDialog<GameResultAction>(
    context: context,
    barrierDismissible: false,
    builder: (dialogContext) => Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Stack(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 30, 24, 22),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: .6, end: 1),
              duration: const Duration(milliseconds: 650),
              curve: Curves.elasticOut,
              builder: (_, value, child) =>
                  Transform.scale(scale: value, child: child),
              child: CircleAvatar(
                radius: 39,
                backgroundColor: color.withValues(alpha: .12),
                child: Icon(
                    win
                        ? Icons.emoji_events_rounded
                        : loss
                            ? Icons.sports_esports_outlined
                            : Icons.handshake_outlined,
                    color: color,
                    size: 42),
              ),
            ),
            const SizedBox(height: 16),
            Text(win ? 'VICTORY' : 'FINAL RESULT',
                style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2,
                    fontSize: 11)),
            const SizedBox(height: 6),
            Text(title,
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Text(
                message ??
                    (loss
                        ? 'Every game teaches something. Try again when you are ready.'
                        : 'A strong game. Your result has been saved.'),
                textAlign: TextAlign.center),
            const SizedBox(height: 18),
            Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                    color: color.withValues(alpha: .08),
                    borderRadius: BorderRadius.circular(12)),
                child: Text(score,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w800))),
            const SizedBox(height: 20),
            SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                    onPressed: () =>
                        Navigator.pop(dialogContext, GameResultAction.newGame),
                    icon: const Icon(Icons.add),
                    label: const Text('New game'))),
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              TextButton(
                  onPressed: () =>
                      Navigator.pop(dialogContext, GameResultAction.home),
                  child: const Text('Home')),
              TextButton(
                  onPressed: () =>
                      Navigator.pop(dialogContext, GameResultAction.close),
                  child: const Text('Close'))
            ]),
          ]),
        ),
        Positioned(
            right: 8,
            top: 8,
            child: IconButton(
                tooltip: 'Close',
                onPressed: () =>
                    Navigator.pop(dialogContext, GameResultAction.close),
                icon: const Icon(Icons.close))),
      ]),
    ),
  );
}
