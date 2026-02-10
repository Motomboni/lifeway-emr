# Generated for EMR upgrade - WhatsApp appointment reminders

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0001_initial'),
        ('notifications', '0002_add_patient_verified_notification_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentReminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('channel', models.CharField(choices=[('whatsapp', 'WhatsApp'), ('sms', 'SMS'), ('email', 'Email')], default='whatsapp', max_length=20)),
                ('hours_before', models.IntegerField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('appointment', models.ForeignKey(help_text='Appointment this reminder is for', on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to='appointments.appointment')),
            ],
            options={
                'verbose_name': 'Appointment Reminder',
                'verbose_name_plural': 'Appointment Reminders',
                'db_table': 'appointment_reminders',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='appointmentreminder',
            index=models.Index(fields=['appointment'], name='appt_reminder_appt_idx'),
        ),
        migrations.AddIndex(
            model_name='appointmentreminder',
            index=models.Index(fields=['status'], name='appt_reminder_status_idx'),
        ),
        migrations.AddIndex(
            model_name='appointmentreminder',
            index=models.Index(fields=['channel'], name='appt_reminder_chan_idx'),
        ),
    ]
