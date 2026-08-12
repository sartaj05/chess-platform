import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:chess_platform_mobile/main.dart';

void main() {
  testWidgets('shows simple play choices and opens a friend game',
      (tester) async {
    await tester.pumpWidget(const ChessPlatformApp());

    expect(find.text('Login'), findsWidgets);
    expect(find.text('Create Account'), findsOneWidget);
    expect(find.text('Choose your side'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Play with Friend'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Play with Bot'), findsOneWidget);
    expect(find.text('Play with Friend'), findsOneWidget);

    await tester.tap(find.text('Play with Friend'));
    await tester.pumpAndSettle();

    expect(find.text('Play with Friend'), findsOneWidget);
    expect(find.text('White to move'), findsOneWidget);
    expect(find.text('Save offline game'), findsOneWidget);
  });
}
