from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0001_initial")]
    operations = [
        migrations.AddField(model_name="message", name="deleted_for_sender", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="message", name="edited_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="message", name="unsent_at", field=models.DateTimeField(blank=True, null=True)),
    ]
