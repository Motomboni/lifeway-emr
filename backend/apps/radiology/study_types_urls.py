"""
URL configuration for Radiology Study Types Catalog (global endpoint).
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .study_types_views import RadiologyStudyTypeViewSet
from .views import RadiologyRequestWorklistView

router = DefaultRouter()
router.register(r'study-types', RadiologyStudyTypeViewSet, basename='radiology-study-type')

urlpatterns = [
    path('requests/worklist/', RadiologyRequestWorklistView.as_view(), name='radiology-request-worklist'),
] + router.urls
