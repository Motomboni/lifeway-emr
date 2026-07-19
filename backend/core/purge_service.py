"""

Shared purge logic for management commands and superuser API endpoints.

"""

from django.db import transaction



from core.superuser_purge import superuser_purge_context





def _delete_all(model_path: str) -> int:

    try:

        module, name = model_path.rsplit(".", 1)

        model = __import__(module, fromlist=[name]).__dict__[name]

        return model.objects.all().delete()[0]

    except (ImportError, AttributeError, KeyError):

        return 0





def _purge_visit_dependencies() -> dict:

    """Delete records that block visit deletion (PROTECT FKs)."""

    stats = {}

    for label, model_path in [

        ("lab_orders_deleted", "apps.laboratory.models.LabOrder"),

        ("radiology_orders_deleted", "apps.radiology.models.RadiologyOrder"),

        ("medication_administrations_deleted", "apps.nursing.models.MedicationAdministration"),

        ("prescriptions_deleted", "apps.pharmacy.models.Prescription"),

        ("referrals_deleted", "apps.referrals.models.Referral"),

        ("procedure_tasks_deleted", "apps.clinical.procedure_models.ProcedureTask"),

        ("operation_notes_deleted", "apps.clinical.operation_models.OperationNote"),

        ("consultations_deleted", "apps.consultations.models.Consultation"),

        ("telemedicine_sessions_deleted", "apps.telemedicine.models.TelemedicineSession"),

        ("ai_requests_deleted", "apps.ai_integration.models.AIRequest"),

        ("invoice_receipts_deleted", "apps.billing.invoice_receipt_models.InvoiceReceipt"),

    ]:

        stats[label] = _delete_all(model_path)

    return stats





def _purge_ivf_records() -> dict:

    """Delete IVF records that PROTECT patient deletion."""

    stats = {}

    stats["ivf_cycles_deleted"] = _delete_all("apps.ivf.models.IVFCycle")

    stats["sperm_analyses_deleted"] = _delete_all("apps.ivf.models.SpermAnalysis")

    return stats





def purge_all_visits():

    from apps.visits.models import Visit



    stats = {}

    with superuser_purge_context():

        with transaction.atomic():

            stats.update(_purge_visit_dependencies())

            stats["visits_deleted"] = Visit.objects.all().delete()[0]

    return stats





def purge_all_patients_and_visits():

    """Delete all patients, visits, and related clinical/billing records."""

    from apps.patients.models import Patient

    from apps.visits.models import Visit



    stats = {}



    with superuser_purge_context():

        with transaction.atomic():

            stats["appointments_deleted"] = _delete_all(

                "apps.appointments.models.Appointment"

            )

            stats.update(_purge_visit_dependencies())

            stats["visits_deleted"] = Visit.objects.all().delete()[0]

            stats.update(_purge_ivf_records())

            stats["patients_deleted"] = Patient.objects.all().delete()[0]



    return stats


