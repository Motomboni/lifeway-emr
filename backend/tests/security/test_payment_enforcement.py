import pytest
import json
from rest_framework.test import APIClient
from rest_framework import status


def get_response_data(response):
    """Helper to get response data from both DRF Response and JsonResponse."""
    if hasattr(response, 'data'):
        return response.data
    else:
        return json.loads(response.content.decode())


@pytest.mark.django_db
class TestPaymentEnforcement:
    def test_consultation_allowed_before_payment(self, doctor_token, unpaid_visit):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {doctor_token}")
        url = f"/api/v1/visits/{unpaid_visit.id}/consultation/"
        response = client.post(
            url,
            {
                "history": "Test history",
                "examination": "Test examination",
                "diagnosis": "Test diagnosis",
                "clinical_notes": "Test notes",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED