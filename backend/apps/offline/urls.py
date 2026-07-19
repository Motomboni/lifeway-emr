from django.urls import path

from .clinic_queue_views import clinic_offline_queue, clinic_offline_sync

urlpatterns = [
    path("queue/", clinic_offline_queue, name="clinic-offline-queue"),
    path("queue/<int:entry_id>/sync/", clinic_offline_sync, name="clinic-offline-sync"),
]
