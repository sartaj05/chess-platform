import 'package:chess_platform_mobile/onboarding_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('onboarding teaches four chess actions before completion',
      (tester) async {
    var completed = false;
    await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onComplete: () async => completed = true)));

    expect(find.text('Your first move'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('lesson-square-e2')));
    await tester.tap(find.byKey(const ValueKey('lesson-square-e4')));
    await tester.pump();

    expect(find.text('Castle safely'), findsOneWidget);
    expect(completed, isFalse);
  });

  testWidgets('tutorial can be skipped', (tester) async {
    var completed = false;
    await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onComplete: () async => completed = true)));

    await tester.tap(find.text('Skip tutorial'));
    await tester.pump();

    expect(completed, isTrue);
  });
}
