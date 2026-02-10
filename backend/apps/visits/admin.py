"""
Admin configuration for Visit model.
"""
from django.contrib import admin
from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'visit_type', 'status', 'created_at')
    search_fields = ('id', 'patient__patient_id', 'patient__first_name', 'patient__last_name')

