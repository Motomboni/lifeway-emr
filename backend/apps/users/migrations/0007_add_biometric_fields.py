# Generated for EMR upgrade - biometric login support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_patient'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='biometric_enabled',
            field=models.BooleanField(default=False, help_text='Whether biometric login is enabled for this user'),
        ),
        migrations.AddField(
            model_name='user',
            name='biometric_key',
            field=models.CharField(blank=True, help_text='Public key or secure token reference for biometric validation (not raw biometric data)', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='device_id',
            field=models.CharField(blank=True, help_text='Device identifier for biometric / session tracking', max_length=255),
        ),
    ]
