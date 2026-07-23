import 'dart:convert';

import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

/// Stores locally played games until the Django server can accept a sync.
class OfflineGameRepository {
  Database? _database;

  Future<Database> get _db async {
    if (_database != null) return _database!;
    final directory = await getApplicationDocumentsDirectory();
    _database = await openDatabase(
      join(directory.path, 'chess_platform_offline.db'),
      version: 1,
      onCreate: (db, _) => db.execute('''
        CREATE TABLE offline_games (
          id TEXT PRIMARY KEY,
          initial_fen TEXT NOT NULL,
          current_fen TEXT NOT NULL,
          pgn TEXT NOT NULL,
          mode TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          synced_at TEXT,
          metadata TEXT NOT NULL
        )
      '''),
    );
    return _database!;
  }

  Future<void> save(OfflineGame game) async {
    final db = await _db;
    await db.insert('offline_games', game.toRow(),
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<OfflineGame>> pendingSync() async {
    final db = await _db;
    final rows = await db.query('offline_games',
        where: 'synced_at IS NULL', orderBy: 'updated_at ASC');
    return rows.map(OfflineGame.fromRow).toList();
  }

  Future<void> markSynced(String id) async {
    final db = await _db;
    await db.update('offline_games',
        {'synced_at': DateTime.now().toUtc().toIso8601String()},
        where: 'id = ?', whereArgs: [id]);
  }
}

class OfflineGame {
  OfflineGame(
      {required this.id,
      required this.initialFen,
      required this.currentFen,
      required this.pgn,
      required this.mode,
      required this.createdAt,
      required this.updatedAt,
      this.metadata = const {}});

  final String id;
  final String initialFen;
  final String currentFen;
  final String pgn;
  final String mode;
  final DateTime createdAt;
  final DateTime updatedAt;
  final Map<String, dynamic> metadata;

  Map<String, Object?> toRow() => {
        'id': id,
        'initial_fen': initialFen,
        'current_fen': currentFen,
        'pgn': pgn,
        'mode': mode,
        'created_at': createdAt.toUtc().toIso8601String(),
        'updated_at': updatedAt.toUtc().toIso8601String(),
        'metadata': jsonEncode(metadata)
      };

  factory OfflineGame.fromRow(Map<String, Object?> row) => OfflineGame(
        id: row['id']! as String,
        initialFen: row['initial_fen']! as String,
        currentFen: row['current_fen']! as String,
        pgn: row['pgn']! as String,
        mode: row['mode']! as String,
        createdAt: DateTime.parse(row['created_at']! as String),
        updatedAt: DateTime.parse(row['updated_at']! as String),
        metadata: Map<String, dynamic>.from(
            jsonDecode(row['metadata']! as String) as Map),
      );
}
