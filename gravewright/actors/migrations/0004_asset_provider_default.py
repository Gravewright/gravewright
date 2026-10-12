from django.db import migrations, models

import gravewright.campaigns.systems


class Migration(migrations.Migration):
    dependencies = [('gravewright_actors', '0003_actor_type')]

    operations = [
        migrations.AlterField(
            model_name='asset', name='kind',
            field=models.CharField(default=gravewright.campaigns.systems.default_asset_kind, max_length=8),
        ),
    ]
