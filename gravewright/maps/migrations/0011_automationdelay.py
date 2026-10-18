import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gravewright_maps", "0010_automationrun"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.CreateModel(
        name="AutomationDelay",
        fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("chain_id", models.UUIDField()),
            ("request_id", models.UUIDField()),
            ("role", models.CharField(max_length=8)),
            ("event", models.CharField(max_length=80)),
            ("node_id", models.CharField(max_length=64)),
            ("graph_hash", models.CharField(max_length=64)),
            ("seconds", models.FloatField()),
            ("due_at", models.DateTimeField()),
            ("status", models.CharField(default="pending", max_length=16)),
            ("data", models.JSONField(default=dict)),
            ("message", models.CharField(blank=True, max_length=240)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("finished_at", models.DateTimeField(blank=True, null=True)),
            ("element", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                         related_name="automation_delays", to="gravewright_maps.sceneobject")),
            ("scene", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                       related_name="automation_delays", to="gravewright_maps.scene")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                      related_name="+", to=settings.AUTH_USER_MODEL)),
        ],
        options={"ordering": ["due_at", "created_at", "id"], "indexes": [
            models.Index(fields=["status", "due_at"], name="map_delay_due"),
            models.Index(fields=["scene", "status"], name="map_delay_scene")]}),
    ]
