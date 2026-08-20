import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0006_fairplayappeal"),
        ("tournaments", "0006_tournamentpairing_game_club_clubmembership_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TeamBoard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("round_number", models.PositiveSmallIntegerField(default=1)),
                ("board_number", models.PositiveSmallIntegerField()),
                ("away_club", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="away_team_boards", to="tournaments.club")),
                ("black_player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="team_black_boards", to=settings.AUTH_USER_MODEL)),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="boards", to="tournaments.teamcompetition")),
                ("game", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="team_board", to="games.game")),
                ("home_club", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="home_team_boards", to="tournaments.club")),
                ("white_player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="team_white_boards", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="teamboard",
            constraint=models.UniqueConstraint(fields=("competition", "round_number", "home_club", "away_club", "board_number"), name="team_unique_match_board"),
        ),
    ]
