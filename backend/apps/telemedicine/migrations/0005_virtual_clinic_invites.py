# Generated manually for virtual clinic staff invites

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("telemedicine", "0004_add_video_provider"),
    ]

    operations = [
        migrations.AddField(
            model_name="telemedicineparticipant",
            name="clinic_role",
            field=models.CharField(
                choices=[
                    ("HOST", "Host doctor"),
                    ("PATIENT", "Patient"),
                    ("NURSE", "Nurse"),
                    ("SPECIALIST", "Specialist"),
                    ("OBSERVER", "Observer"),
                    ("STAFF", "Clinical staff"),
                ],
                default="STAFF",
                help_text="Role in the virtual clinic room",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="telemedicineparticipant",
            name="invite_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("ACCEPTED", "Accepted"),
                    ("DECLINED", "Declined"),
                    ("REVOKED", "Revoked"),
                ],
                default="ACCEPTED",
                help_text="Invite status for staff participants",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="telemedicineparticipant",
            name="invited_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Staff member who sent the invite",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="telemedicine_invites_sent",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="telemedicineparticipant",
            name="invited_at",
            field=models.DateTimeField(
                blank=True, help_text="When the invite was sent", null=True
            ),
        ),
        migrations.AddField(
            model_name="telemedicineparticipant",
            name="invite_message",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional note included with the invite",
                max_length=255,
            ),
        ),
        migrations.AddIndex(
            model_name="telemedicineparticipant",
            index=models.Index(
                fields=["invite_status"], name="telemedicin_invite__7a1b2c_idx"
            ),
        ),
    ]
