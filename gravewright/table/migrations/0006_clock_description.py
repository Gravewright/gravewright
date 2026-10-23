from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gravewright_table', '0005_mind_maps')]

    operations = [
        migrations.AddField(
            model_name='progressclock',
            name='description',
            field=models.TextField(blank=True, default='', max_length=4000),
        ),
    ]
