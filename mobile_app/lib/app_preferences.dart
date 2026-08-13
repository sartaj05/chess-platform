import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AppPreferences {
  AppPreferences({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _themeKey = 'chess_theme_mode';
  static const _soundsKey = 'chess_sounds_enabled';
  static const _localeKey = 'chess_locale';

  Future<ThemeMode> loadTheme() async {
    final value = await _storage.read(key: _themeKey);
    return ThemeMode.values.firstWhere((mode) => mode.name == value,
        orElse: () => ThemeMode.system);
  }

  Future<bool> loadSounds() async =>
      (await _storage.read(key: _soundsKey)) != 'false';
  Future<void> saveTheme(ThemeMode mode) =>
      _storage.write(key: _themeKey, value: mode.name);
  Future<void> saveSounds(bool enabled) =>
      _storage.write(key: _soundsKey, value: enabled.toString());
  Future<Locale?> loadLocale() async {
    final value = await _storage.read(key: _localeKey);
    return value == null || value.isEmpty ? null : Locale(value);
  }

  Future<void> saveLocale(Locale? locale) => locale == null
      ? _storage.delete(key: _localeKey)
      : _storage.write(key: _localeKey, value: locale.languageCode);
}
