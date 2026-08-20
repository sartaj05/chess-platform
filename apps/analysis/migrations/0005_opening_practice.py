import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analysis", "0004_alter_movereview_move"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="OpeningPractice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("interval_days", models.PositiveSmallIntegerField(default=1)),
                ("ease_factor", models.DecimalField(decimal_places=2, default=2.5, max_digits=3)),
                ("repetitions", models.PositiveSmallIntegerField(default=0)),
                ("due_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("last_quality", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("opening", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="practice_records", to="analysis.openingbookline")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="opening_practice", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["due_at"]},
        ),
        migrations.AddConstraint(model_name="openingpractice", constraint=models.UniqueConstraint(fields=("user", "opening"), name="opening_practice_user_line")),
    ]
