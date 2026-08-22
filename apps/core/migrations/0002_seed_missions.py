from django.db import migrations

MISSIONS = [
    ("Daily game", "Complete one chess game today.", "daily", "games", 1, 20),
    ("Daily tactics", "Solve three puzzles today.", "daily", "puzzles", 3, 30),
    ("Active player", "Play twenty moves today.", "daily", "moves", 20, 25),
    ("Weekly competitor", "Complete five games this week.", "weekly", "games", 5, 75),
    ("Winning week", "Win three games this week.", "weekly", "wins", 3, 100),
    ("Puzzle routine", "Solve fifteen puzzles this week.", "weekly", "puzzles", 15, 125),
]


def seed_missions(apps, schema_editor):
    Mission = apps.get_model("core", "Mission")
    for title, description, period, metric, target, reward in MISSIONS:
        Mission.objects.get_or_create(
            title=title,
            defaults={"description": description, "period": period, "metric": metric,
                      "target": target, "reward_points": reward, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed_missions, migrations.RunPython.noop)]
