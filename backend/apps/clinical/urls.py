"""
Global Clinical URLs.
Used in core/urls.py for templates
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClinicalTemplateViewSet

router = DefaultRouter()
router.register(r"templates", ClinicalTemplateViewSet, basename="clinical-templates")

urlpatterns = [
    path("", include(router.urls)),
    path("", include("apps.clinical.immunization_urls")),
]
