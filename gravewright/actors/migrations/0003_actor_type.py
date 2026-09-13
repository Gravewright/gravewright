from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gravewright_actors", "0002_asset_folder")]

    operations = [
        migrations.AddField(
            model_name="actor",
            name="type",
            field=models.CharField(default="character", max_length=80),
        ),
    ]
