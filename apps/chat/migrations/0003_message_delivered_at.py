from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0002_message_edit_and_removal")]
    operations = [
        migrations.AddField(
            model_name="message", name="delivered_at", field=models.DateTimeField(blank=True, db_index=True, null=True)
        )
    ]
