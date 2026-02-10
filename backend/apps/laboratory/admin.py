"""
Admin configuration for Laboratory models.
"""
from django.contrib import admin
from .models import LabOrder, LabResult


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'ordered_by', 'status', 'created_at')
    search_fields = ('id', 'visit__id', 'visit__patient__patient_id', 'visit__patient__first_name', 'visit__patient__last_name')

