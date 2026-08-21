import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'l10n/app_localizations.dart';

import 'offline_board_page.dart';
import 'mobile_session.dart';
import 'online_game_page.dart';
import 'profile_history_pages.dart';
import 'notification_page.dart';
import 'matchmaking_page.dart';
import 'competitive_pages.dart';
import 'push_service.dart';
import 'social_pages.dart';
import 'tournament_page.dart';
import 'deep_link_service.dart';
import 'game_replay_page.dart';
import 'onboarding_page.dart';
import 'retention_page.dart';
import 'dart:async';

enum PlayerSide { white, black, random }

String _defaultServerUrl() {
  const configured = String.fromEnvironment('CHESS_SERVER_URL');
  if (configured.isNotEmpty) return configured;
  return Platform.isWindows ? 'http://127.0.0.1:8000' : 'http://10.0.2.2:8000';
}

class SimpleHomePage extends StatefulWidget {
  const SimpleHomePage(
      {super.key,
      required this.themeMode,
      required this.soundsEnabled,
      required this.boardTheme,
      required this.soundPack,
      required this.locale,
      required this.onThemeChanged,
      required this.onSoundsChanged,
      required this.onBoardThemeChanged,
      required this.onSoundPackChanged,
      required this.onLocaleChanged});
  final ThemeMode themeMode;
  final bool soundsEnabled;
  final String boardTheme;
  final String soundPack;
  final Locale? locale;
  final ValueChanged<ThemeMode> onThemeChanged;
  final ValueChanged<bool> onSoundsChanged;
  final ValueChanged<String> onBoardThemeChanged;
  final ValueChanged<String> onSoundPackChanged;
  final ValueChanged<Locale?> onLocaleChanged;

  @override
  State<SimpleHomePage> createState() => _SimpleHomePageState();
}

class _SimpleHomePageState extends State<SimpleHomePage> {
  StreamSubscription<MobileLink>? _deepLinkSubscription;
  Timer? _presenceTimer;
  final _server = TextEditingController(
    text: _defaultServerUrl(),
  );
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _code = TextEditingController();
  final _session = MobileSession();
  String? _token;
  String? _cookie;
  String? _message;
  bool _busy = false;
  int _botLevel = 1;
  int _selectedBotLevel = 1;
  String _botPersonality = 'balanced';
  String? _displayName;
  Map<String, dynamic>? _experience;
  PlayerSide _side = PlayerSide.random;

  bool get _signedIn => _token != null;

  @override
  void initState() {
    super.initState();
    _deepLinkSubscription = DeepLinkService.links.listen(_handleDeepLink);
    _restoreSession();
  }

  Future<void> _handleDeepLink(MobileLink link) async {
    if (!mounted) return;
    if (link.destination == MobileDestination.notifications) {
      if (_signedIn) await _openNotifications();
      return;
    }
    if (link.destination == MobileDestination.tournament) {
      if (_signedIn) await _openTournaments();
      return;
    }
    if (link.id == null) return;
    if (link.destination == MobileDestination.room) {
      _code.text = link.id!;
      await _joinOnlineGame();
      return;
    }
    if (!_signedIn) {
      setState(() => _message = 'Log in to open this secure chess link.');
      return;
    }
    await _perform((api) async {
      if (link.destination == MobileDestination.profile) {
        final profile = await api.publicProfile(link.id!);
        final comparison = await api.compareProfile(link.id!);
        if (mounted) {
          await Navigator.of(context).push(MaterialPageRoute(
              builder: (_) =>
                  PublicProfilePage(profile: profile, comparison: comparison)));
        }
      } else if (link.destination == MobileDestination.game) {
        final game = await api.game(link.id!);
        if (mounted) {
          await Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => GameReplayPage(
                  game: game,
                  startAnalysis: api.startGameAnalysis,
                  analysisStatus: api.analysisStatus,
                  retryAnalysis: api.retryAnalysis)));
        }
      }
    });
  }

  Future<void> _restoreSession() async {
    await _session.restore();
    if (_session.serverUrl?.isNotEmpty == true) {
      _server.text = _session.serverUrl!;
    }
    if (!_session.isSignedIn) return;
    _token = _session.accessToken;
    try {
      final api = _MobileApi(_server.text, _token, _cookie, session: _session);
      final profile = await api.profile();
      await api.presenceHeartbeat();
      _startPresenceHeartbeat();
      final experience = await api.experience();
      if (!mounted) return;
      setState(() {
        _token = _session.accessToken;
        _botLevel = profile['bot_level'] as int? ?? 1;
        _selectedBotLevel = _botLevel;
        _displayName = profile['display_name'] as String?;
        _experience = experience;
        _name.text = _displayName ?? '';
      });
      await PushService.configure(api.registerPushDevice);
    } catch (_) {
      await _session.clear();
      if (mounted) setState(() => _token = null);
    }
  }

  @override
  void dispose() {
    _deepLinkSubscription?.cancel();
    _presenceTimer?.cancel();
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
      final api = _MobileApi(_server.text, _token, _cookie, session: _session);
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
        final tokens = await api.login(_email.text.trim(), _password.text);
        await _session.saveTokens(
          access: tokens['access']!,
          refresh: tokens['refresh']!,
          server: _server.text.trim(),
        );
        _token = _session.accessToken;
        await _authenticatedApi.presenceHeartbeat();
        _startPresenceHeartbeat();
        await PushService.configure(_authenticatedApi.registerPushDevice);
        final profile =
            await _MobileApi(_server.text, _token, _cookie, session: _session)
                .profile();
        final experience = await _authenticatedApi.experience();
        if (mounted) {
          setState(() {
            _botLevel = profile['bot_level'] as int? ?? 1;
            _selectedBotLevel = _botLevel;
            _displayName = profile['display_name'] as String?;
            _experience = experience;
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

  Future<void> _logout() async {
    _presenceTimer?.cancel();
    await _session.clear();
    if (!mounted) return;
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

  void _startPresenceHeartbeat() {
    _presenceTimer?.cancel();
    _presenceTimer = Timer.periodic(const Duration(seconds: 60), (_) async {
      if (_signedIn) {
        try {
          await _authenticatedApi.presenceHeartbeat();
        } catch (_) {}
      }
    });
  }

  chessSide() => switch (_side) {
        PlayerSide.white => BoardSide.white,
        PlayerSide.black => BoardSide.black,
        PlayerSide.random => BoardSide.random,
      };

  Future<int> _recordBotVictory(int level) async {
    if (!_signedIn) return level;
    final api = _MobileApi(_server.text, _token, _cookie, session: _session);
    final unlocked = await api.recordBotVictory(level);
    if (mounted) setState(() => _botLevel = unlocked);
    return unlocked;
  }

  Future<void> _createOnlineGame() async {
    var variant = 'standard';
    final fen = TextEditingController();
    final choice = await showDialog<bool>(
        context: context,
        builder: (context) => StatefulBuilder(
            builder: (context, setDialogState) => AlertDialog(
                  title: const Text('Create online game'),
                  content: Column(mainAxisSize: MainAxisSize.min, children: [
                    DropdownButtonFormField<String>(
                        initialValue: variant,
                        decoration: const InputDecoration(labelText: 'Variant'),
                        items: const [
                          DropdownMenuItem(
                              value: 'standard', child: Text('Standard chess')),
                          DropdownMenuItem(
                              value: 'chess960', child: Text('Chess960')),
                        ],
                        onChanged: (value) => setDialogState(
                            () => variant = value ?? 'standard')),
                    TextField(
                        controller: fen,
                        maxLines: 2,
                        decoration: const InputDecoration(
                            labelText: 'Custom starting FEN (optional)')),
                  ]),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Cancel')),
                    FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('Create')),
                  ],
                )));
    if (choice != true) {
      fen.dispose();
      return;
    }
    await _perform((api) async {
      final room = await api.createRoom(
        displayName: _name.text.trim(),
        side: _side.name,
        variant: variant,
        initialFen: fen.text.trim(),
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
          session: _session,
          soundsEnabled: widget.soundsEnabled,
        ),
      ));
    });
    fen.dispose();
  }

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
            session: _session,
            soundsEnabled: widget.soundsEnabled,
          ),
        ));
      });

  _MobileApi get _authenticatedApi =>
      _MobileApi(_server.text, _token, _cookie, session: _session);

  Future<void> _openProfile() async {
    final deleted = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (_) => ProfilePage(
        load: _authenticatedApi.profile,
        exportData: _authenticatedApi.exportAccountData,
        deleteAccount: _authenticatedApi.deleteAccount,
        save: (data) async {
          final profile = await _authenticatedApi.updateProfile(data);
          if (mounted) {
            setState(() {
              _displayName = profile['display_name'] as String?;
              _name.text = _displayName ?? _name.text;
            });
          }
          return profile;
        },
      ),
    ));
    if (deleted == true) await _logout();
  }

  Future<void> _openHistory() async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => GameHistoryPage(
          load: _authenticatedApi.gameHistory,
          startAnalysis: _authenticatedApi.startGameAnalysis,
          analysisStatus: _authenticatedApi.analysisStatus,
          retryAnalysis: _authenticatedApi.retryAnalysis),
    ));
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => NotificationPage(
              load: _authenticatedApi.notifications,
              markRead: _authenticatedApi.markNotificationRead,
              markAllRead: _authenticatedApi.markAllNotificationsRead,
            )));
  }

  Future<void> _openCompetitive() async =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => CompetitiveHubPage(
              leaderboard: _authenticatedApi.leaderboard,
              puzzles: _authenticatedApi.puzzles,
              playPuzzle: _authenticatedApi.playPuzzle)));

  Future<void> _openSocial() async =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => SocialPage(
              load: _authenticatedApi.social,
              action: _authenticatedApi.socialAction,
              connectChat: _authenticatedApi.connectDirectChat)));

  Future<void> _openLiveGame(Map item, {bool spectate = false}) =>
      _perform((api) async {
        final code = item['room_code']?.toString();
        final gameId = item['id']?.toString();
        if (code == null || gameId == null) return;
        if (spectate) {
          await api.joinRoom(code, _name.text.trim(), asSpectator: true);
        }
        final game = await api.game(gameId);
        if (!mounted) return;
        await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => OnlineGamePage(
            serverUrl: _server.text,
            initialGame: game,
            sessionCookie: api.cookie,
            accessTokenProvider: api.validAccessToken,
            soundsEnabled: widget.soundsEnabled,
          ),
        ));
        final refreshed = await api.experience();
        if (mounted) setState(() => _experience = refreshed);
      });

  Future<void> _challengePlayer(String playerId) => _perform((api) async {
        final result = await api.challengePlayer(playerId);
        final code = result['room_code']?.toString();
        if (code == null || !mounted) return;
        await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ShareCodePage(
            serverUrl: _server.text,
            roomCode: code,
            displayName: _name.text.trim(),
            token: _token,
            cookie: api.cookie,
            session: _session,
            soundsEnabled: widget.soundsEnabled,
          ),
        ));
      });

  Future<void> _openTournaments() async =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => TournamentPage(
              load: _authenticatedApi.tournaments,
              action: _authenticatedApi.tournamentAction,
              create: _authenticatedApi.createTournament,
              manage: _authenticatedApi.manageTournament)));
  Future<void> _openRetention() async =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => RetentionPage(
              load: _authenticatedApi.retention,
              action: _authenticatedApi.retentionAction)));
  Future<void> _openOpenings() async =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => OpeningStatsPage(
              load: _authenticatedApi.openingStats,
              loadPractice: _authenticatedApi.openingPractice,
              gradePractice: _authenticatedApi.gradeOpeningPractice)));

  Future<String?> _stockfishMove(String fen, int level) => Platform.isWindows
      ? Future<String?>.value(null)
      : _authenticatedApi.stockfishMove(fen, level);

  Future<void> _openMatchmaking() async {
    final api = _authenticatedApi;
    await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => MatchmakingPage(
              enter: api.enterMatchmaking,
              status: api.matchmakingStatus,
              cancel: api.cancelMatchmaking,
              openRoom: (room) async {
                await Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ShareCodePage(
                        serverUrl: _server.text,
                        roomCode: room['code'] as String,
                        displayName: _name.text,
                        token: _token,
                        cookie: api.cookie,
                        session: _session,
                        soundsEnabled: widget.soundsEnabled)));
              },
            )));
  }

  Future<void> _createDailyGame() async {
    await _perform((api) async {
      final room =
          await api.createDailyRoom(displayName: _name.text, side: _side.name);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ShareCodePage(
              serverUrl: _server.text,
              roomCode: room['code'] as String,
              displayName: _name.text,
              token: _token,
              cookie: api.cookie,
              session: _session,
              soundsEnabled: widget.soundsEnabled)));
    });
  }

  Future<void> _handleHomeMenu(String action) async {
    switch (action) {
      case 'openings':
        await _openOpenings();
        return;
      case 'social':
        await _openSocial();
        return;
      case 'tournaments':
        await _openTournaments();
        return;
      case 'community':
        await _openRetention();
        return;
      case 'competitive':
        await _openCompetitive();
        return;
      case 'notifications':
        await _openNotifications();
        return;
      case 'history':
        await _openHistory();
        return;
      case 'profile':
        await _openProfile();
        return;
      case 'tutorial':
        await Navigator.of(context).push(MaterialPageRoute(
            builder: (tutorialContext) => OnboardingPage(onComplete: () async {
                  if (tutorialContext.mounted) Navigator.pop(tutorialContext);
                })));
        return;
      case 'logout':
        await _logout();
        return;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(AppLocalizations.of(context)!.appTitle),
          actions: [
            if (_signedIn)
              PopupMenuButton<String>(
                tooltip: 'Account and chess features',
                onSelected: _handleHomeMenu,
                itemBuilder: (_) => const [
                  PopupMenuItem(
                      value: 'profile',
                      child: ListTile(
                          leading: Icon(Icons.account_circle_outlined),
                          title: Text('Profile'))),
                  PopupMenuItem(
                      value: 'competitive',
                      child: ListTile(
                          leading: Icon(Icons.extension_outlined),
                          title: Text('Puzzles & leaderboard'))),
                  PopupMenuItem(
                      value: 'history',
                      child: ListTile(
                          leading: Icon(Icons.history),
                          title: Text('Game history'))),
                  PopupMenuItem(
                      value: 'notifications',
                      child: ListTile(
                          leading: Icon(Icons.notifications_none),
                          title: Text('Notifications'))),
                  PopupMenuItem(
                      value: 'social',
                      child: ListTile(
                          leading: Icon(Icons.people_outline),
                          title: Text('Friends & chat'))),
                  PopupMenuItem(
                      value: 'tournaments',
                      child: ListTile(
                          leading: Icon(Icons.workspace_premium_outlined),
                          title: Text('Tournaments'))),
                  PopupMenuItem(
                      value: 'community',
                      child: ListTile(
                          leading: Icon(Icons.emoji_events_outlined),
                          title: Text('Community & rewards'))),
                  PopupMenuItem(
                      value: 'openings',
                      child: ListTile(
                          leading: Icon(Icons.auto_graph),
                          title: Text('Opening statistics'))),
                  PopupMenuItem(
                      value: 'tutorial',
                      child: ListTile(
                          leading: Icon(Icons.school_outlined),
                          title: Text('Chess tutorial'))),
                  PopupMenuDivider(),
                  PopupMenuItem(
                      value: 'logout',
                      child: ListTile(
                          leading: Icon(Icons.logout), title: Text('Logout'))),
                ],
              ),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.sizeOf(context).width >= 900 ? 900 : 760,
              ),
              child: ListView(
                padding: EdgeInsets.fromLTRB(
                  MediaQuery.sizeOf(context).width < 380 ? 12 : 18,
                  8,
                  MediaQuery.sizeOf(context).width < 380 ? 12 : 18,
                  32,
                ),
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
                              style: TextStyle(
                                  color: Color(0xffd4e2d5), height: 1.4)),
                        ]),
                  ),
                  if (_signedIn && _experience != null) ...[
                    const SizedBox(height: 16),
                    _ExperiencePanel(
                      data: _experience!,
                      onResume: (game) => _openLiveGame(game),
                      onSpectate: (game) => _openLiveGame(game, spectate: true),
                      onChallenge: _challengePlayer,
                    ),
                  ],
                  const SizedBox(height: 22),
                  if (!_signedIn) ...[
                    Text(AppLocalizations.of(context)!.login,
                        style: Theme.of(context).textTheme.headlineSmall),
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
                      child: Text(AppLocalizations.of(context)!.login),
                    ),
                    OutlinedButton(
                      onPressed: _busy ? null : _openRegistration,
                      child: Text(AppLocalizations.of(context)!.createAccount),
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
                  Text(AppLocalizations.of(context)!.chooseSide,
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  SegmentedButton<PlayerSide>(
                    segments: const [
                      ButtonSegment(
                          value: PlayerSide.white, label: Text('White')),
                      ButtonSegment(
                          value: PlayerSide.random, label: Text('Random')),
                      ButtonSegment(
                          value: PlayerSide.black, label: Text('Black')),
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
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                    Text(
                                        AppLocalizations.of(context)!
                                            .playWithBot,
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
                              onChanged: (value) => setState(
                                  () => _selectedBotLevel = value ?? 1),
                            ),
                            const SizedBox(height: 10),
                            DropdownButtonFormField<String>(
                              initialValue: _botPersonality,
                              decoration: const InputDecoration(
                                  labelText: 'Computer personality'),
                              items: const [
                                DropdownMenuItem(
                                    value: 'balanced', child: Text('Balanced')),
                                DropdownMenuItem(
                                    value: 'aggressive',
                                    child: Text('Aggressive attacker')),
                                DropdownMenuItem(
                                    value: 'positional',
                                    child: Text('Positional strategist')),
                                DropdownMenuItem(
                                    value: 'defensive',
                                    child: Text('Solid defender')),
                                DropdownMenuItem(
                                    value: 'unpredictable',
                                    child: Text('Creative wildcard')),
                              ],
                              onChanged: (value) => setState(
                                  () => _botPersonality = value ?? 'balanced'),
                            ),
                            const SizedBox(height: 10),
                            FilledButton.icon(
                              onPressed: () =>
                                  Navigator.of(context).push(MaterialPageRoute(
                                builder: (_) => OfflineBoardPage(
                                    mode: OfflinePlayMode.bot,
                                    preferredSide: chessSide(),
                                    botLevel: _selectedBotLevel,
                                    botPersonality: _botPersonality,
                                    onBotVictory: _recordBotVictory,
                                    stockfishMove: _stockfishMove,
                                    soundsEnabled: widget.soundsEnabled,
                                    boardTheme: widget.boardTheme,
                                    soundPack: widget.soundPack),
                              )),
                              icon: const Icon(Icons.play_arrow),
                              label: const Text('Play Bot'),
                            ),
                          ]),
                    ),
                  ),
                  _PlayCard(
                    icon: Icons.bolt,
                    title: 'Rated Matchmaking',
                    subtitle: 'Live search for a close-rated player',
                    onTap: _signedIn ? _openMatchmaking : null,
                  ),
                  _PlayCard(
                    icon: Icons.people_outline,
                    title: AppLocalizations.of(context)!.playWithFriend,
                    subtitle: 'Two players on this device',
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => OfflineBoardPage(
                        preferredSide: chessSide(),
                        soundsEnabled: widget.soundsEnabled,
                        boardTheme: widget.boardTheme,
                        soundPack: widget.soundPack,
                      ),
                    )),
                  ),
                  _PlayCard(
                    icon: Icons.phone_android,
                    title: 'Play on Another Mobile',
                    subtitle: 'Create a game and share its code',
                    onTap: _busy ? null : _createOnlineGame,
                  ),
                  _PlayCard(
                      icon: Icons.calendar_today_outlined,
                      title: 'Daily Chess',
                      subtitle: 'A relaxed 24-hour correspondence clock',
                      onTap: _signedIn && !_busy ? _createDailyGame : null),
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
                    title: Text(AppLocalizations.of(context)!.appSettings),
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: widget.locale?.languageCode ?? '',
                        decoration: InputDecoration(
                            labelText: AppLocalizations.of(context)!.language),
                        items: [
                          DropdownMenuItem(
                              value: '',
                              child: Text(AppLocalizations.of(context)!
                                  .systemLanguage)),
                          DropdownMenuItem(
                              value: 'en',
                              child:
                                  Text(AppLocalizations.of(context)!.english)),
                          DropdownMenuItem(
                              value: 'hi',
                              child: Text(AppLocalizations.of(context)!.hindi)),
                          DropdownMenuItem(
                              value: 'es',
                              child:
                                  Text(AppLocalizations.of(context)!.spanish)),
                        ],
                        onChanged: (code) => widget.onLocaleChanged(
                            code == null || code.isEmpty ? null : Locale(code)),
                      ),
                      DropdownButtonFormField<ThemeMode>(
                          initialValue: widget.themeMode,
                          decoration: const InputDecoration(labelText: 'Theme'),
                          items: ThemeMode.values
                              .map((mode) => DropdownMenuItem(
                                  value: mode, child: Text(mode.name)))
                              .toList(),
                          onChanged: (mode) {
                            if (mode != null) widget.onThemeChanged(mode);
                          }),
                      SwitchListTile(
                          title: const Text('Move and game sounds'),
                          value: widget.soundsEnabled,
                          onChanged: widget.onSoundsChanged),
                      DropdownButtonFormField<String>(
                          initialValue: widget.boardTheme,
                          decoration:
                              const InputDecoration(labelText: 'Board theme'),
                          items: const [
                            DropdownMenuItem(
                                value: 'classic', child: Text('Classic wood')),
                            DropdownMenuItem(
                                value: 'forest', child: Text('Forest club')),
                            DropdownMenuItem(
                                value: 'midnight', child: Text('Midnight'))
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              widget.onBoardThemeChanged(value);
                            }
                          }),
                      DropdownButtonFormField<String>(
                          initialValue: widget.soundPack,
                          decoration:
                              const InputDecoration(labelText: 'Sound set'),
                          items: const [
                            DropdownMenuItem(
                                value: 'wood', child: Text('Wood')),
                            DropdownMenuItem(
                                value: 'soft', child: Text('Soft')),
                            DropdownMenuItem(
                                value: 'silent', child: Text('Silent'))
                          ],
                          onChanged: (value) {
                            if (value != null) widget.onSoundPackChanged(value);
                          }),
                      TextField(
                        controller: _server,
                        keyboardType: TextInputType.url,
                        decoration:
                            const InputDecoration(labelText: 'Server URL'),
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
          ),
        ),
      );
}

class _ExperiencePanel extends StatelessWidget {
  const _ExperiencePanel({
    required this.data,
    required this.onResume,
    required this.onSpectate,
    required this.onChallenge,
  });
  final Map<String, dynamic> data;
  final ValueChanged<Map> onResume;
  final ValueChanged<Map> onSpectate;
  final ValueChanged<String> onChallenge;

  @override
  Widget build(BuildContext context) {
    final recommendations = data['recommendations'] as List? ?? const [];
    final achievements = data['achievements'] as List? ?? const [];
    final goals = data['daily_goals'] as List? ?? const [];
    final live = data['live_activity'] as Map? ?? const {};
    final activeGames = live['active_games'] as List? ?? const [];
    final resumeGames = live['resume_games'] as List? ?? const [];
    final winners = live['recent_winners'] as List? ?? const [];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Your next best move',
              style: Theme.of(context).textTheme.titleMedium),
          ...recommendations.take(2).map((item) {
            final row = item as Map;
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.auto_awesome),
              title: Text(row['title']?.toString() ?? ''),
              subtitle: Text(row['detail']?.toString() ?? ''),
              trailing:
                  row['kind'] == 'REMATCH' ? const Text('Challenge') : null,
              onTap: row['kind'] == 'REMATCH' && row['player_id'] != null
                  ? () => onChallenge(row['player_id'].toString())
                  : null,
            );
          }),
          if (resumeGames.isNotEmpty) ...[
            const Divider(),
            Text('Continue playing',
                style: Theme.of(context).textTheme.titleSmall),
            ...resumeGames.map((item) {
              final game = item as Map;
              return _gameTile(game, 'Resume', onResume);
            }),
          ],
          const Divider(),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('Live now', style: Theme.of(context).textTheme.titleSmall),
            Text('${live['active_player_count'] ?? 0} players · '
                '${live['active_game_count'] ?? 0} games'),
          ]),
          ...activeGames.take(3).map((item) {
            final game = item as Map;
            return _gameTile(game, 'Watch', onSpectate,
                icon: Icons.visibility_outlined);
          }),
          if (winners.isNotEmpty) ...[
            const Divider(),
            Text('Recent champions',
                style: Theme.of(context).textTheme.titleSmall),
            ...winners.map((item) {
              final winner = item as Map;
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.emoji_events_outlined),
                title: Text(winner['player']?.toString() ?? 'Champion'),
                subtitle: Text('${winner['tournament']} · '
                    '${winner['score']} points'),
                trailing: const Text('Challenge'),
                onTap: () {
                  final id = winner['player_id']?.toString();
                  if (id != null) onChallenge(id);
                },
              );
            }),
          ],
          const Divider(),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('Achievements', style: Theme.of(context).textTheme.titleSmall),
            Text('${(data['unlocked_count'] as num? ?? 0) + 1}/'
                '${achievements.length + 1}'),
          ]),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            const Chip(
                avatar: Icon(Icons.verified, size: 17),
                label: Text('First Steps')),
            ...achievements.map((item) {
              final row = item as Map;
              return Chip(
                  avatar: Icon(
                      row['unlocked'] == true
                          ? Icons.verified
                          : Icons.lock_outline,
                      size: 17),
                  label: Text(row['name']?.toString() ?? 'Achievement'));
            }),
          ]),
          const Divider(),
          Text('Daily goals', style: Theme.of(context).textTheme.titleSmall),
          ...goals.map((item) {
            final row = item as Map;
            final done =
                (row['current'] as num? ?? 0) >= (row['target'] as num? ?? 1);
            return ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                    done ? Icons.check_circle : Icons.radio_button_unchecked,
                    color: done ? Colors.green : null),
                title: Text(row['name']?.toString() ?? ''),
                trailing: Text('${row['current']}/${row['target']}'));
          }),
        ]),
      ),
    );
  }

  Widget _gameTile(Map game, String action, ValueChanged<Map> callback,
          {IconData icon = Icons.play_circle_outline}) =>
      ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(icon),
        title: Text('${game['white']} vs ${game['black']}'),
        subtitle: Text('${game['time_control']} · ${game['ply_count']} moves'),
        trailing: Text(action),
        onTap: () => callback(game),
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
      this.cookie,
      required this.session,
      required this.soundsEnabled});
  final String serverUrl;
  final String roomCode;
  final String displayName;
  final String? token;
  final String? cookie;
  final MobileSession session;
  final bool soundsEnabled;

  @override
  State<ShareCodePage> createState() => _ShareCodePageState();
}

class _ShareCodePageState extends State<ShareCodePage> {
  WebSocket? _roomSocket;
  Map<String, dynamic>? _room;
  String? _error;
  bool _busy = false;
  bool _openingGame = false;

  @override
  void initState() {
    super.initState();
    _refresh();
    _connectLobby();
  }

  Future<void> _connectLobby() async {
    try {
      final api = _MobileApi(widget.serverUrl, widget.token, widget.cookie,
          session: widget.session);
      final token = await api.validAccessToken();
      final base = Uri.parse(widget.serverUrl);
      final uri = base.replace(
          scheme: base.scheme == 'https' ? 'wss' : 'ws',
          path: '/ws/rooms/${widget.roomCode}/');
      final headers = <String, dynamic>{};
      if (token != null) {
        headers[HttpHeaders.authorizationHeader] = 'Bearer $token';
      }
      if (widget.cookie != null) {
        headers[HttpHeaders.cookieHeader] = widget.cookie!;
      }
      final socket = await WebSocket.connect(uri.toString(),
          headers: headers.isEmpty ? null : headers);
      _roomSocket = socket;
      socket.listen((message) {
        final data = jsonDecode(message as String) as Map<String, dynamic>;
        if (data['room'] is Map && mounted) {
          setState(
              () => _room = Map<String, dynamic>.from(data['room'] as Map));
        }
        if (data['type'] == 'game.started' && data['game'] is Map) {
          _openGame(Map<String, dynamic>.from(data['game'] as Map), api);
        }
      }, onError: (_) {
        if (mounted) {
          setState(() => _error = 'Lobby connection lost. Refresh to retry.');
        }
      });
    } catch (_) {
      if (mounted) {
        setState(() =>
            _error = 'Live lobby unavailable. You can still refresh manually.');
      }
    }
  }

  Future<void> _openGame(Map<String, dynamic> game, _MobileApi api) async {
    if (_openingGame || !mounted) return;
    _openingGame = true;
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => OnlineGamePage(
        serverUrl: widget.serverUrl,
        initialGame: game,
        sessionCookie: api.cookie ?? widget.cookie,
        accessTokenProvider: api.validAccessToken,
        soundsEnabled: widget.soundsEnabled,
      ),
    ));
    _openingGame = false;
  }

  Future<void> _refresh() async {
    try {
      final api = _MobileApi(widget.serverUrl, widget.token, widget.cookie,
          session: widget.session);
      final room = await api.room(widget.roomCode);
      if (mounted) setState(() => _room = room);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    }
  }

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final api = _MobileApi(widget.serverUrl, widget.token, widget.cookie,
          session: widget.session);
      final game = await api.start(widget.roomCode);
      await _openGame(game, api);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _roomSocket?.close();
    super.dispose();
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
  _MobileApi(String baseUrl, this.token, this.cookie, {this.session})
      : base = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');
  final Uri base;
  final String? token;
  String? cookie;
  final MobileSession? session;

  Future<Map<String, String>> login(String email, String password) async {
    final data = await _request(
        'POST', 'api/auth/token/', {'email': email, 'password': password});
    return {
      'access': data['access'] as String,
      'refresh': data['refresh'] as String
    };
  }

  Future<String?> validAccessToken() async {
    if (session?.refreshToken == null) return session?.accessToken ?? token;
    try {
      await _refreshAccess();
    } catch (_) {
      return session?.accessToken ?? token;
    }
    return session?.accessToken;
  }

  Future<void> _refreshAccess() async {
    final refresh = session?.refreshToken;
    if (refresh == null) {
      throw const HttpException(
          'Your session has expired. Please log in again.');
    }
    final data = await _request(
        'POST', 'api/auth/token/refresh/', {'refresh': refresh}, false);
    await session!.updateAccess(data['access'] as String);
  }

  Future<Map<String, dynamic>> profile() async => Map<String, dynamic>.from(
      await _request('GET', 'api/accounts/me/') as Map);
  Future<Map<String, dynamic>> exportAccountData() async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/accounts/me/export/') as Map);
  Future<void> deleteAccount(String password) async {
    await _request('POST', 'api/accounts/me/delete/',
        {'password': password, 'confirmation': 'DELETE'});
    await session?.clear();
  }

  Future<Map<String, dynamic>> experience() async => Map<String, dynamic>.from(
      await _request('GET', 'api/accounts/experience/') as Map);

  Future<Map<String, dynamic>> publicProfile(String id) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/accounts/players/$id/') as Map);
  Future<Map<String, dynamic>> compareProfile(String id) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/accounts/players/$id/compare/') as Map);

  Future<Map<String, dynamic>> game(String id) async =>
      Map<String, dynamic>.from(await _request('GET', 'api/games/$id/') as Map);

  Future<Map<String, dynamic>> updateProfile(
          Map<String, dynamic> values) async =>
      Map<String, dynamic>.from(
          await _request('PATCH', 'api/accounts/me/', values) as Map);

  Future<List<Map<String, dynamic>>> gameHistory() async {
    final data = await _request('GET', 'api/games/');
    final rows =
        data is Map ? (data['results'] as List? ?? const []) : data as List;
    return rows.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<List<Map<String, dynamic>>> leaderboard(String category) async {
    final data =
        await _request('GET', 'api/accounts/leaderboard/?category=$category')
            as Map;
    return (data['results'] as List)
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> puzzles() async => Map<String, dynamic>.from(
      await _request('GET', 'api/accounts/puzzles/') as Map);

  Future<Map<String, dynamic>> playPuzzle(int id, String move) async =>
      Map<String, dynamic>.from(await _request(
          'POST', 'api/accounts/puzzles/$id/play/', {'move': move}) as Map);

  Future<Map<String, dynamic>> social() async =>
      Map<String, dynamic>.from(await _request('GET', 'api/social/') as Map);
  Future<Map<String, dynamic>> retention() async =>
      Map<String, dynamic>.from(await _request('GET', 'api/retention/') as Map);
  Future<Map<String, dynamic>> retentionAction(
          Map<String, dynamic> values) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/retention/', values) as Map);
  Future<void> presenceHeartbeat() async {
    await _request('POST', 'api/presence/heartbeat/');
  }

  Future<void> socialAction(Map<String, dynamic> values) async {
    await _request('POST', 'api/social/', values);
  }

  Future<WebSocket> connectDirectChat(int conversationId) async {
    final access = await validAccessToken();
    final uri = base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '/ws/chat/$conversationId/',
    );
    final headers = <String, dynamic>{};
    if (access != null) {
      headers[HttpHeaders.authorizationHeader] = 'Bearer $access';
    }
    if (cookie != null) headers[HttpHeaders.cookieHeader] = cookie!;
    return WebSocket.connect(uri.toString(),
        headers: headers.isEmpty ? null : headers);
  }

  Future<Map<String, dynamic>> challengePlayer(String playerId) async =>
      Map<String, dynamic>.from(await _request('POST', 'api/social/',
          {'action': 'challenge', 'user_id': playerId, 'minutes': 10}) as Map);

  Future<List<Map<String, dynamic>>> tournaments() async {
    final data = await _request('GET', 'api/tournaments/') as List;
    return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<void> tournamentAction(int id, String action) async {
    await _request('POST', 'api/tournaments/$id/', {'action': action});
  }

  Future<Map<String, dynamic>> createTournament(
          Map<String, dynamic> values) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/tournaments/', values) as Map);

  Future<Map<String, dynamic>> manageTournament(
          int id, Map<String, dynamic> values) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/tournaments/$id/', values) as Map);

  Future<List<Map<String, dynamic>>> openingStats() async {
    final data =
        await _request('GET', 'api/analysis/openings/personal/') as List;
    return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> openingPractice() async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/analysis/openings/practice/') as Map);
  Future<void> gradeOpeningPractice(String openingId, int quality) async {
    await _request('POST', 'api/analysis/openings/practice/',
        {'opening_id': openingId, 'quality': quality});
  }

  Future<String?> stockfishMove(String fen, int level) async {
    final data = await _request(
        'POST', 'api/stockfish/best-move/', {'fen': fen, 'level': level});
    return data['bestmove'] as String?;
  }

  Future<List<Map<String, dynamic>>> notifications() async {
    final data = await _request('GET', 'api/notifications/') as List;
    return data.map((row) => Map<String, dynamic>.from(row as Map)).toList();
  }

  Future<void> markNotificationRead(int id) async {
    await _request('POST', 'api/notifications/$id/read/');
  }

  Future<void> markAllNotificationsRead() async {
    await _request('POST', 'api/notifications/read-all/');
  }

  Future<void> registerPushDevice(String deviceToken) async {
    await _request('POST', 'api/notifications/devices/',
        {'token': deviceToken, 'platform': 'android'});
  }

  Future<Map<String, dynamic>> enterMatchmaking(String category) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/matchmaking/', {'category': category})
              as Map);
  Future<Map<String, dynamic>> matchmakingStatus(String category) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/matchmaking/?category=$category') as Map);
  Future<void> cancelMatchmaking() async {
    await _request('DELETE', 'api/matchmaking/');
  }

  Future<Map<String, dynamic>> startGameAnalysis(String gameId) async =>
      Map<String, dynamic>.from(await _request(
          'POST',
          'api/analysis/games/$gameId/start/',
          {'analysis_type': 'quick', 'depth': 10}) as Map);
  Future<Map<String, dynamic>> analysisStatus(String jobId) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/analysis/jobs/$jobId/') as Map);
  Future<Map<String, dynamic>> retryAnalysis(String jobId) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/analysis/jobs/$jobId/') as Map);

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
      {required String displayName,
      required String side,
      String variant = 'standard',
      String initialFen = ''}) async {
    final data = await _request('POST', 'api/rooms/', {
      'name': '${displayName.isEmpty ? 'Player' : displayName}\'s game',
      'host_display_name': displayName,
      'mode': 'online',
      'visibility': 'private',
      'color_preference': side,
      'clock_initial_minutes': 10,
      'allow_guests': true,
      'spectator_enabled': false,
      'variant': variant,
      'initial_fen': initialFen,
    });
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> createDailyRoom(
          {required String displayName, required String side}) async =>
      Map<String, dynamic>.from(await _request('POST', 'api/rooms/', {
        'name': 'Daily game',
        'host_display_name': displayName,
        'mode': 'online',
        'visibility': 'private',
        'color_preference': side,
        'clock_initial_minutes': 1440,
        'increment_seconds': 0,
        'rated': false,
        'allow_guests': false,
        'spectator_enabled': true
      }) as Map);

  Future<void> joinRoom(String code, String name, {bool asSpectator = false}) =>
      _request('POST', 'api/rooms/$code/join/',
          {'display_name': name, 'as_spectator': asSpectator});
  Future<Map<String, dynamic>> room(String code) async =>
      Map<String, dynamic>.from(
          await _request('GET', 'api/rooms/$code/') as Map);
  Future<Map<String, dynamic>> start(String code) async =>
      Map<String, dynamic>.from(
          await _request('POST', 'api/rooms/$code/start/') as Map);

  Future<dynamic> _request(String method, String path,
      [Map<String, dynamic>? body, bool retryAfterRefresh = true]) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, base.resolve(path));
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final access = session?.accessToken ?? token;
      if (access != null) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $access');
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
      if (response.statusCode == HttpStatus.unauthorized &&
          retryAfterRefresh &&
          session?.refreshToken != null) {
        await _refreshAccess();
        return _request(method, path, body, false);
      }
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
