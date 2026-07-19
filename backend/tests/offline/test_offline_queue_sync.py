"""Tests for offline clinic queue sync execution."""

import pytest
from rest_framework import status

from apps.offline.clinic_queue_models import ClinicOfflineQueueEntry
from apps.offline.clinic_queue_sync_service import execute_offline_queue_entry
from apps.patients.models import Patient


@pytest.mark.django_db
class TestOfflineQueueSyncService:
    def test_register_patient_sync_creates_patient(self, receptionist_user, test_org):
        entry = ClinicOfflineQueueEntry.objects.create(
            organization=test_org,
            device_id="test-device",
            action="REGISTER_PATIENT",
            payload={
                "first_name": "Offline",
                "last_name": "Patient",
                "phone": "08012345678",
            },
            created_by=receptionist_user,
        )
        result = execute_offline_queue_entry(
            entry, user=receptionist_user, organization=test_org
        )
        assert result["patient_id"]
        assert Patient.objects.filter(first_name="Offline", last_name="Patient").exists()
        entry.refresh_from_db()
        assert entry.status == "SYNCED"

    def test_sync_api_executes_entry(self, api_client, receptionist_user, test_org):
        entry = ClinicOfflineQueueEntry.objects.create(
            organization=test_org,
            device_id="test-device",
            action="REGISTER_PATIENT",
            payload={"first_name": "Queued", "last_name": "User"},
            created_by=receptionist_user,
        )
        client = api_client(user=receptionist_user)
        response = client.post(f"/api/v1/offline/queue/{entry.id}/sync/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "SYNCED"
        assert Patient.objects.filter(first_name="Queued").exists()

    def test_sync_rejects_wrong_org(self, api_client, receptionist_user, test_org):
        entry = ClinicOfflineQueueEntry.objects.create(
            organization=None,
            device_id="other",
            action="REGISTER_PATIENT",
            payload={"first_name": "X", "last_name": "Y"},
            created_by=receptionist_user,
        )
        client = api_client(user=receptionist_user)
        response = client.post(f"/api/v1/offline/queue/{entry.id}/sync/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
