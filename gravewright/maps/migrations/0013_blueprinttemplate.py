import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("gravewright_maps", "0012_automationdelay_timer")]

    operations = [
        migrations.AddField(
            model_name="mapasset", name="generated_for",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name="generated_builder_assets", to="gravewright_maps.scene"),
        ),
        migrations.CreateModel(
            name="BlueprintTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("definition", models.JSONField(default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="+", to="gravewright_campaigns.campaign")),
            ],
            options={"ordering": ["name", "id"]},
        ),
    ]
