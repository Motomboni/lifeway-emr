"""
URL configuration for Lab Test Catalog (global endpoint).
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .catalog_views import LabTestCatalogViewSet
from .views import LabOrderWorklistView

router = DefaultRouter()
router.register(r'lab-tests', LabTestCatalogViewSet, basename='lab-test-catalog')

urlpatterns = [
    path('orders/worklist/', LabOrderWorklistView.as_view(), name='lab-order-worklist'),
] + router.urls
