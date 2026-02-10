"""
URL configuration for Discharge Summaries (visit-scoped).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DischargeSummaryViewSet

router = DefaultRouter()
router.register(r'discharge-summaries', DischargeSummaryViewSet, basename='discharge-summary')

urlpatterns = router.urls
