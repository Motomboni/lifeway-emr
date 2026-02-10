"""
Admin configuration for Consultation model.
"""
from django.contrib import admin
from .models import Consultation


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'created_by', 'created_at')
    search_fields = ('visit__id', 'visit__patient__patient_id', 'visit__patient__first_name', 'visit__patient__last_name')

