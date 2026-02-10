"""
URL configuration for Drug catalog API.

Endpoint pattern: /api/v1/drugs/

Pharmacist-only for create/update/delete.
All authenticated users can view (for reference when creating prescriptions).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DrugViewSet

# Create router for drug viewset
router = DefaultRouter()
router.register(
    r'',
    DrugViewSet,
    basename='drug'
)

urlpatterns = [
    path('', include(router.urls)),
]
