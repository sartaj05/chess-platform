import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class MobileSession {
  MobileSession({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessKey = 'chess_access_token';
  static const _refreshKey = 'chess_refresh_token';
  static const _serverKey = 'chess_server_url';

  final FlutterSecureStorage _storage;
  String? accessToken;
  String? refreshToken;
  String? serverUrl;

  bool get isSignedIn => accessToken != null && refreshToken != null;

  Future<void> restore() async {
    accessToken = await _storage.read(key: _accessKey);
    refreshToken = await _storage.read(key: _refreshKey);
    serverUrl = await _storage.read(key: _serverKey);
  }

  Future<void> saveTokens({
    required String access,
    required String refresh,
    required String server,
  }) async {
    accessToken = access;
    refreshToken = refresh;
    serverUrl = server;
    await Future.wait([
      _storage.write(key: _accessKey, value: access),
      _storage.write(key: _refreshKey, value: refresh),
      _storage.write(key: _serverKey, value: server),
    ]);
  }

  Future<void> updateAccess(String access) async {
    accessToken = access;
    await _storage.write(key: _accessKey, value: access);
  }

  Future<void> clear() async {
    accessToken = null;
    refreshToken = null;
    await Future.wait([
      _storage.delete(key: _accessKey),
      _storage.delete(key: _refreshKey),
    ]);
  }
}
