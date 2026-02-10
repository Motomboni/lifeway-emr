# Generated manually for transcription and billing support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telemedicine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='telemedicinesession',
            name='transcription_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Not requested'),
                    ('PENDING', 'Pending'),
                    ('PROCESSING', 'Processing'),
                    ('COMPLETED', 'Completed'),
                    ('FAILED', 'Failed'),
                ],
                default='',
                help_text='Status of automatic transcription',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='telemedicinesession',
            name='transcription_text',
            field=models.TextField(
                blank=True,
                help_text='Transcribed text from session recording (when available)',
            ),
        ),
        migrations.AddField(
            model_name='telemedicinesession',
            name='transcription_requested_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When transcription was requested',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='telemedicinesession',
            name='transcription_completed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When transcription finished',
                null=True,
            ),
        ),
    ]
