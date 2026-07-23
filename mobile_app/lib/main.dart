import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

void main() => runApp(const ChessPlatformApp());

class ChessPlatformApp extends StatelessWidget {
  const ChessPlatformApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Chess Platform',
    theme: ThemeData(
      colorSchemeSeed: const Color(0xff1b5e20),
      useMaterial3: true,
    ),
    home: const OfflineLobbyPage(),
  );
}

class OfflineLobbyPage extends StatefulWidget {
  const OfflineLobbyPage({super.key});

  @override
  State<OfflineLobbyPage> createState() => _OfflineLobbyPageState();
}

class _OfflineLobbyPageState extends State<OfflineLobbyPage> {
  final _server = TextEditingController(text: 'http://192.168.1.10:8000');
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _roomName = TextEditingController();
  final _hostName = TextEditingController();
  String? _accessToken;
  List<Map<String, dynamic>> _rooms = [];
  bool _loading = false;
  String? _message;

  @override
  void dispose() {
    _server.dispose();
    _email.dispose();
    _password.dispose();
    _roomName.dispose();
    _hostName.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function(OfflineApi api) action) async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await action(OfflineApi(_server.text, _accessToken));
    } on SocketException {
      _message =
          'Cannot reach the server. Check the LAN IP address and that Django is running.';
    } on HttpException catch (error) {
      _message = error.message;
    } catch (_) {
      _message =
          'Something went wrong. Check the server address and try again.';
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _login() => _run((api) async {
    _accessToken = await api.login(_email.text, _password.text);
    if (mounted) setState(() => _message = 'Signed in to your local server.');
  });

  Future<void> _loadRooms() => _run((api) async {
    final rooms = await api.publicRooms();
    if (mounted) setState(() => _rooms = rooms);
  });

  Future<void> _createRoom() => _run((api) async {
    await api.createRoom(name: _roomName.text, hostName: _hostName.text);
    _roomName.clear();
    await _loadRooms();
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Chess Platform — Offline LAN')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Local server',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          TextField(
            controller: _server,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              hintText: 'http://192.168.x.x:8000',
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Sign in (optional for public rooms)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          TextField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: 'Email'),
          ),
          TextField(
            controller: _password,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Password'),
          ),
          FilledButton(
            onPressed: _loading ? null : _login,
            child: const Text('Sign in locally'),
          ),
          const Divider(height: 32),
          TextField(
            controller: _roomName,
            decoration: const InputDecoration(labelText: 'New room name'),
          ),
          TextField(
            controller: _hostName,
            decoration: const InputDecoration(labelText: 'Your display name'),
          ),
          FilledButton.tonal(
            onPressed: _loading ? null : _createRoom,
            child: const Text('Create public room'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _loading ? null : _loadRooms,
            child: const Text('Refresh public rooms'),
          ),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(12),
                child: CircularProgressIndicator(),
              ),
            ),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_message!),
            ),
          const SizedBox(height: 8),
          ..._rooms.map(
            (room) => Card(
              child: ListTile(
                title: Text(room['name'] as String? ?? 'Untitled room'),
                subtitle: Text(
                  '${room['time_control'] ?? '—'} • Host: ${room['host_display_name'] ?? 'Guest'}',
                ),
                trailing: Text(room['code'] as String? ?? ''),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class OfflineApi {
  OfflineApi(String baseUrl, this.token)
    : _baseUri = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');

  final Uri _baseUri;
  final String? token;

  Future<String> login(String email, String password) async {
    final body = await _request('POST', 'api/auth/token/', {
      'email': email,
      'password': password,
    });
    final access = body['access'] as String?;
    if (access == null)
      throw const HttpException(
        'The local server did not return an access token.',
      );
    return access;
  }

  Future<List<Map<String, dynamic>>> publicRooms() async {
    final body = await _request('GET', 'api/rooms/');
    final data = body['results'] ?? body;
    if (data is! List)
      throw const HttpException(
        'Unexpected room response from the local server.',
      );
    return data
        .cast<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<void> createRoom({
    required String name,
    required String hostName,
  }) async {
    await _request('POST', 'api/rooms/', {
      'name': name.trim(),
      'host_display_name': hostName.trim(),
      'visibility': 'public',
      'mode': 'lan',
      'clock_initial_minutes': 5,
      'increment_seconds': 0,
      'allow_guests': true,
      'spectator_enabled': true,
    });
  }

  Future<dynamic> _request(
    String method,
    String path, [
    Map<String, dynamic>? payload,
  ]) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, _baseUri.resolve(path));
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (token != null)
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      if (payload != null) request.write(jsonEncode(payload));
      final response = await request.close();
      final text = await utf8.decodeStream(response);
      final decoded = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw HttpException(
          decoded is Map
              ? decoded.toString()
              : 'Server returned ${response.statusCode}.',
        );
      }
      return decoded;
    } finally {
      client.close(force: true);
    }
  }
}
