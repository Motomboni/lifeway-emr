from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("telemedicine", "0002_add_transcription_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="telemedicinesession",
            name="recording_consent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When recording consent was recorded",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="telemedicinesession",
            name="recording_consent_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who recorded consent (typically the doctor)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="telemedicine_recording_consents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
