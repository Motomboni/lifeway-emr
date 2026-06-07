import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestRoleEscalation:
    def test_receptionist_cannot_consult(self, receptionist_token, visit, api_client):
        client = api_client(token=receptionist_token)
        url = f"/api/v1/visits/{visit.id}/consultation/"
