"""
Admin configuration for Patient model.
"""
from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'first_name', 'last_name', 'phone')
    search_fields = ('first_name', 'last_name', 'phone')
