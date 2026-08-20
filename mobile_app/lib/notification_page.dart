import 'package:flutter/material.dart';

import 'deep_link_service.dart';

class NotificationPage extends StatefulWidget {
  const NotificationPage(
      {super.key,
      required this.load,
      required this.markRead,
      required this.markAllRead});
  final Future<List<Map<String, dynamic>>> Function() load;
  final Future<void> Function(int id) markRead;
  final Future<void> Function() markAllRead;

  @override
  State<NotificationPage> createState() => _NotificationPageState();
}

class _NotificationPageState extends State<NotificationPage> {
  List<Map<String, dynamic>> _rows = [];
  bool _busy = true;
  String? _error;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await widget.load();
      if (mounted) setState(() => _rows = rows);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Notifications'), actions: [
          TextButton(
              onPressed: _rows.any((e) => e['is_read'] != true)
                  ? () async {
                      await widget.markAllRead();
                      await _load();
                    }
                  : null,
              child: const Text('Read all'))
        ]),
        body: _busy
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!))
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                        itemCount: _rows.length,
                        itemBuilder: (_, i) {
                          final row = _rows[i];
                          return ListTile(
                              leading: Icon(
                                  row['is_read'] == true
                                      ? Icons.notifications_none
                                      : Icons.notifications_active,
                                  color: row['is_read'] == true
                                      ? null
                                      : Theme.of(context).colorScheme.primary),
                              title: Text(row['title']?.toString() ?? ''),
                              subtitle: Text(row['message']?.toString() ?? ''),
                              onTap: () async {
                                await widget.markRead(row['id'] as int);
                                DeepLinkService.dispatch(
                                    row['target_url']?.toString());
                                await _load();
                              });
                        })),
      );
}
