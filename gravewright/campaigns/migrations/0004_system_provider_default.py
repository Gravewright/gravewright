from django.db import migrations, models

import gravewright.campaigns.systems


class Migration(migrations.Migration):
    dependencies = [('gravewright_campaigns', '0003_onboarding_streamerlink_and_more')]

    operations = [
        migrations.AlterField(
            model_name='campaign', name='system',
            field=models.CharField(blank=True, default=gravewright.campaigns.systems.default_system_id, max_length=120),
        ),
    ]
