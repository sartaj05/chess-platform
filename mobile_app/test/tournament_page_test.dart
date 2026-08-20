import 'package:chess_platform_mobile/tournament_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('organizer sees tournament share and management controls',
      (tester) async {
    final managed = <Map<String, dynamic>>[];
    Future<List<Map<String, dynamic>>> load() async => [
          {
            'id': 4,
            'name': 'Mobile Cup',
            'format': 'swiss',
            'time_control': '10+0',
            'player_count': 2,
            'max_players': 8,
            'invite_code': 'ABCD1234',
            'description': 'Android tournament',
            'standings': <dynamic>[],
            'is_organizer': true,
            'status': 'registration',
          }
        ];

    await tester.pumpWidget(MaterialApp(
      home: TournamentPage(
        load: load,
        action: (_, __) async {},
        create: (values) async => values,
        manage: (id, values) async {
          managed.add(values);
          return values;
        },
      ),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mobile Cup'));
    await tester.pumpAndSettle();

    expect(find.text('ABCD1234'), findsOneWidget);
    expect(find.text('Start'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
    expect(find.text('Announce'), findsOneWidget);
    await tester.tap(find.text('Start'));
    await tester.pumpAndSettle();
    expect(managed.single['action'], 'start');
  });
}
