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

    def test_consultation_allowed_before_payment(self, doctor_token, unpaid_visit):
        """Consultation can be created while visit payment is still pending."""
        from rest_framework import status

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
