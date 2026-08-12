import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'offline_board_page.dart';

enum PlayerSide { white, black, random }

class SimpleHomePage extends StatefulWidget {
  const SimpleHomePage({super.key});

  @override
  State<SimpleHomePage> createState() => _SimpleHomePageState();
}

class _SimpleHomePageState extends State<SimpleHomePage> {
  final _server = TextEditingController(
    text: const String.fromEnvironment(
      'CHESS_SERVER_URL',
      defaultValue: 'http://10.0.2.2:8000',
    ),
  );
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _code = TextEditingController();
  String? _token;
  String? _cookie;
  String? _message;
  bool _busy = false;
  int _botLevel = 1;
  int _selectedBotLevel = 1;
  String? _displayName;
  PlayerSide _side = PlayerSide.random;

  bool get _signedIn => _token != null;

  @override
  void dispose() {
    _server.dispose();
    _email.dispose();
    _password.dispose();
    _name.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _perform(Future<void> Function(_MobileApi api) action) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final api = _MobileApi(_server.text, _token, _cookie);
      await action(api);
      _cookie = api.cookie ?? _cookie;
    } on SocketException {
      _message = 'Server unavailable. Check the server address and Wi-Fi.';
    } on HttpException catch (error) {
      _message = error.message;
    } catch (error) {
      _message = 'Could not complete that action: $error';
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _login() => _perform((api) async {
        if (_email.text.trim().isEmpty || _password.text.isEmpty) {
          throw const HttpException('Enter your email and password.');
        }
        _token = await api.login(_email.text.trim(), _password.text);
        final profile =
            await _MobileApi(_server.text, _token, _cookie).profile();
        if (mounted) {
          setState(() {
            _botLevel = profile['bot_level'] as int? ?? 1;
            _selectedBotLevel = _botLevel;
            _displayName = profile['display_name'] as String?;
            _name.text = _displayName ?? _name.text;
            _message = 'Welcome back, ${_displayName ?? 'Player'}.';
          });
        }
      });

  Future<void> _openRegistration() async {
    final registered = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (_) => RegistrationPage(serverUrl: _server.text),
    ));
    if (registered == true && mounted) {
      setState(
          () => _message = 'Account verified. Log in with your new account.');
    }
  }

  void _logout() {
    setState(() {
      _token = null;
      _cookie = null;
      _password.clear();
      _botLevel = 1;
      _selectedBotLevel = 1;
      _displayName = null;
      _message = 'Logged out.';
    });
  }

  chessSide() => switch (_side) {
        PlayerSide.white => BoardSide.white,
        PlayerSide.black => BoardSide.black,
        PlayerSide.random => BoardSide.random,
      };

  Future<int> _recordBotVictory(int level) async {
    if (!_signedIn) return level;
    final api = _MobileApi(_server.text, _token, _cookie);
    final unlocked = await api.recordBotVictory(level);
    if (mounted) setState(() => _botLevel = unlocked);
    return unlocked;
  }

  Future<void> _createOnlineGame() => _perform((api) async {
        final room = await api.createRoom(
          displayName: _name.text.trim(),
          side: _side.name,
        );
        final code = room['code'] as String;
        if (!mounted) return;
        await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ShareCodePage(
            serverUrl: _server.text,
            roomCode: code,
            displayName: _name.text.trim(),
            token: _token,
            cookie: api.cookie,
          ),
        ));
      });

  Future<void> _joinOnlineGame() => _perform((api) async {
        final code = _code.text.trim().toUpperCase();
        if (code.isEmpty) throw const HttpException('Enter the shared code.');
        await api.joinRoom(code, _name.text.trim());
        if (!mounted) return;
        await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ShareCodePage(
            serverUrl: _server.text,
            roomCode: code,
            displayName: _name.text.trim(),
            token: _token,
            cookie: api.cookie,
          ),
        ));
      });

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Chess Platform'),
          actions: [
            if (_signedIn)
              TextButton.icon(
                onPressed: _logout,
                icon: const Icon(Icons.logout),
                label: const Text('Logout'),
              ),
          ],
        ),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
            children: [
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: const Color(0xff173b2a),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('YOUR NEXT GAME',
                          style: TextStyle(
                              color: Color(0xffa9c7a9),
                              fontSize: 11,
                              letterSpacing: 1.8,
                              fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Text(
                          _signedIn
                              ? 'Ready, ${_displayName ?? 'Player'}?'
                              : 'Play chess your way.',
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 27,
                              fontWeight: FontWeight.bold)),
                      const SizedBox(height: 7),
                      const Text(
                          'Train with the bot, share a board, or challenge a friend online.',
                          style:
                              TextStyle(color: Color(0xffd4e2d5), height: 1.4)),
                    ]),
              ),
              const SizedBox(height: 22),
              if (!_signedIn) ...[
                Text('Login', style: Theme.of(context).textTheme.headlineSmall),
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
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: _busy ? null : _login,
                  child: const Text('Login'),
                ),
                OutlinedButton(
                  onPressed: _busy ? null : _openRegistration,
                  child: const Text('Create Account'),
                ),
                const Center(child: Text('or continue as guest')),
                const Divider(height: 32),
              ],
              TextField(
                controller: _name,
                decoration: const InputDecoration(
                  labelText: 'Your name',
                  prefixIcon: Icon(Icons.person_outline),
                ),
              ),
              const SizedBox(height: 20),
              Text('Choose your side',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              SegmentedButton<PlayerSide>(
                segments: const [
                  ButtonSegment(value: PlayerSide.white, label: Text('White')),
                  ButtonSegment(
                      value: PlayerSide.random, label: Text('Random')),
                  ButtonSegment(value: PlayerSide.black, label: Text('Black')),
                ],
                selected: {_side},
                onSelectionChanged: (value) =>
                    setState(() => _side = value.first),
              ),
              const SizedBox(height: 24),
              Text('Play', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          const CircleAvatar(
                              child: Icon(Icons.smart_toy_outlined)),
                          const SizedBox(width: 12),
                          Expanded(
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                const Text('Bot Challenge',
                                    style: TextStyle(
                                        fontSize: 17,
                                        fontWeight: FontWeight.bold)),
                                Text(_signedIn
                                    ? 'Level $_botLevel unlocked'
                                    : 'Guest progress · Level 1'),
                              ])),
                        ]),
                        const SizedBox(height: 12),
                        LinearProgressIndicator(
                            value: _botLevel / 10,
                            minHeight: 7,
                            borderRadius: BorderRadius.circular(10)),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<int>(
                          initialValue: _selectedBotLevel,
                          decoration:
                              const InputDecoration(labelText: 'Bot level'),
                          items: [
                            for (var level = 1; level <= _botLevel; level++)
                              DropdownMenuItem(
                                  value: level, child: Text('Level $level'))
                          ],
                          onChanged: (value) =>
                              setState(() => _selectedBotLevel = value ?? 1),
                        ),
                        const SizedBox(height: 10),
                        FilledButton.icon(
                          onPressed: () =>
                              Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => OfflineBoardPage(
                                mode: OfflinePlayMode.bot,
                                preferredSide: chessSide(),
                                botLevel: _selectedBotLevel,
                                onBotVictory: _recordBotVictory),
                          )),
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Play Bot'),
                        ),
                      ]),
                ),
              ),
              _PlayCard(
                icon: Icons.people_outline,
                title: 'Play with Friend',
                subtitle: 'Two players on this device',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => OfflineBoardPage(
                    preferredSide: chessSide(),
                  ),
                )),
              ),
              _PlayCard(
                icon: Icons.phone_android,
                title: 'Play on Another Mobile',
                subtitle: 'Create a game and share its code',
                onTap: _busy ? null : _createOnlineGame,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _code,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(
                  labelText: 'Friend code',
                  prefixIcon: Icon(Icons.key),
                ),
              ),
              FilledButton.tonal(
                onPressed: _busy ? null : _joinOnlineGame,
                child: const Text('Join with Code'),
              ),
              ExpansionTile(
                title: const Text('Server settings'),
                children: [
                  TextField(
                    controller: _server,
                    keyboardType: TextInputType.url,
                    decoration: const InputDecoration(labelText: 'Server URL'),
                  ),
                ],
              ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.all(12),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (_message != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(_message!, textAlign: TextAlign.center),
                ),
            ],
          ),
        ),
      );
}

class _PlayCard extends StatelessWidget {
  const _PlayCard(
      {required this.icon,
      required this.title,
      required this.subtitle,
      this.onTap});
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: Icon(icon, size: 32),
          title: Text(title),
          subtitle: Text(subtitle),
          trailing: const Icon(Icons.chevron_right),
          onTap: onTap,
        ),
      );
}

class RegistrationPage extends StatefulWidget {
  const RegistrationPage({super.key, required this.serverUrl});
  final String serverUrl;

  @override
  State<RegistrationPage> createState() => _RegistrationPageState();
}

class _RegistrationPageState extends State<RegistrationPage> {
  final _email = TextEditingController();
  final _name = TextEditingController();
  final _password = TextEditingController();
  final _confirmPassword = TextEditingController();
  final _code = TextEditingController();
  bool _codeSent = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _name.dispose();
    _password.dispose();
    _confirmPassword.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (_password.text != _confirmPassword.text) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = _MobileApi(widget.serverUrl, null, null);
      await api.register(_email.text.trim(), _name.text.trim(), _password.text);
      if (mounted) setState(() => _codeSent = true);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = _MobileApi(widget.serverUrl, null, null);
      await api.verifyEmail(_email.text.trim(), _code.text.trim());
      if (mounted) Navigator.of(context).pop(true);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Create Account')),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          TextField(
            controller: _email,
            enabled: !_codeSent,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: 'Email'),
          ),
          if (!_codeSent) ...[
            TextField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Display name'),
            ),
            TextField(
              controller: _password,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
            ),
            TextField(
              controller: _confirmPassword,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Confirm password'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy ? null : _register,
              child: const Text('Register'),
            ),
          ] else ...[
            const SizedBox(height: 16),
            const Text(
                'Check your email and enter the 6-digit verification code.'),
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(labelText: 'Verification code'),
            ),
            FilledButton(
              onPressed: _busy ? null : _verify,
              child: const Text('Verify Account'),
            ),
          ],
          if (_busy) const Center(child: CircularProgressIndicator()),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, textAlign: TextAlign.center),
            ),
        ]),
      );
}

class ShareCodePage extends StatefulWidget {
  const ShareCodePage(
      {super.key,
      required this.serverUrl,
      required this.roomCode,
      required this.displayName,
      this.token,
      this.cookie});
  final String serverUrl;
  final String roomCode;
  final String displayName;
  final String? token;
  final String? cookie;

  @override
  State<ShareCodePage> createState() => _ShareCodePageState();
}

class _ShareCodePageState extends State<ShareCodePage> {
  Map<String, dynamic>? _room;
  String? _error;
  bool _busy = false;

  Future<void> _refresh() async {
    try {
      final api = _MobileApi(widget.serverUrl, widget.token, widget.cookie);
      final room = await api.room(widget.roomCode);
      if (mounted) setState(() => _room = room);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    }
  }

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final api = _MobileApi(widget.serverUrl, widget.token, widget.cookie);
      final game = await api.start(widget.roomCode);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
              'Game started: ${game['white_display_name']} vs ${game['black_display_name']}'),
        ));
      }
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final players = (_room?['participants'] as List? ?? const []);
    return Scaffold(
      appBar: AppBar(title: const Text('Play with Friend')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Text('Share this code', textAlign: TextAlign.center),
        SelectableText(widget.roomCode,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.displaySmall),
        FilledButton.icon(
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: widget.roomCode));
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Code copied')),
              );
            }
          },
          icon: const Icon(Icons.copy),
          label: const Text('Copy Code'),
        ),
        const SizedBox(height: 20),
        Text('Players (${players.length}/2)',
            style: Theme.of(context).textTheme.titleLarge),
        ...players.map((item) => ListTile(
              leading: const Icon(Icons.person),
              title:
                  Text((item as Map)['display_name']?.toString() ?? 'Player'),
              subtitle: Text(item['role']?.toString() ?? ''),
            )),
        OutlinedButton.icon(
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
            label: const Text('Refresh Players')),
        FilledButton(
            onPressed: _busy || players.length < 2 ? null : _start,
            child: const Text('Start Game')),
        if (_error != null) Text(_error!, textAlign: TextAlign.center),
      ]),
    );
  }
}

class _MobileApi {
  _MobileApi(String baseUrl, this.token, this.cookie)
      : base = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');
  final Uri base;
  final String? token;
  String? cookie;

  Future<String> login(String email, String password) async {
    final data = await _request(
        'POST', 'api/auth/token/', {'email': email, 'password': password});
    return data['access'] as String;
  }

  Future<Map<String, dynamic>> profile() async => Map<String, dynamic>.from(
      await _request('GET', 'api/accounts/me/') as Map);

  Future<int> recordBotVictory(int level) async {
    final data =
        await _request('POST', 'api/accounts/bot-victory/', {'level': level});
    return data['bot_level'] as int? ?? level;
  }

  Future<void> register(String email, String displayName, String password) =>
      _request('POST', 'api/accounts/register/', {
        'email': email,
        'display_name': displayName,
        'password': password,
      });

  Future<void> verifyEmail(String email, String code) =>
      _request('POST', 'api/accounts/verify-email/', {
        'email': email,
        'code': code,
      });

  Future<Map<String, dynamic>> createRoom(
      {required String displayName, required String side}) async {
    final data = await _request('POST', 'api/rooms/', {
      'name': '${displayName.isEmpty ? 'Player' : displayName}\'s game',
      'host_display_name': displayName,
      'mode': 'online',
      'visibility': 'private',
      'color_preference': side,
      'clock_initial_minutes': 10,
      'allow_guests': true,
      'spectator_enabled': false,
    });
    return Map<String, dynamic>.from(data as Map);
  }

  Future<void> joinRoom(String code, String name) =>
      _request('POST', 'api/rooms/$code/join/', {'display_name': name});
  Future<Map<String, dynamic>> room(String code) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/rooms/$code/') as Map);
  Future<Map<String, dynamic>> start(String code) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/rooms/$code/start/') as Map);

  Future<dynamic> _request(String method, String path,
      [Map<String, dynamic>? body]) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, base.resolve(path));
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (token != null) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      if (cookie != null) {
        request.headers.set(HttpHeaders.cookieHeader, cookie!);
      }
      if (body != null) {
        final payload = utf8.encode(jsonEncode(body));
        request.contentLength = payload.length;
        request.add(payload);
      }
      final response = await request.close();
      if (response.cookies.isNotEmpty) {
        cookie = response.cookies
            .map((item) => '${item.name}=${item.value}')
            .join('; ');
      }
      final text = await utf8.decodeStream(response);
      final data = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw HttpException(_errorMessage(data, response.statusCode));
      }
      return data;
    } finally {
      client.close(force: true);
    }
  }

  String _errorMessage(dynamic data, int statusCode) {
    if (data is Map) {
      final messages = <String>[];
      for (final entry in data.entries) {
        final value = entry.value;
        if (value is List) {
          messages.addAll(value.map((item) => item.toString()));
        } else if (value != null) {
          messages.add(value.toString());
        }
      }
      if (messages.isNotEmpty) return messages.join(' ');
    }
    return 'Server returned status $statusCode.';
  }
}
