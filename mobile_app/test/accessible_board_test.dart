import 'package:chess_platform_mobile/offline_board_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('offline board fits landscape and exposes semantic squares',
      (tester) async {
    tester.view.physicalSize = const Size(1000, 600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(const MaterialApp(
      home: OfflineBoardPage(soundsEnabled: false),
    ));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('board-square-e2')), findsOneWidget);
    expect(find.bySemanticsLabel('e2, white p'), findsOneWidget);
    expect(tester.takeException(), isNull);
    semantics.dispose();
  });
}
