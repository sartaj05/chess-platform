import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class RetentionPage extends StatefulWidget {
  const RetentionPage({super.key, required this.load, required this.action});
  final Future<Map<String, dynamic>> Function() load;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic>) action;

  @override
  State<RetentionPage> createState() => _RetentionPageState();
}

class _RetentionPageState extends State<RetentionPage> {
  late Future<Map<String, dynamic>> data = widget.load();
  void reload() => setState(() => data = widget.load());

  Future<void> act(Map<String, dynamic> values) async {
    final result = await widget.action(values);
    if (!mounted) return;
    final shareValue = result['code'] ?? result['share_url'];
    if (shareValue != null) {
      await Clipboard.setData(ClipboardData(text: shareValue.toString()));
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Share value copied.')));
      }
    }
    reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Community & rewards')),
        body: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (_, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final value = snapshot.data!;
            final missions = value['missions'] as List? ?? const [];
            final clubs = value['club_leaderboard'] as List? ?? const [];
            final news = value['news'] as List? ?? const [];
            final achievements = value['achievements'] as List? ?? const [];
            return RefreshIndicator(
              onRefresh: () async {
                reload();
                await data;
              },
              child: ListView(padding: const EdgeInsets.all(16), children: [
                Card(
                    child: ListTile(
                        leading: const Icon(Icons.stars),
                        title: Text('${value['points'] ?? 0} reward points'),
                        subtitle: Text(value['season'] == null
                            ? 'Complete missions to earn rewards'
                            : '${value['season']['name']} · ${value['season']['reward_title']}'))),
                const SizedBox(height: 12),
                Text('Missions', style: Theme.of(context).textTheme.titleLarge),
                ...missions.map((raw) {
                  final item = raw as Map;
                  return Card(
                      child: ListTile(
                          title: Text(item['title'].toString()),
                          subtitle: Text(
                              '${item['description']}\n${item['progress']}/${item['target']} · ${item['period']}'),
                          isThreeLine: true,
                          trailing: item['completed'] == true &&
                                  item['claimed'] != true
                              ? FilledButton(
                                  onPressed: () => act({
                                        'action': 'claim_mission',
                                        'mission_id': item['id']
                                      }),
                                  child: Text('+${item['reward_points']}'))
                              : item['claimed'] == true
                                  ? const Icon(Icons.check_circle,
                                      color: Colors.green)
                                  : null));
                }),
                FilledButton.icon(
                    onPressed: () => act({'action': 'create_referral'}),
                    icon: const Icon(Icons.person_add_alt_1),
                    label: const Text('Create referral invite')),
                const SizedBox(height: 18),
                Text('Share achievements',
                    style: Theme.of(context).textTheme.titleLarge),
                Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: achievements
                        .where((raw) => (raw as Map)['unlocked'] == true)
                        .map((raw) {
                      final item = raw as Map;
                      final key = item['name']
                          .toString()
                          .toLowerCase()
                          .replaceAll(' ', '_');
                      return ActionChip(
                          avatar: const Icon(Icons.share, size: 18),
                          label: Text(item['name'].toString()),
                          onPressed: () => act({
                                'action': 'share_achievement',
                                'achievement_key': key
                              }));
                    }).toList()),
                const SizedBox(height: 18),
                Text('Club leaderboard',
                    style: Theme.of(context).textTheme.titleLarge),
                ...clubs.asMap().entries.map((entry) {
                  final club = entry.value as Map;
                  return ListTile(
                      leading: CircleAvatar(child: Text('${entry.key + 1}')),
                      title: Text(club['name'].toString()),
                      subtitle: Text(
                          '${club['members']} members · ${club['league_wins']} wins'),
                      trailing: Text(club['score'].toString()));
                }),
                const SizedBox(height: 18),
                Text('News & announcements',
                    style: Theme.of(context).textTheme.titleLarge),
                ...news.map((raw) {
                  final item = raw as Map;
                  return Card(
                      child: ListTile(
                          title: Text(item['title'].toString()),
                          subtitle: Text(item['summary'].toString())));
                }),
              ]),
            );
          },
        ),
      );
}
