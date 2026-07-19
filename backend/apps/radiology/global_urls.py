"""Global radiology API routes (worklist, etc.)."""

from django.urls import path

from .worklist_views import radiology_worklist

urlpatterns = [
    path("requests/worklist/", radiology_worklist, name="radiology-worklist"),
]
