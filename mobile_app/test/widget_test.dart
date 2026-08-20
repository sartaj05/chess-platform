import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:chess_platform_mobile/main.dart';
import 'package:chess_platform_mobile/deep_link_service.dart';

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues(
        {'chess_onboarding_complete_v1': 'true'});
  });

  test('parses supported mobile deep links', () {
    expect(MobileLink.parse('chessplatform://rooms/abc123')?.id, 'ABC123');
    expect(
        MobileLink.parse('https://chess.example.com/games/game-id/')
            ?.destination,
        MobileDestination.game);
    expect(MobileLink.parse('chessplatform://notifications')?.destination,
        MobileDestination.notifications);
    expect(MobileLink.parse('/rooms/abc123/')?.destination,
        MobileDestination.room);
    expect(MobileLink.parse('/players/player-id/')?.destination,
        MobileDestination.profile);
    expect(MobileLink.parse('/games/game-id/')?.destination,
        MobileDestination.game);
    expect(MobileLink.parse('/tournaments/42/')?.destination,
        MobileDestination.tournament);
    expect(MobileLink.parse('/notifications/')?.destination,
        MobileDestination.notifications);
  });
  testWidgets('shows simple play choices and opens a friend game',
      (tester) async {
    await tester.pumpWidget(const ChessPlatformApp());
    await tester.pumpAndSettle();

    expect(find.text('Login'), findsWidgets);
    expect(find.text('Create Account'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Play with Friend'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Choose your side'), findsOneWidget);
    expect(find.text('Play with Bot'), findsOneWidget);
    expect(find.text('Play with Friend'), findsOneWidget);

    await tester.tap(find.text('Play with Friend'));
    await tester.pumpAndSettle();

    expect(find.text('Play with Friend'), findsOneWidget);
    expect(find.text('White to move'), findsOneWidget);
    expect(find.text('Save offline game'), findsOneWidget);
  });

  testWidgets('home remains usable on a narrow phone', (tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const ChessPlatformApp());
    await tester.pumpAndSettle();

    expect(find.text('Chess Platform'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('home uses a stable tablet content width', (tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const ChessPlatformApp());
    await tester.pumpAndSettle();

    expect(find.text('Chess Platform'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
