import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:chess_platform_mobile/main.dart';
import 'package:chess_platform_mobile/deep_link_service.dart';

void main() {
  test('parses supported mobile deep links', () {
    expect(MobileLink.parse('chessplatform://rooms/abc123')?.id, 'ABC123');
    expect(
        MobileLink.parse('https://chess.example.com/games/game-id/')
            ?.destination,
        MobileDestination.game);
    expect(MobileLink.parse('chessplatform://notifications')?.destination,
        MobileDestination.notifications);
  });
  testWidgets('shows simple play choices and opens a friend game',
      (tester) async {
    await tester.pumpWidget(const ChessPlatformApp());

    expect(find.text('Login'), findsWidgets);
    expect(find.text('Create Account'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Play with Friend'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Choose your side'), findsOneWidget);
    expect(find.text('Bot Challenge'), findsOneWidget);
    expect(find.text('Play with Friend'), findsOneWidget);

    await tester.tap(find.text('Play with Friend'));
    await tester.pumpAndSettle();

    expect(find.text('Play with Friend'), findsOneWidget);
    expect(find.text('White to move'), findsOneWidget);
    expect(find.text('Save offline game'), findsOneWidget);
  });
}
