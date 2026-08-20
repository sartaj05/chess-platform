import 'package:chess_platform_mobile/social_pages.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('mobile chat exposes edit delete and unsend actions', (tester) async {
    final actions = <Map<String, dynamic>>[];
    final social = <String, dynamic>{
      'friendships': <dynamic>[],
      'conversations': [
        {
          'id': 7,
          'player': {'id': 'player-2', 'display_name': 'Alex'},
          'messages': [
            {
              'id': 41,
              'body': 'Ready to play?',
              'mine': true,
              'unsent': false,
              'can_edit': true,
              'can_delete': true,
              'can_unsend': true,
            }
          ]
        }
      ]
    };
    Future<Map<String, dynamic>> load() async => social;
    Future<void> action(Map<String, dynamic> value) async => actions.add(value);

    await tester.pumpWidget(MaterialApp(home: SocialPage(load: load, action: action)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alex'));
    await tester.pumpAndSettle();

    expect(find.text('Ready to play?'), findsOneWidget);
    await tester.tap(find.byType(PopupMenuButton<String>));
    await tester.pumpAndSettle();
    expect(find.text('Edit'), findsOneWidget);
    expect(find.text('Delete for me'), findsOneWidget);
    expect(find.text('Unsend for everyone'), findsOneWidget);

    await tester.tap(find.text('Unsend for everyone'));
    await tester.pumpAndSettle();
    expect(actions.single['action'], 'unsend_message');
    expect(actions.single['conversation_id'], 7);
    expect(actions.single['message_id'], 41);
  });
}
