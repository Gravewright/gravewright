from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gravewright_tokens", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="token", name="appearance", field=models.JSONField(default=dict)
        ),
    ]
