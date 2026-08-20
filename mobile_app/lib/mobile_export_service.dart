import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

class MobileExportService {
  static Future<String> saveText(String filename, String content) async {
    final directory = await getApplicationDocumentsDirectory();
    final safeName = filename.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
    final file = File(path.join(directory.path, safeName));
    await file.writeAsString(content, flush: true);
    await Clipboard.setData(ClipboardData(text: content));
    return file.path;
  }

  static Future<String> saveGame(Map<String, dynamic> game, String format) {
    final id = game['id']?.toString() ?? 'game';
    if (format == 'fen') {
      return saveText('$id.fen',
          game['current_fen']?.toString() ?? game['fen']?.toString() ?? '');
    }
    return saveText('$id.pgn',
        game['cached_pgn']?.toString() ?? game['pgn']?.toString() ?? '');
  }

  static Future<String> saveAccount(Map<String, dynamic> data) => saveText(
      'chess-platform-data.json',
      const JsonEncoder.withIndent('  ').convert(data));
}
