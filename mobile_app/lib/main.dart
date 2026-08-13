import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

import 'offline_board_page.dart';
import 'simple_home_page.dart';
import 'app_preferences.dart';

void main() => runApp(const ChessPlatformApp());

class ChessPlatformApp extends StatefulWidget {
  const ChessPlatformApp({super.key});

  @override
  State<ChessPlatformApp> createState() => _ChessPlatformAppState();
}

class _ChessPlatformAppState extends State<ChessPlatformApp> {
  final _preferences = AppPreferences();
  ThemeMode _themeMode = ThemeMode.system;
  bool _soundsEnabled = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final theme = await _preferences.loadTheme();
    final sounds = await _preferences.loadSounds();
    if (mounted) {
      setState(() {
        _themeMode = theme;
        _soundsEnabled = sounds;
      });
    }
  }

  Future<void> _setTheme(ThemeMode mode) async {
    await _preferences.saveTheme(mode);
    setState(() => _themeMode = mode);
  }

  Future<void> _setSounds(bool enabled) async {
    await _preferences.saveSounds(enabled);
    setState(() => _soundsEnabled = enabled);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Chess Platform',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xff24563b),
            brightness: Brightness.light,
            surface: const Color(0xfffbfcf7),
          ),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xfff4f7ef),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xfff4f7ef),
            foregroundColor: Color(0xff17251c),
            elevation: 0,
          ),
          cardTheme: const CardThemeData(
            color: Colors.white,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(20)),
              side: BorderSide(color: Color(0xffdce5d8)),
            ),
          ),
          inputDecorationTheme: const InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.all(Radius.circular(14)),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        darkTheme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
                seedColor: const Color(0xff62a85f),
                brightness: Brightness.dark),
            useMaterial3: true,
            scaffoldBackgroundColor: const Color(0xff111713),
            cardTheme: const CardThemeData(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.all(Radius.circular(20))))),
        themeMode: _themeMode,
        home: SimpleHomePage(
            themeMode: _themeMode,
            soundsEnabled: _soundsEnabled,
            onThemeChanged: _setTheme,
            onSoundsChanged: _setSounds),
      );
}

class OfflineLobbyPage extends StatefulWidget {
  const OfflineLobbyPage({super.key});

  @override
  State<OfflineLobbyPage> createState() => _OfflineLobbyPageState();
}

class _OfflineLobbyPageState extends State<OfflineLobbyPage> {
  final _server = TextEditingController(
    text: const String.fromEnvironment(
      'CHESS_SERVER_URL',
      defaultValue: 'http://10.0.2.2:8000',
    ),
  );
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _roomName = TextEditingController();
  final _hostName = TextEditingController();
  final _roomCode = TextEditingController();
  final _joinName = TextEditingController();
  String? _accessToken;
  String? _sessionCookie;
  List<Map<String, dynamic>> _rooms = [];
  Map<String, dynamic>? _joinedParticipant;
  bool _joinAsSpectator = false;
  bool _loading = false;
  String? _message;

  @override
  void dispose() {
    _server.dispose();
    _email.dispose();
    _password.dispose();
    _roomName.dispose();
    _hostName.dispose();
    _roomCode.dispose();
    _joinName.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function(OfflineApi api) action) async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final api = OfflineApi(_server.text, _accessToken, _sessionCookie);
      await action(api);
      _sessionCookie = api.sessionCookie ?? _sessionCookie;
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
        if (mounted) {
          setState(() => _message = 'Signed in to your local server.');
        }
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

  Future<void> _joinRoom() => _run((api) async {
        final participant = await api.joinRoom(
          code: _roomCode.text,
          displayName: _joinName.text,
          asSpectator: _joinAsSpectator,
        );
        if (mounted) {
          setState(() {
            _joinedParticipant = participant;
            _message =
                'Joined room ${_roomCode.text.trim().toUpperCase()} as ${participant['role'] ?? 'player'}.';
          });
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => RoomLobbyPage(
                serverUrl: _server.text,
                roomCode: _roomCode.text.trim().toUpperCase(),
                sessionCookie: _sessionCookie,
              ),
            ),
          );
        }
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
                decoration:
                    const InputDecoration(labelText: 'Your display name'),
              ),
              FilledButton.tonal(
                onPressed: _loading ? null : _createRoom,
                child: const Text('Create public room'),
              ),
              const Divider(height: 32),
              const Text(
                'Join a room by code',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              TextField(
                controller: _roomCode,
                textCapitalization: TextCapitalization.characters,
                maxLength: 12,
                decoration: const InputDecoration(labelText: 'Room code'),
              ),
              TextField(
                controller: _joinName,
                decoration:
                    const InputDecoration(labelText: 'Your display name'),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Join as spectator'),
                value: _joinAsSpectator,
                onChanged: _loading
                    ? null
                    : (value) => setState(() => _joinAsSpectator = value),
              ),
              FilledButton(
                onPressed: _loading ? null : _joinRoom,
                child: const Text('Join room'),
              ),
              if (_joinedParticipant != null)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.check_circle_outline),
                    title: Text(
                        _joinedParticipant!['display_name'] as String? ??
                            'Joined'),
                    subtitle: Text(
                        'Role: ${_joinedParticipant!['role'] ?? 'player'}'),
                  ),
                ),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _loading
                    ? null
                    : () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => const OfflineBoardPage(),
                          ),
                        ),
                icon: const Icon(Icons.sports_esports),
                label: const Text('Play offline on this device'),
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
                    trailing: TextButton(
                      onPressed: () => setState(
                        () => _roomCode.text = room['code'] as String? ?? '',
                      ),
                      child: Text(room['code'] as String? ?? ''),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
}

class RoomLobbyPage extends StatefulWidget {
  const RoomLobbyPage(
      {super.key,
      required this.serverUrl,
      required this.roomCode,
      this.sessionCookie});

  final String serverUrl;
  final String roomCode;
  final String? sessionCookie;

  @override
  State<RoomLobbyPage> createState() => _RoomLobbyPageState();
}

class _RoomLobbyPageState extends State<RoomLobbyPage> {
  WebSocket? _socket;
  Map<String, dynamic>? _room;
  String? _error;
  bool _ready = false;

  Future<void> _startGame() async {
    try {
      final api = OfflineApi(widget.serverUrl, null, widget.sessionCookie);
      final game = await api.startRoomGame(widget.roomCode);
      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => GameStatePage(game: game)),
        );
      }
    } on HttpException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on SocketException {
      if (mounted) {
        setState(() => _error = 'Cannot reach the local game server.');
      }
    }
  }

  @override
  void initState() {
    super.initState();
    _connect();
  }

  Future<void> _connect() async {
    final base = Uri.parse(widget.serverUrl);
    final uri = base.replace(
        scheme: base.scheme == 'https' ? 'wss' : 'ws',
        path: '/ws/rooms/${widget.roomCode}/');
    try {
      final socket = await WebSocket.connect(uri.toString(),
          headers: widget.sessionCookie == null
              ? null
              : {HttpHeaders.cookieHeader: widget.sessionCookie!});
      _socket = socket;
      socket.listen((message) {
        final data = jsonDecode(message as String) as Map<String, dynamic>;
        if (data['room'] is Map && mounted) {
          setState(
              () => _room = Map<String, dynamic>.from(data['room'] as Map));
        }
        if (data['type'] == 'error' && mounted) {
          setState(() => _error = data['message'] as String?);
        }
      }, onError: (_) {
        if (mounted) setState(() => _error = 'Lost connection to the room.');
      });
    } on SocketException {
      if (mounted) {
        setState(() => _error = 'Cannot connect to the local room server.');
      }
    }
  }

  @override
  void dispose() {
    _socket?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final participants =
        (_room?['participants'] as List? ?? const []).cast<Map>();
    return Scaffold(
      appBar: AppBar(title: Text('Room ${widget.roomCode}')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(_room?['name'] as String? ?? 'Connecting...',
            style: Theme.of(context).textTheme.headlineSmall),
        Text(
            '${_room?['time_control'] ?? '-'} | ${_room?['status'] ?? 'waiting'}'),
        if (_error != null)
          Padding(
              padding: const EdgeInsets.only(top: 12), child: Text(_error!)),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Ready to play'),
          value: _ready,
          onChanged: _socket == null
              ? null
              : (ready) {
                  _socket!
                      .add(jsonEncode({'type': 'room.ready', 'ready': ready}));
                  setState(() => _ready = ready);
                },
        ),
        FilledButton.icon(
          onPressed: _socket == null ? null : _startGame,
          icon: const Icon(Icons.play_arrow),
          label: const Text('Start game'),
        ),
        const Divider(),
        const Text('Participants',
            style: TextStyle(fontWeight: FontWeight.bold)),
        ...participants.map((item) => ListTile(
            title: Text(item['display_name'] as String? ?? 'Guest'),
            trailing: Text(item['role'] as String? ?? ''))),
      ]),
    );
  }
}

class GameStatePage extends StatelessWidget {
  const GameStatePage({super.key, required this.game});

  final Map<String, dynamic> game;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Game started')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                  '${game['white_display_name'] ?? 'White'} vs ${game['black_display_name'] ?? 'Black'}',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 12),
              Text('Status: ${game['status'] ?? 'in progress'}'),
              Text('Turn: ${game['turn'] ?? 'white'}'),
              const SizedBox(height: 16),
              const Text(
                  'The interactive chessboard is the next mobile update.'),
            ],
          ),
        ),
      );
}

class OfflineApi {
  OfflineApi(String baseUrl, this.token, this.sessionCookie)
      : _baseUri = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');

  final Uri _baseUri;
  final String? token;
  String? sessionCookie;

  Future<String> login(String email, String password) async {
    final body = await _request('POST', 'api/auth/token/', {
      'email': email,
      'password': password,
    });
    final access = body['access'] as String?;
    if (access == null) {
      throw const HttpException(
        'The local server did not return an access token.',
      );
    }
    return access;
  }

  Future<List<Map<String, dynamic>>> publicRooms() async {
    final body = await _request('GET', 'api/rooms/');
    final data = body['results'] ?? body;
    if (data is! List) {
      throw const HttpException(
        'Unexpected room response from the local server.',
      );
    }
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

  Future<Map<String, dynamic>> joinRoom({
    required String code,
    required String displayName,
    required bool asSpectator,
  }) async {
    final cleanCode = code.trim().toUpperCase();
    if (cleanCode.isEmpty) throw const HttpException('Enter a room code.');
    final body = await _request('POST', 'api/rooms/$cleanCode/join/', {
      'display_name': displayName.trim(),
      'as_spectator': asSpectator,
    });
    if (body is! Map) {
      throw const HttpException(
          'Unexpected join response from the local server.');
    }
    return Map<String, dynamic>.from(body);
  }

  Future<Map<String, dynamic>> startRoomGame(String code) async {
    final body =
        await _request('POST', 'api/rooms/${code.trim().toUpperCase()}/start/');
    if (body is! Map) {
      throw const HttpException(
          'Unexpected game response from the local server.');
    }
    return Map<String, dynamic>.from(body);
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
      if (sessionCookie != null) {
        request.headers.set(HttpHeaders.cookieHeader, sessionCookie!);
      }
      if (token != null) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      if (payload != null) request.write(jsonEncode(payload));
      final response = await request.close();
      final session = response.cookies
          .where((cookie) => cookie.name == 'sessionid')
          .toList();
      if (session.isNotEmpty) {
        sessionCookie = 'sessionid=${session.first.value}';
      }
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
