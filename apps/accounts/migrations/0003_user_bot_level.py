from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_user_managers")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="bot_level",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
