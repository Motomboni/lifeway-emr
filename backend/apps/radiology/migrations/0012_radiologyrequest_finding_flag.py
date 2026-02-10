# Generated migration: add finding_flag to RadiologyRequest

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radiology', '0011_radiologyrequest_status_pending_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='radiologyrequest',
            name='finding_flag',
            field=models.CharField(
                blank=True,
                choices=[
                    ('NORMAL', 'Normal'),
                    ('ABNORMAL', 'Abnormal'),
                    ('CRITICAL', 'Critical Finding'),
                ],
                help_text='Finding flag set by Radiology Tech when posting report',
                max_length=20,
                null=True
            ),
        ),
    ]
