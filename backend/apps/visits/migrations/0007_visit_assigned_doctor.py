# Generated manually for assigned_doctor FK

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('visits', '0006_timelineevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='assigned_doctor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_visits',
                to=settings.AUTH_USER_MODEL,
                help_text='Registered doctor the patient is scheduled to see (set by reception at visit creation).',
            ),
        ),
    ]
