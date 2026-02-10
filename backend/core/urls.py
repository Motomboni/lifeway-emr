"""
Main URL configuration for EMR API.

All APIs are versioned under /api/v1/
Visit-scoped endpoints are nested under /api/v1/visits/{visit_id}/
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    # Health check endpoints (public, no auth required)
    path('', include('core.health_urls')),
    # API Documentation (Swagger/OpenAPI)
    path('', include('core.api_docs_urls')),
    # Mobile API (patient portal - lightweight, offline-friendly)
    path('api/mobile/', include('apps.auth_otp.mobile_urls')),
    # API v1
    path('api/v1/', include([
        # Authentication endpoints (non-visit-scoped)
        path('auth/', include('apps.users.urls')),
        # Patient management (non-visit-scoped)
        path('patients/', include('apps.patients.urls')),
        # National Health ID verification (Nigeria-ready)
        path('nhid/', include('apps.patients.nhid_urls')),
        # Patient Portal (read-only access for patients)
        path('patient-portal/', include('apps.patients.portal_urls')),
        # Drug catalog management (Pharmacist only)
        path('drugs/', include('apps.pharmacy.drug_urls')),
        # E-Prescription + drug interaction check (Doctor only)
        path('eprescription/', include('apps.pharmacy.eprescription_urls')),
        # Inventory management (Pharmacist only)
        path('inventory/', include('apps.pharmacy.inventory_urls')),
        # Appointment scheduling
        path('appointments/', include('apps.appointments.urls')),
        # Visit-scoped endpoints (all clinical actions)
        path('visits/', include('apps.visits.urls')),
        # Audit logs (read-only, compliance)
        path('audit-logs/', include('core.audit_urls')),
        # Reports and analytics
        path('reports/', include('apps.reports.urls')),
        # Backup and restore (Superuser only)
        path('backups/', include('apps.backup.urls')),
        # Notifications
        path('notifications/', include('apps.notifications.urls')),
        # AI (global: note generation; visit-scoped AI under visits)
        path('ai/', include('apps.ai_integration.global_urls')),
        # Telemedicine
        path('telemedicine/', include('apps.telemedicine.urls')),
        # Clinical features (global - templates)
        path('clinical/', include('apps.clinical.urls')),
        # Lab Test Catalog (global - not visit-scoped)
        path('laboratory/', include('apps.laboratory.catalog_urls')),
        # Lab Test Templates (global - not visit-scoped)
        path('lab-templates/', include('apps.laboratory.template_urls')),
        # Admission management (Wards, Beds, Inpatients list)
        path('admissions/', include('apps.discharges.admission_urls')),
        # Radiology Test Templates (global - not visit-scoped)
        path('radiology-templates/', include('apps.radiology.template_urls')),
        # Radiology Study Types Catalog (global - not visit-scoped)
        path('radiology/', include('apps.radiology.study_types_urls')),
        # Radiology Offline Image Sync (metadata-first upload) - separate from study types
        path('radiology/', include('apps.radiology.offline_image_urls')),
        # Radiology Upload Sessions (offline-first imaging upload) - global endpoint for status page
        path('radiology/', include('apps.radiology.upload_session_urls')),
        # Wallet management
        path('wallet/', include('apps.wallet.urls')),
        # HMO Provider management (Receptionist only)
        path('billing/hmo-providers/', include('apps.billing.hmo_provider_urls')),
        # Insurance Provider management (for patient registration)
        path('billing/insurance-providers/', include('apps.billing.insurance_provider_urls')),
        # Paystack webhook (public endpoint, signature-verified)
        path('billing/paystack/webhook/', include('apps.billing.paystack_webhook_urls')),
        # Insurance claim management (Receptionist only)
        path('billing/insurance/', include('apps.billing.insurance_claim_urls')),
        # Insurance policies and claims automation
        path('billing/claims/', include('apps.billing.claims_urls')),
        # Bill item management (Receptionist only)
        path('billing/', include('apps.billing.bill_item_urls')),
        # Central billing queue (Receptionist only)
        path('billing/', include('apps.billing.billing_queue_urls')),
        # Service Catalog API
        path('billing/', include('apps.billing.service_catalog_urls')),
        # Revenue Leak Detection (Admin only)
        path('billing/', include('apps.billing.leak_detection_urls')),
        # End-of-Day Reconciliation (Admin/Receptionist)
        path('billing/', include('apps.billing.reconciliation_urls')),
        # Simplified Paystack payment endpoints
        path('payments/', include('apps.billing.paystack_payment_urls')),
        # Explainable Lock System
        path('locks/', include('apps.core.lock_urls')),
        # IVF Treatment Module (specialized, role-restricted)
        path('ivf/', include('apps.ivf.urls')),
        # Antenatal Clinic Management
        path('antenatal/', include('apps.antenatal.urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
