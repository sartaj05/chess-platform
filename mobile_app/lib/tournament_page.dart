import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class TournamentPage extends StatefulWidget {
  const TournamentPage({
    super.key,
    required this.load,
    required this.action,
    required this.create,
    required this.manage,
  });

  final Future<List<Map<String, dynamic>>> Function() load;
  final Future<void> Function(int, String) action;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic>) create;
  final Future<Map<String, dynamic>> Function(int, Map<String, dynamic>) manage;

  @override
  State<TournamentPage> createState() => _TournamentPageState();
}

class _TournamentPageState extends State<TournamentPage> {
  late Future<List<Map<String, dynamic>>> data = widget.load();

  void reload() => setState(() {
        data = widget.load();
      });

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Tournaments'),
          actions: [
            IconButton(
              icon: const Icon(Icons.add),
              tooltip: 'Create tournament',
              onPressed: _create,
            )
          ],
        ),
        body: FutureBuilder<List<Map<String, dynamic>>>(
          future: data,
          builder: (_, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            return RefreshIndicator(
              onRefresh: () async {
                reload();
                await data;
              },
              child: ListView(
                padding: const EdgeInsets.all(12),
                children: snapshot.data!.map(_card).toList(),
              ),
            );
          },
        ),
      );

  Widget _card(Map<String, dynamic> tournament) => Card(
        child: ExpansionTile(
          title: Text(tournament['name'].toString()),
          subtitle: Text(
            '${tournament['format']} · ${tournament['time_control']} · '
            '${tournament['player_count']}/${tournament['max_players']}',
          ),
          children: [
            ListTile(
              title: const Text('Invite code'),
              subtitle: Text(tournament['invite_code']?.toString() ?? ''),
              trailing: IconButton(
                icon: const Icon(Icons.share),
                onPressed: () => _share(tournament),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(tournament['description']?.toString() ?? ''),
            ),
            ...(tournament['standings'] as List? ?? const []).map((raw) {
              final standing = raw as Map;
              return ListTile(
                dense: true,
                title: Text(standing['name'].toString()),
                subtitle: Text(
                    'Buchholz ${standing['buchholz'] ?? '0'} · SB ${standing['sonneborn_berger'] ?? '0'}'),
                trailing: tournament['is_organizer'] == true &&
                        tournament['status'] == 'registration' &&
                        standing['user_id'] != tournament['organizer_id']
                    ? IconButton(
                        icon: const Icon(Icons.person_remove_outlined),
                        tooltip: 'Remove player',
                        onPressed: () => _manage(tournament, {
                          'action': 'remove_player',
                          'entry_id': standing['entry_id'],
                        }),
                      )
                    : Text(standing['score'].toString()),
              );
            }),
            ..._rounds(tournament),
            if (tournament['is_organizer'] == true)
              _organizerControls(tournament)
            else
              FilledButton(
                onPressed: () async {
                  await widget.action(
                    tournament['id'] as int,
                    tournament['joined'] == true ? 'withdraw' : 'join',
                  );
                  reload();
                },
                child: Text(tournament['joined'] == true ? 'Withdraw' : 'Join'),
              ),
          ],
        ),
      );

  Iterable<Widget> _rounds(Map<String, dynamic> tournament) =>
      (tournament['rounds'] as List? ?? const []).map((raw) {
        final round = raw as Map;
        return ExpansionTile(
          title: Text('Round ${round['number']} · ${round['status']}'),
          children:
              (round['pairings'] as List? ?? const []).map<Widget>((item) {
            final pairing = item as Map;
            return ListTile(
              title: Text('${pairing['white']} vs ${pairing['black']}'),
              subtitle:
                  Text('Board ${pairing['board']} · ${pairing['result']}'),
              trailing: tournament['is_organizer'] == true &&
                      pairing['result'] == 'pending'
                  ? PopupMenuButton<String>(
                      tooltip: 'Report result',
                      onSelected: (result) => _manage(tournament, {
                        'action': 'report_result',
                        'pairing_id': pairing['pairing_id'],
                        'result': result,
                      }),
                      itemBuilder: (_) => const [
                        PopupMenuItem(
                            value: 'white_win', child: Text('White wins')),
                        PopupMenuItem(value: 'draw', child: Text('Draw')),
                        PopupMenuItem(
                            value: 'black_win', child: Text('Black wins')),
                      ],
                    )
                  : null,
            );
          }).toList(),
        );
      });

  Widget _organizerControls(Map<String, dynamic> tournament) => Padding(
        padding: const EdgeInsets.all(12),
        child: Wrap(spacing: 8, runSpacing: 8, children: [
          if (tournament['status'] == 'registration')
            FilledButton.icon(
              onPressed: () => _manage(tournament, {'action': 'start'}),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start'),
            ),
          if (!['completed', 'cancelled'].contains(tournament['status']))
            OutlinedButton.icon(
              onPressed: () => _manage(tournament, {'action': 'cancel'}),
              icon: const Icon(Icons.cancel_outlined),
              label: const Text('Cancel'),
            ),
          OutlinedButton.icon(
            onPressed: () => _announcement(tournament),
            icon: const Icon(Icons.campaign_outlined),
            label: const Text('Announce'),
          ),
        ]),
      );

  Future<void> _manage(
      Map<String, dynamic> tournament, Map<String, dynamic> action) async {
    await widget.manage(tournament['id'] as int, action);
    reload();
  }

  Future<void> _share(Map<String, dynamic> tournament) async {
    final code = tournament['invite_code']?.toString() ?? '';
    await Clipboard.setData(ClipboardData(
      text: 'Join ${tournament['name']} on Chess Platform with code $code',
    ));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invite copied. Share it anywhere.')),
      );
    }
  }

  Future<void> _create() async {
    final name = TextEditingController();
    final description = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Create tournament'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Name')),
            TextField(
              controller: description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Description'),
            ),
          ]),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Create')),
        ],
      ),
    );
    if (confirmed == true && name.text.trim().isNotEmpty) {
      await widget.create({
        'name': name.text.trim(),
        'description': description.text.trim(),
        'format': 'swiss',
        'starts_at': DateTime.now()
            .add(const Duration(hours: 1))
            .toUtc()
            .toIso8601String(),
        'max_players': 16,
        'clock_initial_minutes': 10,
        'increment_seconds': 0,
        'is_public': true,
      });
      reload();
    }
    name.dispose();
    description.dispose();
  }

  Future<void> _announcement(Map<String, dynamic> tournament) async {
    final controller = TextEditingController();
    final body = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Tournament announcement'),
        content: TextField(controller: controller, maxLength: 500),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Publish'),
          )
        ],
      ),
    );
    controller.dispose();
    if (body?.trim().isNotEmpty == true) {
      await _manage(tournament, {'action': 'announce', 'body': body});
    }
  }
}
