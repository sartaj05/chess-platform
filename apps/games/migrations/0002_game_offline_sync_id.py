import uuid

from django.db import migrations, models
from django.db.models import Q


def backfill_offline_sync_ids(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    seen: set[tuple[object, uuid.UUID]] = set()
    updates = []

    for game in Game.objects.filter(white_user__isnull=False).order_by("created_at").iterator():
        raw_sync_id = (game.metadata or {}).get("offline_sync_id")
        if not raw_sync_id:
            continue
        try:
            sync_id = uuid.UUID(str(raw_sync_id))
        except (TypeError, ValueError):
            continue
        owner_key = (game.white_user_id, sync_id)
        if owner_key in seen:
            continue
        seen.add(owner_key)
        game.offline_sync_id = sync_id
        updates.append(game)

    if updates:
        Game.objects.bulk_update(updates, ["offline_sync_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="offline_sync_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(backfill_offline_sync_ids, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="game",
            constraint=models.UniqueConstraint(
                condition=Q(offline_sync_id__isnull=False),
                fields=("white_user", "offline_sync_id"),
                name="games_user_offline_sync_unique",
            ),
        ),
    ]
