"""
URL configuration for End-of-Day Reconciliation.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .reconciliation_views import EndOfDayReconciliationViewSet

router = DefaultRouter()
router.register(
    r'reconciliation',
    EndOfDayReconciliationViewSet,
    basename='reconciliation'
)

urlpatterns = router.urls

