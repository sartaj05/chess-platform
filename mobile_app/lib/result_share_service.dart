import 'package:flutter/services.dart';

class ResultShareService {
  static const _channel = MethodChannel('chess_platform/share');

  static Future<void> shareGame(Map<String, dynamic> game) {
    final white = game['white_display_name'] ?? 'White';
    final black = game['black_display_name'] ?? 'Black';
    final result = game['result'] ?? '*';
    final moves = game['ply_count'] ?? (game['moves'] as List?)?.length ?? 0;
    final text = '''
CHESS PLATFORM
$white vs $black
Result: $result
Moves: $moves

Played on Chess Platform
''';
    return _channel.invokeMethod<void>('shareResult', {
      'title': '$white vs $black',
      'text': text,
    });
  }
}
