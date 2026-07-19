# Generated manually for LiveKit video provider support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("telemedicine", "0003_recording_consent"),
    ]

    operations = [
        migrations.AddField(
            model_name="telemedicinesession",
            name="video_provider",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Video backend used for this session (twilio | livekit)",
                max_length=20,
            ),
        ),
    ]
