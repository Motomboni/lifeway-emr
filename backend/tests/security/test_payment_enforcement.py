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
    def test_consultation_requires_payment(self, doctor_token, unpaid_visit):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {doctor_token}")
        url = f"/api/v1/visits/{unpaid_visit.id}/consultation/"
        response = client.post(url, {})
        # PermissionDenied raises 403, but 402 is also acceptable
        assert response.status_code in [status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN]
        # Check that payment-related error is present
        response_data = get_response_data(response)
        error_text = str(response_data).lower()
        assert 'payment' in error_text or 'cleared' in error_text