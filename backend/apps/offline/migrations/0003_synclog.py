# Generated for EMR upgrade - offline-first mobile sync

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('offline', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(help_text='Device identifier (mobile app instance)', max_length=255)),
                ('last_sync_time', models.DateTimeField(help_text='Last successful sync timestamp')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(help_text='User who synced', on_delete=django.db.models.deletion.CASCADE, related_name='sync_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sync Log',
                'verbose_name_plural': 'Sync Logs',
                'db_table': 'sync_logs',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='synclog',
            index=models.Index(fields=['user', 'device_id'], name='sync_logs_user_device_idx'),
        ),
        migrations.AddIndex(
            model_name='synclog',
            index=models.Index(fields=['last_sync_time'], name='sync_logs_last_sync_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='synclog',
            unique_together={('user', 'device_id')},
        ),
    ]
