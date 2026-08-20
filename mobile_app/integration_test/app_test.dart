import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:integration_test/integration_test.dart';
import 'package:chess_platform_mobile/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('launches, scrolls, and exposes the primary play controls',
      (tester) async {
    await app.main();
    await tester.pumpAndSettle();
    if (find.text('Skip tutorial').evaluate().isNotEmpty) {
      await tester.tap(find.text('Skip tutorial'));
      await tester.pumpAndSettle();
    }
    expect(find.text('Chess Platform'), findsOneWidget);
    expect(find.text('Login'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Play with Bot'), 300,
        scrollable: find.byType(Scrollable).first);
    expect(find.text('Play with Bot'), findsOneWidget);
    expect(find.text('Play with Friend'), findsOneWidget);
    await tester.tap(find.text('Play with Friend'));
    await tester.pumpAndSettle();
    expect(find.text('White to move'), findsOneWidget);
    expect(find.text('Save offline game'), findsOneWidget);

    for (final move in const [
      ['f2', 'f3'],
      ['e7', 'e5'],
      ['g2', 'g4'],
      ['d8', 'h4'],
    ]) {
      await tester.tap(find.byKey(ValueKey('board-square-${move[0]}')));
      await tester.tap(find.byKey(ValueKey('board-square-${move[1]}')));
      await tester.pumpAndSettle();
    }
    expect(find.text('Game complete'), findsOneWidget);
    expect(find.text('0 – 1'), findsOneWidget);
    expect(find.text('New game'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
  });
}
