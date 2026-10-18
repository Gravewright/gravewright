from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gravewright_maps", "0011_automationdelay")]

    operations = [
        migrations.AddField(model_name="automationdelay", name="kind",
                            field=models.CharField(default="delay", max_length=8)),
        migrations.AddField(model_name="automationdelay", name="name",
                            field=models.CharField(blank=True, max_length=64)),
        migrations.AddConstraint(model_name="automationdelay", constraint=models.UniqueConstraint(
            fields=("element", "name"), condition=models.Q(kind="timer", status="pending"),
            name="map_timer_pending_name")),
    ]
