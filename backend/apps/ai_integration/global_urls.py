"""
Global AI URLs (not visit-scoped).
POST /api/v1/ai/generate-note
POST /api/v1/ai/notes/
"""
from django.urls import path
from . import global_views

urlpatterns = [
    path('generate-note/', global_views.generate_note, name='ai-generate-note'),
    path('notes/', global_views.save_clinical_note, name='ai-notes-save'),
]
