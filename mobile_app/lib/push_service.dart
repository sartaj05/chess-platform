import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class PushService {
  static const _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const _appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const _senderId = String.fromEnvironment('FIREBASE_SENDER_ID');

  static Future<void> configure(
      Future<void> Function(String token) register) async {
    if (_apiKey.isEmpty ||
        _appId.isEmpty ||
        _projectId.isEmpty ||
        _senderId.isEmpty) {
      return;
    }
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp(
            options: const FirebaseOptions(
                apiKey: _apiKey,
                appId: _appId,
                messagingSenderId: _senderId,
                projectId: _projectId));
      }
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(alert: true, badge: true, sound: true);
      final token = await messaging.getToken();
      if (token != null) await register(token);
      messaging.onTokenRefresh.listen(register);
    } catch (_) {
      // The app remains usable if Google Play services are unavailable.
    }
  }
}
