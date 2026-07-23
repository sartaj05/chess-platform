import 'package:flutter_test/flutter_test.dart';

import 'package:chess_platform_mobile/main.dart';

void main() {
  testWidgets('shows the offline LAN lobby', (WidgetTester tester) async {
    await tester.pumpWidget(const ChessPlatformApp());

    expect(find.text('Chess Platform — Offline LAN'), findsOneWidget);
    expect(find.text('Refresh public rooms'), findsOneWidget);
  });
}
