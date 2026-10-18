from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gravewright_maps", "0008_mapbuilderproject")]

    operations = [
        migrations.AddField(
            model_name="mapbuilderproject", name="generation",
            field=models.JSONField(default=dict),
        ),
    ]
