"""
General security tests for EMR API.

Tests cover:
- Unauthenticated access enforcement
- Payment requirement enforcement
"""
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSecurity:
    """General security enforcement tests."""
    
    def test_unauthenticated_access(self, visit):
        """Test that unauthenticated access is denied."""
        client = APIClient()
        url = f"/api/v1/visits/{visit.id}/consultation/"
        response = client.get(url)
        # Unauthenticated requests should return 401, not 403
        assert response.status_code == 401

    def test_payment_required_for_consultation(self, doctor_token, unpaid_visit):
        """Test that payment is required before creating consultation."""
        from rest_framework import status
        import json
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {doctor_token}")
        url = f"/api/v1/visits/{unpaid_visit.id}/consultation/"
        response = client.post(url, {})
        # PermissionDenied raises 403, but 402 is also acceptable
        assert response.status_code in [status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN]
        # Check that payment-related error is present
        if hasattr(response, 'data'):
            error_text = str(response.data).lower()
        else:
            error_text = json.loads(response.content.decode()).get('detail', '').lower()
        assert 'payment' in error_text or 'cleared' in error_text
