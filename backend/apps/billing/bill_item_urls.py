"""
URL configuration for bill item endpoints.
"""
from django.urls import path
from .bill_item_views import AddBillItemView, ListServicesView, GetServicePriceView
from .billing_dashboard_views import VisitBillingSummaryView
from .service_import_views import ImportServicesView

urlpatterns = [
    path('add-item/', AddBillItemView.as_view(), name='add-bill-item'),
    path('services/', ListServicesView.as_view(), name='list-services'),
    # Service catalog is now in service_catalog_urls.py
    path('services/import/', ImportServicesView.as_view(), name='import-services'),
    path('service-price/', GetServicePriceView.as_view(), name='get-service-price'),
    path('visit/<int:visit_id>/summary/', VisitBillingSummaryView.as_view(), name='visit-billing-summary'),
]

