"""Immunization schedule URL routes."""

from django.urls import path

from .immunization_views import immunization_detail, patient_immunizations

urlpatterns = [
    path(
        "patients/<int:patient_id>/immunizations/",
        patient_immunizations,
        name="patient-immunizations",
    ),
    path(
        "immunizations/<int:record_id>/",
        immunization_detail,
        name="immunization-detail",
    ),
]
