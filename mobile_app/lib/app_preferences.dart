import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AppPreferences {
  AppPreferences({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _themeKey = 'chess_theme_mode';
  static const _soundsKey = 'chess_sounds_enabled';
  static const _localeKey = 'chess_locale';
  static const _boardKey = 'chess_board_theme';
  static const _soundPackKey = 'chess_sound_pack';
  static const _onboardingKey = 'chess_onboarding_complete_v1';

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
  Future<String> loadBoardTheme() async =>
      await _storage.read(key: _boardKey) ?? 'forest';
  Future<String> loadSoundPack() async =>
      await _storage.read(key: _soundPackKey) ?? 'wood';
  Future<void> saveBoardTheme(String value) =>
      _storage.write(key: _boardKey, value: value);
  Future<void> saveSoundPack(String value) =>
      _storage.write(key: _soundPackKey, value: value);
  Future<bool> loadOnboardingComplete() async =>
      (await _storage.read(key: _onboardingKey)) == 'true';
  Future<void> saveOnboardingComplete() =>
      _storage.write(key: _onboardingKey, value: 'true');
  Future<Locale?> loadLocale() async {
    final value = await _storage.read(key: _localeKey);
    return value == null || value.isEmpty ? null : Locale(value);
  }

  Future<void> saveLocale(Locale? locale) => locale == null
      ? _storage.delete(key: _localeKey)
      : _storage.write(key: _localeKey, value: locale.languageCode);
}
