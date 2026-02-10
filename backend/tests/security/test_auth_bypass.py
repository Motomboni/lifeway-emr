import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestAuthBypass:
    def test_unauthenticated_access_denied(self, visit):
        client = APIClient()
        url = f"/api/v1/visits/{visit.id}/consultation/"
        response = client.get(url)
        assert response.status_code == 401

    def test_expired_token_denied(self, expired_token, visit):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        url = f"/api/v1/visits/{visit.id}/consultation/"
        response = client.get(url)
        assert response.status_code == 401