# Generated manually to migrate old payment status values

from django.db import migrations


def migrate_payment_statuses_forward(apps, schema_editor):
    """
    Migrate old payment status values to new ones:
    - PENDING -> UNPAID
    - CLEARED -> PAID
    """
    Visit = apps.get_model('visits', 'Visit')
    
    # Update PENDING to UNPAID
    Visit.objects.filter(payment_status='PENDING').update(payment_status='UNPAID')
    
    # Update CLEARED to PAID
    Visit.objects.filter(payment_status='CLEARED').update(payment_status='PAID')


def migrate_payment_statuses_backward(apps, schema_editor):
    """
    Reverse migration (for rollback):
    - UNPAID -> PENDING
    - PAID -> CLEARED
    """
    Visit = apps.get_model('visits', 'Visit')
    
    # Update UNPAID to PENDING
    Visit.objects.filter(payment_status='UNPAID').update(payment_status='PENDING')
    
    # Update PAID to CLEARED
    Visit.objects.filter(payment_status='PAID').update(payment_status='CLEARED')


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0004_add_payment_type_and_insurance_claim'),
    ]

    operations = [
        migrations.RunPython(
            migrate_payment_statuses_forward,
            migrate_payment_statuses_backward
        ),
    ]

