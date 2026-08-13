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
    expect(find.text('Chess Platform'), findsOneWidget);
    expect(find.text('Login'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Play with Bot'), 300,
        scrollable: find.byType(Scrollable).first);
    expect(find.text('Play with Bot'), findsOneWidget);
    expect(find.text('Play with Friend'), findsOneWidget);
  });
}
