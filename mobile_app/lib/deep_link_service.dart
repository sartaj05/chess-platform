import 'dart:async';

import 'package:flutter/services.dart';

enum MobileDestination { room, profile, game, tournament, notifications }

class MobileLink {
  const MobileLink(this.destination, [this.id]);

  final MobileDestination destination;
  final String? id;

  static MobileLink? parse(String? raw) {
    if (raw == null || raw.trim().isEmpty) return null;
    final uri = Uri.tryParse(raw.trim());
    if (uri == null) return null;
    final segments = uri.pathSegments.where((part) => part.isNotEmpty).toList();
    if (uri.scheme == 'chessplatform' && uri.host.isNotEmpty) {
      segments.insert(0, uri.host);
    }
    if (segments.isEmpty) return null;
    if (segments.first == 'notifications') {
      return const MobileLink(MobileDestination.notifications);
    }
    if ({'rooms', 'room', 'invite'}.contains(segments.first) &&
        segments.length > 1) {
      return MobileLink(MobileDestination.room, segments[1].toUpperCase());
    }
    if ({'games', 'game'}.contains(segments.first) && segments.length > 1) {
      return MobileLink(MobileDestination.game, segments[1]);
    }
    if ({'profiles', 'profile', 'players'}.contains(segments.first) &&
        segments.length > 1) {
      return MobileLink(MobileDestination.profile, segments[1]);
    }
    if ({'tournaments', 'tournament'}.contains(segments.first) &&
        segments.length > 1) {
      return MobileLink(MobileDestination.tournament, segments[1]);
    }
    return null;
  }
}

class DeepLinkService {
  DeepLinkService._();

  static const _channel = MethodChannel('chess_platform/deep_links');
  static final StreamController<MobileLink> _links =
      StreamController<MobileLink>.broadcast();
  static Stream<MobileLink> get links => _links.stream;

  static Future<void> initialize() async {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'link') dispatch(call.arguments as String?);
    });
    try {
      dispatch(await _channel.invokeMethod<String>('getInitialLink'));
    } on PlatformException {
      // Deep links remain optional on unsupported platforms.
    }
  }

  static void dispatch(String? raw) {
    final link = MobileLink.parse(raw);
    if (link != null) _links.add(link);
  }
}
