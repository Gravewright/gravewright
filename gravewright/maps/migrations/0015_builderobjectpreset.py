import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("gravewright_maps", "0014_sceneassignment")]
    operations = [migrations.CreateModel(name="BuilderObjectPreset", fields=[
        ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
        ("name", models.CharField(max_length=120)),
        ("document", models.JSONField(default=dict)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("campaign", models.ForeignKey(to="gravewright_campaigns.campaign", on_delete=django.db.models.deletion.CASCADE, related_name="+")),
    ], options={"ordering": ["name", "id"]})]
