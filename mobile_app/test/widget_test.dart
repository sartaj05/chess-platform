import 'package:flutter_test/flutter_test.dart';

import 'package:chess_platform_mobile/main.dart';

void main() {
  testWidgets('shows the offline LAN lobby and room join action',
      (tester) async {
    await tester.pumpWidget(const ChessPlatformApp());

    expect(find.text('Refresh public rooms'), findsOneWidget);
    expect(find.text('Join room'), findsOneWidget);
  });
}
