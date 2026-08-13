import 'package:flutter/material.dart';

class SocialPage extends StatefulWidget {
  const SocialPage({super.key, required this.load, required this.action});
  final Future<Map<String, dynamic>> Function() load;
  final Future<void> Function(Map<String, dynamic>) action;
  @override
  State<SocialPage> createState() => _SocialPageState();
}

class _SocialPageState extends State<SocialPage> {
  late Future<Map<String, dynamic>> data = widget.load();
  final email = TextEditingController();
  void reload() => setState(() => data = widget.load());
  Future<void> run(Map<String, dynamic> value) async {
    await widget.action(value);
    reload();
  }

  @override
  void dispose() {
    email.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Friends & messages')),
      body: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final friendships = snapshot.data!['friendships'] as List? ?? [];
            final chats = snapshot.data!['conversations'] as List? ?? [];
            return ListView(padding: const EdgeInsets.all(16), children: [
              TextField(
                  controller: email,
                  decoration: InputDecoration(
                      labelText: 'Friend email',
                      suffixIcon: IconButton(
                          icon: const Icon(Icons.person_add),
                          onPressed: () async {
                            await run(
                                {'action': 'request', 'email': email.text});
                            email.clear();
                          }))),
              const SizedBox(height: 20),
              Text('Friends', style: Theme.of(context).textTheme.titleLarge),
              ...friendships.map((raw) {
                final f = raw as Map;
                final p = f['player'] as Map;
                return Card(
                    child: ListTile(
                        title: Text(p['display_name'].toString()),
                        subtitle: Text(f['status'].toString()),
                        trailing: Wrap(children: [
                          if (f['status'] == 'pending' && f['incoming'] == true)
                            IconButton(
                                icon: const Icon(Icons.check),
                                onPressed: () => run({
                                      'action': 'accept',
                                      'friendship_id': f['id']
                                    })),
                          if (f['status'] == 'accepted')
                            PopupMenuButton<String>(
                                onSelected: (a) => _friendAction(a, p),
                                itemBuilder: (_) => const [
                                      PopupMenuItem(
                                          value: 'challenge',
                                          child: Text('Challenge')),
                                      PopupMenuItem(
                                          value: 'message',
                                          child: Text('Message')),
                                      PopupMenuItem(
                                          value: 'block', child: Text('Block')),
                                      PopupMenuItem(
                                          value: 'report',
                                          child: Text('Report'))
                                    ])
                        ])));
              }),
              const SizedBox(height: 20),
              Text('Chats', style: Theme.of(context).textTheme.titleLarge),
              ...chats.map((raw) {
                final c = raw as Map;
                final p = c['player'] as Map;
                return ListTile(
                    leading: const Icon(Icons.chat_bubble_outline),
                    title: Text(p['display_name'].toString()),
                    subtitle: Text(
                        ((c['messages'] as List?)?.firstOrNull as Map?)?['body']
                                ?.toString() ??
                            'No messages'),
                    onTap: () => _message(p));
              })
            ]);
          }));
  void _friendAction(String action, Map player) {
    if (action == 'message') {
      _message(player);
      return;
    }
    run({
      'action': action,
      'user_id': player['id'],
      if (action == 'report') 'reason': 'unsporting'
    });
  }

  Future<void> _message(Map player) async {
    final controller = TextEditingController();
    final text = await showDialog<String>(
        context: context,
        builder: (_) => AlertDialog(
                title: Text('Message ${player['display_name']}'),
                content: TextField(controller: controller, maxLength: 2000),
                actions: [
                  FilledButton(
                      onPressed: () => Navigator.pop(context, controller.text),
                      child: const Text('Send'))
                ]));
    controller.dispose();
    if (text?.trim().isNotEmpty == true) {
      await run({'action': 'message', 'user_id': player['id'], 'body': text});
    }
  }
}

class TournamentPage extends StatefulWidget {
  const TournamentPage({super.key, required this.load, required this.action});
  final Future<List<Map<String, dynamic>>> Function() load;
  final Future<void> Function(int, String) action;
  @override
  State<TournamentPage> createState() => _TournamentPageState();
}

class _TournamentPageState extends State<TournamentPage> {
  late Future<List<Map<String, dynamic>>> data = widget.load();
  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Tournaments')),
      body: FutureBuilder<List<Map<String, dynamic>>>(
          future: data,
          builder: (_, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            return ListView(
                children: snapshot.data!
                    .map((t) => Card(
                            child: ExpansionTile(
                                title: Text(t['name'].toString()),
                                subtitle: Text(
                                    '${t['format']} · ${t['time_control']} · ${t['player_count']}/${t['max_players']}'),
                                children: [
                              Padding(
                                  padding: const EdgeInsets.all(12),
                                  child:
                                      Text(t['description']?.toString() ?? '')),
                              ...(t['standings'] as List).map((s) => ListTile(
                                  title: Text((s as Map)['name'].toString()),
                                  trailing: Text(s['score'].toString()))),
                              FilledButton(
                                  onPressed: () async {
                                    await widget.action(
                                        t['id'] as int,
                                        t['joined'] == true
                                            ? 'withdraw'
                                            : 'join');
                                    setState(() => data = widget.load());
                                  },
                                  child: Text(t['joined'] == true
                                      ? 'Withdraw'
                                      : 'Join'))
                            ])))
                    .toList());
          }));
}

class OpeningStatsPage extends StatelessWidget {
  const OpeningStatsPage({super.key, required this.load});
  final Future<List<Map<String, dynamic>>> Function() load;
  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('My openings')),
      body: FutureBuilder<List<Map<String, dynamic>>>(
          future: load(),
          builder: (_, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.data!.isEmpty) {
              return const Center(
                  child:
                      Text('Finish games to build your opening statistics.'));
            }
            return ListView(
                children: snapshot.data!
                    .map((row) => Card(
                        child: ListTile(
                            leading: CircleAvatar(
                                child: Text(row['eco'].toString())),
                            title: Text(row['name'].toString()),
                            subtitle: Text(
                                '${row['games']} games · ${row['wins']} wins · ${row['draws']} draws'),
                            trailing: Text('${row['losses']} losses'))))
                    .toList());
          }));
}
