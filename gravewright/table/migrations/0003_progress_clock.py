"""Add campaign and scene progress clocks without modifying existing documents."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gravewright_maps', '0001_initial'),
        ('gravewright_table', '0002_document_access'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgressClock',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('segments', models.PositiveSmallIntegerField(default=4)),
                ('value', models.PositiveSmallIntegerField(default=0)),
                ('color', models.CharField(default='#c9a44c', max_length=7)),
                ('visibility', models.CharField(choices=[('gm', 'GM'), ('players', 'Players')], default='gm', max_length=8)),
                ('players_can_edit', models.BooleanField(default=False)),
                ('pinned', models.BooleanField(default=False)),
                ('version', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gravewright_campaigns.campaign')),
                ('scene', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gravewright_maps.scene')),
            ],
            options={
                'ordering': ['created_at', 'id'],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(segments__gte=2, segments__lte=24), name='table_clock_segments'),
                    models.CheckConstraint(condition=models.Q(value__lte=models.F('segments')), name='table_clock_value'),
                    models.CheckConstraint(condition=models.Q(visibility__in=['gm', 'players']), name='table_clock_visibility'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ClockReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.UUIDField()),
                ('result', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gravewright_campaigns.campaign')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('campaign', 'user', 'request_id'),
                                                       name='table_unique_clock_command')],
            },
        ),
    ]
