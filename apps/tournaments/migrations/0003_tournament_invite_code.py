import secrets
import string

from django.db import migrations, models


def populate_invite_codes(apps, schema_editor):
    Tournament = apps.get_model("tournaments", "Tournament")
    alphabet = string.ascii_uppercase + string.digits
    used = set()
    for tournament in Tournament.objects.all().iterator():
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if code not in used:
                used.add(code)
                break
        tournament.invite_code = code
        tournament.save(update_fields=["invite_code"])


class Migration(migrations.Migration):
    dependencies = [("tournaments", "0002_tournamentround_tournamentpairing_and_more")]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="invite_code",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=8, null=True),
        ),
        migrations.RunPython(populate_invite_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="tournament",
            name="invite_code",
            field=models.CharField(db_index=True, editable=False, max_length=8, unique=True),
        ),
    ]
