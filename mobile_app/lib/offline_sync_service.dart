import 'dart:convert';
import 'dart:io';

import 'offline_game_repository.dart';

/// Sends locally completed games to the Django LAN server when it is reachable.
class OfflineSyncService {
  OfflineSyncService(this._repository);

  final OfflineGameRepository _repository;

  Future<OfflineSyncResult> sync(
      {required String serverUrl,
      String? accessToken,
      String? sessionCookie}) async {
    final pending = await _repository.pendingSync();
    var synced = 0;
    for (final game in pending) {
      final client = HttpClient();
      try {
        final uri = Uri.parse(serverUrl.endsWith('/')
            ? '${serverUrl}api/games/sync_offline/'
            : '$serverUrl/api/games/sync_offline/');
        final request = await client.postUrl(uri);
        request.headers.contentType = ContentType.json;
        request.headers.set(HttpHeaders.acceptHeader, 'application/json');
        if (accessToken != null) {
          request.headers
              .set(HttpHeaders.authorizationHeader, 'Bearer $accessToken');
        }
        if (sessionCookie != null) {
          request.headers.set(HttpHeaders.cookieHeader, sessionCookie);
        }
        request.write(jsonEncode({
          'sync_id': game.id,
          'initial_fen': game.initialFen,
          'current_fen': game.currentFen,
          'pgn': game.pgn,
          'mode': game.mode,
          'metadata': game.metadata,
        }));
        final response = await request.close();
        final responseText = await utf8.decodeStream(response);
        if (response.statusCode >= 200 && response.statusCode < 300) {
          await _repository.markSynced(game.id);
          synced++;
        } else if (response.statusCode == HttpStatus.conflict) {
          final details = responseText.isEmpty
              ? <String, dynamic>{'detail': 'Offline sync conflict.'}
              : Map<String, dynamic>.from(jsonDecode(responseText) as Map);
          await _repository.markConflict(game.id, details);
          return OfflineSyncResult(
              synced: synced,
              pending: pending.length - synced,
              conflicts: [OfflineSyncConflict(game: game, details: details)],
              message:
                  'A game changed on both device and server. Choose which copy to keep.');
        } else {
          return OfflineSyncResult(
              synced: synced,
              pending: pending.length - synced,
              message: 'Server rejected a game sync (${response.statusCode}).');
        }
      } on SocketException {
        return OfflineSyncResult(
            synced: synced,
            pending: pending.length - synced,
            message:
                'Local server is unavailable. Games remain safely on this device.');
      } finally {
        client.close(force: true);
      }
    }
    return OfflineSyncResult(
        synced: synced, pending: 0, message: 'Offline games synced.');
  }

  Future<void> resolve(OfflineSyncConflict conflict,
      OfflineConflictResolution resolution) async {
    if (resolution == OfflineConflictResolution.keepServer) {
      await _repository.keepServerVersion(conflict.game.id);
    } else {
      await _repository.uploadAsCopy(conflict.game);
    }
  }
}

enum OfflineConflictResolution { keepServer, uploadDeviceAsCopy }

class OfflineSyncConflict {
  const OfflineSyncConflict({required this.game, required this.details});
  final OfflineGame game;
  final Map<String, dynamic> details;
}

class OfflineSyncResult {
  const OfflineSyncResult(
      {required this.synced,
      required this.pending,
      required this.message,
      this.conflicts = const []});

  final int synced;
  final int pending;
  final String message;
  final List<OfflineSyncConflict> conflicts;
}
