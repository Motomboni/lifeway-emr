import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestRoleEscalation:
    def test_receptionist_cannot_consult(self, receptionist_token, visit):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        url = f"/api/v1/visits/{visit.id}/consultation/"
     