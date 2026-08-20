import 'package:chess_platform_mobile/deep_link_service.dart';
import 'package:chess_platform_mobile/notification_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('notification tap marks read and dispatches its deep link',
      (tester) async {
    MobileLink? opened;
    final subscription = DeepLinkService.links.listen((link) => opened = link);
    addTearDown(subscription.cancel);

    await tester.pumpWidget(MaterialApp(
      home: NotificationPage(
        load: () async => [
          {
            'id': 8,
            'title': 'Your move',
            'message': 'Return to the board',
            'is_read': false,
            'target_url': '/games/game-42/',
          }
        ],
        markRead: (_) async {},
        markAllRead: () async {},
      ),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Your move'));
    await tester.pump();

    expect(opened?.destination, MobileDestination.game);
    expect(opened?.id, 'game-42');
  });
}
