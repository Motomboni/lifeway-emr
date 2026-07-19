"""
URL configuration for Drug catalog API.

Endpoint pattern: /api/v1/drugs/

Pharmacist-only for create/update/delete.
All authenticated users can view (for reference when creating prescriptions).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DrugViewSet
from .worklist_views import prescription_worklist

# Create router for drug viewset
router = DefaultRouter()
router.register(r"", DrugViewSet, basename="drug")

urlpatterns = [
    path("prescriptions/worklist/", prescription_worklist, name="prescription-worklist"),
    path("", include(router.urls)),
]
