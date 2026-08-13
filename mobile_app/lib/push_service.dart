import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

import 'deep_link_service.dart';

const _channel = AndroidNotificationChannel(
  'chess_games',
  'Chess games',
  description: 'Move alerts, active clocks, and game invitations.',
  importance: Importance.high,
);

final _localNotifications = FlutterLocalNotificationsPlugin();

FirebaseOptions? get _firebaseOptions {
  const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  const appId = String.fromEnvironment('FIREBASE_APP_ID');
  const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  const senderId = String.fromEnvironment('FIREBASE_SENDER_ID');
  if ([apiKey, appId, projectId, senderId].any((value) => value.isEmpty)) {
    return null;
  }
  return const FirebaseOptions(
    apiKey: apiKey,
    appId: appId,
    messagingSenderId: senderId,
    projectId: projectId,
  );
}

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  final options = _firebaseOptions;
  if (options != null && Firebase.apps.isEmpty) {
    await Firebase.initializeApp(options: options);
  }
}

class PushService {
  static bool _initialized = false;

  static Future<void> initializeNavigation() async {
    if (_initialized) return;
    _initialized = true;
    tz.initializeTimeZones();
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _localNotifications.initialize(
      const InitializationSettings(android: android),
      onDidReceiveNotificationResponse: (response) =>
          DeepLinkService.dispatch(response.payload),
    );
    await _localNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_channel);
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  }

  static Future<void> configure(
      Future<void> Function(String token) register) async {
    final options = _firebaseOptions;
    if (options == null) return;
    try {
      if (Firebase.apps.isEmpty) await Firebase.initializeApp(options: options);
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(alert: true, badge: true, sound: true);
      FirebaseMessaging.onMessage.listen(_showForeground);
      FirebaseMessaging.onMessageOpenedApp.listen(_openRemoteMessage);
      _openRemoteMessage(await messaging.getInitialMessage());
      final token = await messaging.getToken();
      if (token != null) await register(token);
      messaging.onTokenRefresh.listen(register);
    } catch (_) {
      // The app remains usable when Firebase or Play services are unavailable.
    }
  }

  static Future<void> _showForeground(RemoteMessage message) async {
    final notification = message.notification;
    await _localNotifications.show(
      message.messageId.hashCode,
      notification?.title ?? message.data['title'] ?? 'Chess Platform',
      notification?.body ?? message.data['body'] ?? 'You have a chess update.',
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'chess_games',
          'Chess games',
          channelDescription:
              'Move alerts, active clocks, and game invitations.',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      payload: message.data['target_url']?.toString(),
    );
  }

  static void _openRemoteMessage(RemoteMessage? message) {
    if (message != null) {
      DeepLinkService.dispatch(message.data['target_url']?.toString());
    }
  }

  static Future<void> scheduleTurnReminder({
    required String gameId,
    required Duration remaining,
  }) async {
    final delay = remaining > const Duration(minutes: 2)
        ? remaining - const Duration(minutes: 1)
        : const Duration(seconds: 5);
    await _localNotifications.zonedSchedule(
      gameId.hashCode,
      'Your chess clock is running',
      remaining > const Duration(minutes: 2)
          ? 'One minute remains. Make your move.'
          : 'It is your move. Return to the board.',
      tz.TZDateTime.now(tz.local).add(delay),
      const NotificationDetails(
        android: AndroidNotificationDetails('chess_games', 'Chess games',
            channelDescription:
                'Move alerts, active clocks, and game invitations.',
            importance: Importance.high,
            priority: Priority.high),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      payload: 'chessplatform://games/$gameId',
    );
  }

  static Future<void> cancelGameReminder(String gameId) =>
      _localNotifications.cancel(gameId.hashCode);
}
