# Data migration: set restricted_service_flag for Registration and Consultation services

from django.db import migrations


def set_restricted_flags(apps, schema_editor):
    ServiceCatalog = apps.get_model('billing', 'ServiceCatalog')
    from django.db.models import Q
    # Registration: REG-* or name contains REGISTRATION
    ServiceCatalog.objects.filter(
        Q(service_code__istartswith='REG-') |
        Q(name__icontains='REGISTRATION')
    ).update(restricted_service_flag=True)
    # Consultation (GOPD_CONSULT, not registration)
    ServiceCatalog.objects.filter(
        department='CONSULTATION',
        workflow_type='GOPD_CONSULT',
    ).exclude(
        Q(service_code__istartswith='REG-') | Q(name__icontains='REGISTRATION')
    ).update(restricted_service_flag=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0018_add_restricted_service_flag'),
    ]

    operations = [
        migrations.RunPython(set_restricted_flags, noop),
    ]
