# RadiologyRequest status: PENDING | COMPLETED only (Service Catalog flow)
# Migrate existing IN_PROGRESS and CANCELLED to PENDING

from django.db import migrations, models


def set_old_statuses_to_pending(apps, schema_editor):
    RadiologyRequest = apps.get_model('radiology', 'RadiologyRequest')
    RadiologyRequest.objects.filter(status__in=['IN_PROGRESS', 'CANCELLED']).update(status='PENDING')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('radiology', '0010_alter_imageuploaditem_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(set_old_statuses_to_pending, noop),
        migrations.AlterField(
            model_name='radiologyrequest',
            name='status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed')],
                default='PENDING',
                help_text='Status of the radiology request (PENDING until report is posted)',
                max_length=20,
            ),
        ),
    ]
