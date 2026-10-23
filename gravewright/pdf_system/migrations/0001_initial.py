import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("gravewright_campaigns", "0004_system_provider_default")]
    operations = [
        migrations.CreateModel(
            name="MappingTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("bundle", models.JSONField(default=dict)),
                ("revision", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="gravewright_campaigns.campaign")),
            ],
            options={"ordering": ["name", "id"]},
        ),
    ]
