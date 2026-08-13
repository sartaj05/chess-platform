import 'package:flutter/material.dart';

class CompetitiveHubPage extends StatefulWidget {
  const CompetitiveHubPage(
      {super.key,
      required this.leaderboard,
      required this.puzzles,
      required this.playPuzzle});
  final Future<List<Map<String, dynamic>>> Function(String category)
      leaderboard;
  final Future<List<Map<String, dynamic>>> Function() puzzles;
  final Future<Map<String, dynamic>> Function(int id, String move) playPuzzle;
  @override
  State<CompetitiveHubPage> createState() => _CompetitiveHubPageState();
}

class _CompetitiveHubPageState extends State<CompetitiveHubPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);
  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: const Text('Chess Community'),
            bottom: TabBar(
                controller: _tabs,
                tabs: const [Tab(text: 'Leaderboard'), Tab(text: 'Puzzles')])),
        body: TabBarView(controller: _tabs, children: [
          _Leaderboard(load: widget.leaderboard),
          _Puzzles(load: widget.puzzles, play: widget.playPuzzle),
        ]),
      );
}

class _Leaderboard extends StatefulWidget {
  const _Leaderboard({required this.load});
  final Future<List<Map<String, dynamic>>> Function(String) load;
  @override
  State<_Leaderboard> createState() => _LeaderboardState();
}

class _LeaderboardState extends State<_Leaderboard> {
  String category = 'blitz';
  @override
  Widget build(BuildContext context) => Column(children: [
        SegmentedButton<String>(segments: const [
          ButtonSegment(value: 'bullet', label: Text('Bullet')),
          ButtonSegment(value: 'blitz', label: Text('Blitz')),
          ButtonSegment(value: 'rapid', label: Text('Rapid'))
        ], selected: {
          category
        }, onSelectionChanged: (v) => setState(() => category = v.first)),
        Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
                future: widget.load(category),
                builder: (context, snapshot) {
                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final rows = snapshot.data!;
                  return ListView.builder(
                      itemCount: rows.length,
                      itemBuilder: (_, i) {
                        final p = rows[i];
                        return ListTile(
                            leading: CircleAvatar(child: Text('${i + 1}')),
                            title:
                                Text(p['display_name']?.toString() ?? 'Player'),
                            subtitle: Text('${p['country'] ?? ''}'),
                            trailing: Text('${p['${category}_rating'] ?? 1200}',
                                style: Theme.of(context).textTheme.titleMedium),
                            onTap: () => showDialog(
                                context: context,
                                builder: (_) => AlertDialog(
                                    title: Text(p['display_name']?.toString() ??
                                        'Player'),
                                    content: Text(
                                        'Bullet ${p['bullet_rating']}\nBlitz ${p['blitz_rating']}\nRapid ${p['rapid_rating']}\n${p['bio'] ?? ''}'))));
                      });
                }))
      ]);
}

class _Puzzles extends StatelessWidget {
  const _Puzzles({required this.load, required this.play});
  final Future<List<Map<String, dynamic>>> Function() load;
  final Future<Map<String, dynamic>> Function(int, String) play;
  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
          future: load(),
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            return ListView(
                children: snapshot.data!
                    .map((p) => ListTile(
                        leading: const Icon(Icons.extension),
                        title: Text(p['title'].toString()),
                        subtitle: Text('${p['difficulty']} · ${p['rating']}'),
                        onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) =>
                                    _PuzzlePlay(puzzle: p, play: play)))))
                    .toList());
          });
}

class _PuzzlePlay extends StatefulWidget {
  const _PuzzlePlay({required this.puzzle, required this.play});
  final Map<String, dynamic> puzzle;
  final Future<Map<String, dynamic>> Function(int, String) play;
  @override
  State<_PuzzlePlay> createState() => _PuzzlePlayState();
}

class _PuzzlePlayState extends State<_PuzzlePlay> {
  final move = TextEditingController();
  String result = 'Enter a move in UCI notation, for example e2e4.';
  @override
  void dispose() {
    move.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text(widget.puzzle['title'].toString())),
      body: Padding(
          padding: const EdgeInsets.all(20),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            SelectableText('Position: ${widget.puzzle['fen']}'),
            const SizedBox(height: 16),
            TextField(
                controller: move,
                decoration: const InputDecoration(labelText: 'Your move')),
            const SizedBox(height: 12),
            FilledButton(
                onPressed: () async {
                  final r =
                      await widget.play(widget.puzzle['id'] as int, move.text);
                  setState(() => result = r['correct'] == true
                      ? (r['status'] == 'solved'
                          ? 'Solved!'
                          : 'Correct. Reply: ${r['reply']}')
                      : 'Try again.');
                },
                child: const Text('Play move')),
            const SizedBox(height: 16),
            Text(result)
          ])));
}
