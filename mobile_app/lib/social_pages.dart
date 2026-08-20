import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

class SocialPage extends StatefulWidget {
  const SocialPage(
      {super.key, required this.load, required this.action, this.connectChat});
  final Future<Map<String, dynamic>> Function() load;
  final Future<void> Function(Map<String, dynamic>) action;
  final Future<WebSocket> Function(int conversationId)? connectChat;
  @override
  State<SocialPage> createState() => _SocialPageState();
}

class _SocialPageState extends State<SocialPage> {
  late Future<Map<String, dynamic>> data = widget.load();
  final email = TextEditingController();
  void reload() => setState(() {
        data = widget.load();
      });
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
                    onTap: () => _openChat(c));
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

  Future<void> _openChat(Map conversation) async {
    await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => MobileChatThreadPage(
            conversationId: conversation['id'] as int,
            player: Map<String, dynamic>.from(conversation['player'] as Map),
            initialMessages: (conversation['messages'] as List? ?? const [])
                .map((item) => Map<String, dynamic>.from(item as Map))
                .toList(),
            loadSocial: widget.load,
            action: widget.action,
            connectSocket: widget.connectChat)));
    reload();
  }
}

class MobileChatThreadPage extends StatefulWidget {
  const MobileChatThreadPage(
      {super.key,
      required this.conversationId,
      required this.player,
      required this.initialMessages,
      required this.loadSocial,
      required this.action,
      this.connectSocket});
  final int conversationId;
  final Map<String, dynamic> player;
  final List<Map<String, dynamic>> initialMessages;
  final Future<Map<String, dynamic>> Function() loadSocial;
  final Future<void> Function(Map<String, dynamic>) action;
  final Future<WebSocket> Function(int conversationId)? connectSocket;
  @override
  State<MobileChatThreadPage> createState() => _MobileChatThreadPageState();
}

class _MobileChatThreadPageState extends State<MobileChatThreadPage> {
  late List<Map<String, dynamic>> messages = widget.initialMessages;
  final controller = TextEditingController();
  bool busy = false;
  WebSocket? socket;
  Timer? reconnectTimer;
  bool realtimeConnected = false;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  Future<void> _connect() async {
    if (widget.connectSocket == null || !mounted) return;
    try {
      final connected = await widget.connectSocket!(widget.conversationId);
      if (!mounted) {
        await connected.close();
        return;
      }
      socket = connected;
      setState(() => realtimeConnected = true);
      connected.add(jsonEncode({'type': 'chat.read'}));
      connected.listen(_receive,
          onDone: _reconnect, onError: (_) => _reconnect());
    } catch (_) {
      _reconnect();
    }
  }

  void _reconnect() {
    socket = null;
    if (mounted) setState(() => realtimeConnected = false);
    reconnectTimer?.cancel();
    reconnectTimer = Timer(const Duration(seconds: 2), _connect);
  }

  void _receive(dynamic raw) {
    final data = jsonDecode(raw as String) as Map<String, dynamic>;
    if (data['type'] == 'chat.message' && data['message'] is Map) {
      final incoming = Map<String, dynamic>.from(data['message'] as Map);
      final mine =
          incoming['sender_id']?.toString() != widget.player['id']?.toString();
      incoming.addAll({
        'mine': mine,
        'unsent': false,
        'delivery_state': mine ? 'sent' : null,
      });
      if (mounted) setState(() => messages.insert(0, incoming));
      if (!mine) socket?.add(jsonEncode({'type': 'chat.read'}));
    } else if (data['type'] == 'chat.read' &&
        data['user_id']?.toString() == widget.player['id']?.toString()) {
      if (mounted) {
        setState(() {
          for (final message
              in messages.where((item) => item['mine'] == true)) {
            message['delivery_state'] = 'read';
            message['read_at'] = DateTime.now().toIso8601String();
          }
        });
      }
    }
  }

  Future<void> reload() async {
    final data = await widget.loadSocial();
    final conversations = data['conversations'] as List? ?? const [];
    final row = conversations
        .cast<Map>()
        .where((item) => item['id'] == widget.conversationId)
        .firstOrNull;
    if (row != null && mounted) {
      setState(() => messages = (row['messages'] as List? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList());
    }
  }

  Future<void> run(Map<String, dynamic> values) async {
    setState(() => busy = true);
    try {
      await widget.action(values);
      await reload();
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> edit(Map message) async {
    final edit = TextEditingController(text: message['body']?.toString() ?? '');
    final body = await showDialog<String>(
        context: context,
        builder: (_) => AlertDialog(
                title: const Text('Edit message'),
                content: TextField(
                    controller: edit, autofocus: true, maxLength: 2000),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Cancel')),
                  FilledButton(
                      onPressed: () => Navigator.pop(context, edit.text),
                      child: const Text('Save'))
                ]));
    edit.dispose();
    if (body?.trim().isNotEmpty == true) {
      await run({
        'action': 'edit_message',
        'conversation_id': widget.conversationId,
        'message_id': message['id'],
        'body': body
      });
    }
  }

  @override
  void dispose() {
    reconnectTimer?.cancel();
    socket?.close();
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rows = messages.reversed.toList();
    return Scaffold(
        appBar: AppBar(
            title: Text(widget.player['display_name']?.toString() ?? 'Chat')),
        body: SafeArea(
            child: Column(children: [
          Expanded(
              child: ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: rows.length,
                  itemBuilder: (_, index) {
                    final message = rows[index];
                    final mine = message['mine'] == true;
                    final unsent = message['unsent'] == true;
                    final delivery = message['delivery_state']?.toString() ??
                        (message['read_at'] != null
                            ? 'read'
                            : message['delivered_at'] != null
                                ? 'delivered'
                                : 'sent');
                    return Align(
                        alignment:
                            mine ? Alignment.centerRight : Alignment.centerLeft,
                        child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Column(
                                crossAxisAlignment: mine
                                    ? CrossAxisAlignment.end
                                    : CrossAxisAlignment.start,
                                children: [
                                  Container(
                                      constraints:
                                          const BoxConstraints(maxWidth: 310),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 14, vertical: 10),
                                      decoration: BoxDecoration(
                                          color: unsent
                                              ? Colors.grey.shade200
                                              : mine
                                                  ? Theme.of(context)
                                                      .colorScheme
                                                      .primary
                                                  : Colors.white,
                                          borderRadius:
                                              BorderRadius.circular(15),
                                          border: mine && !unsent
                                              ? null
                                              : Border.all(
                                                  color: Colors.grey.shade300)),
                                      child: Text(
                                          unsent
                                              ? 'Message unsent'
                                              : message['body']?.toString() ??
                                                  '',
                                          style: TextStyle(
                                              color: mine && !unsent
                                                  ? Colors.white
                                                  : Colors.black87,
                                              fontStyle: unsent
                                                  ? FontStyle.italic
                                                  : null))),
                                  if (mine && !unsent)
                                    Text(
                                        delivery == 'read'
                                            ? 'Read'
                                            : delivery == 'delivered'
                                                ? 'Delivered'
                                                : 'Sent',
                                        style: Theme.of(context)
                                            .textTheme
                                            .labelSmall),
                                  if (mine && !unsent)
                                    PopupMenuButton<String>(
                                        padding: EdgeInsets.zero,
                                        iconSize: 18,
                                        onSelected: (value) {
                                          if (value == 'edit') {
                                            edit(message);
                                          } else {
                                            run({
                                              'action': value,
                                              'conversation_id':
                                                  widget.conversationId,
                                              'message_id': message['id']
                                            });
                                          }
                                        },
                                        itemBuilder: (_) => [
                                              if (message['can_edit'] == true)
                                                const PopupMenuItem(
                                                    value: 'edit',
                                                    child: Text('Edit')),
                                              if (message['can_delete'] == true)
                                                const PopupMenuItem(
                                                    value: 'delete_message',
                                                    child:
                                                        Text('Delete for me')),
                                              if (message['can_unsend'] == true)
                                                const PopupMenuItem(
                                                    value: 'unsend_message',
                                                    child: Text(
                                                        'Unsend for everyone'))
                                            ])
                                ])));
                  })),
          if (busy) const LinearProgressIndicator(),
          Padding(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                if (widget.connectSocket != null)
                  Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: Icon(realtimeConnected ? Icons.wifi : Icons.sync,
                          size: 18,
                          color: realtimeConnected
                              ? Colors.green
                              : Colors.orange)),
                Expanded(
                    child: TextField(
                        controller: controller,
                        maxLength: 2000,
                        decoration: const InputDecoration(
                            hintText: 'Write a message…', counterText: ''))),
                IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: busy
                        ? null
                        : () async {
                            final body = controller.text.trim();
                            if (body.isEmpty) return;
                            controller.clear();
                            if (socket != null) {
                              socket!.add(jsonEncode(
                                  {'type': 'chat.send', 'body': body}));
                            } else {
                              await run({
                                'action': 'message',
                                'user_id': widget.player['id'],
                                'body': body
                              });
                            }
                          })
              ]))
        ])));
  }
}

class LegacyTournamentPage extends StatefulWidget {
  const LegacyTournamentPage(
      {super.key, required this.load, required this.action});
  final Future<List<Map<String, dynamic>>> Function() load;
  final Future<void> Function(int, String) action;
  @override
  State<LegacyTournamentPage> createState() => _LegacyTournamentPageState();
}

class _LegacyTournamentPageState extends State<LegacyTournamentPage> {
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
