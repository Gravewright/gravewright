import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gravewright_maps", "0007_scenenavigation"),
    ]

    operations = [
        migrations.CreateModel(
            name="MapBuilderProject",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("document", models.JSONField(default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="gravewright_campaigns.campaign")),
                ("folder", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="gravewright_maps.folder")),
                ("scene", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="gravewright_maps.scene")),
            ],
            options={"ordering": ["-updated_at", "id"]},
        ),
    ]
