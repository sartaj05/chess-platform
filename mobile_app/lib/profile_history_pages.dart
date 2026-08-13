import 'package:flutter/material.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key, required this.load, required this.save});

  final Future<Map<String, dynamic>> Function() load;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic>) save;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final _displayName = TextEditingController();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _bio = TextEditingController();
  final _country = TextEditingController();
  Map<String, dynamic>? _profile;
  String? _error;
  bool _busy = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final profile = await widget.load();
      _displayName.text = profile['display_name']?.toString() ?? '';
      _firstName.text = profile['first_name']?.toString() ?? '';
      _lastName.text = profile['last_name']?.toString() ?? '';
      _bio.text = profile['bio']?.toString() ?? '';
      _country.text = profile['country']?.toString() ?? '';
      if (mounted) setState(() => _profile = profile);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    setState(() { _busy = true; _error = null; });
    try {
      final profile = await widget.save({
        'display_name': _displayName.text.trim(),
        'first_name': _firstName.text.trim(),
        'last_name': _lastName.text.trim(),
        'bio': _bio.text.trim(),
        'country': _country.text.trim(),
      });
      if (mounted) {
        setState(() => _profile = profile);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profile updated.')));
      }
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    for (final controller in [_displayName, _firstName, _lastName, _bio, _country]) { controller.dispose(); }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('My Profile')),
    body: _busy && _profile == null
        ? const Center(child: CircularProgressIndicator())
        : ListView(padding: const EdgeInsets.all(20), children: [
            CircleAvatar(radius: 42, child: Text((_displayName.text.isEmpty ? 'P' : _displayName.text[0]).toUpperCase(), style: const TextStyle(fontSize: 30))),
            const SizedBox(height: 12),
            Text(_profile?['email']?.toString() ?? '', textAlign: TextAlign.center),
            Text('Bot level ${_profile?['bot_level'] ?? 1}', textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 20),
            TextField(controller: _displayName, decoration: const InputDecoration(labelText: 'Display name')),
            TextField(controller: _firstName, decoration: const InputDecoration(labelText: 'First name')),
            TextField(controller: _lastName, decoration: const InputDecoration(labelText: 'Last name')),
            TextField(controller: _country, decoration: const InputDecoration(labelText: 'Country')),
            TextField(controller: _bio, maxLines: 3, decoration: const InputDecoration(labelText: 'Bio')),
            if (_error != null) Padding(padding: const EdgeInsets.all(8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
            FilledButton.icon(onPressed: _busy ? null : _save, icon: const Icon(Icons.save), label: const Text('Save profile')),
          ]),
  );
}

class GameHistoryPage extends StatefulWidget {
  const GameHistoryPage({super.key, required this.load});
  final Future<List<Map<String, dynamic>>> Function() load;

  @override
  State<GameHistoryPage> createState() => _GameHistoryPageState();
}

class _GameHistoryPageState extends State<GameHistoryPage> {
  List<Map<String, dynamic>> _games = [];
  String? _error;
  bool _busy = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _busy = true; _error = null; });
    try {
      final games = await widget.load();
      if (mounted) setState(() => _games = games);
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Game History')),
    body: RefreshIndicator(
      onRefresh: _load,
      child: _busy
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? ListView(children: [Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center))])
              : _games.isEmpty
                  ? ListView(children: const [Padding(padding: EdgeInsets.all(32), child: Text('No saved online games yet.', textAlign: TextAlign.center))])
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _games.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, index) {
                        final game = _games[index];
                        return Card(child: ListTile(
                          leading: CircleAvatar(child: Text((game['result'] ?? '*').toString())),
                          title: Text('${game['white_display_name'] ?? 'White'} vs ${game['black_display_name'] ?? 'Black'}'),
                          subtitle: Text('${game['status'] ?? ''} · ${game['termination'] ?? 'in progress'}\n${game['created_at'] ?? ''}'),
                          isThreeLine: true,
                          trailing: Text('${game['ply_count'] ?? 0} moves'),
                        ));
                      }),
    ),
  );
}
