"""
Tests for patient self-registration workflow.

Tests:
- Patient can register with PATIENT role
- Patient record is automatically created
- Patient account is unverified by default
- Patient cannot access portal until verified
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.patients.portal_views import get_patient_from_user
from rest_framework.exceptions import PermissionDenied

User = get_user_model()


@pytest.mark.django_db
class TestPatientSelfRegistration:
    """Test patient self-registration creates unverified account."""
    
    def test_patient_registration_creates_patient_record(self):
        """Test patient registration automatically creates Patient record."""
        client = APIClient()
        
        registration_data = {
            'username': 'newpatient',
            'email': 'newpatient@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'New',
            'last_name': 'Patient',
            'role': 'PATIENT'
        }
        
        response = client.post('/api/v1/auth/register/', registration_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify user was created
        user = User.objects.get(username='newpatient')
        assert user.role == 'PATIENT'
        assert user.email == 'newpatient@test.com'
        
        # Verify patient record was created
        patient = Patient.objects.get(user=user)
        assert patient.first_name == 'New'
        assert patient.last_name == 'Patient'
        assert patient.email == 'newpatient@test.com'
        assert patient.is_verified is False
        assert patient.user == user
    
    def test_patient_registration_unverified_by_default(self):
        """Test patient registration creates unverified account."""
        client = APIClient()
        
        registration_data = {
            'username': 'unverified',
            'email': 'unverified@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Unverified',
            'last_name': 'Patient',
            'role': 'PATIENT'
        }
        
        response = client.post('/api/v1/auth/register/', registration_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        user = User.objects.get(username='unverified')
        patient = Patient.objects.get(user=user)
        
        assert patient.is_verified is False
        assert patient.verified_by is None
        assert patient.verified_at is None
    
    def test_unverified_patient_cannot_access_portal(self):
        """Test unverified patient cannot access portal."""
        client = APIClient()
        
        # Register patient
        registration_data = {
            'username': 'blocked',
            'email': 'blocked@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Blocked',
            'last_name': 'Patient',
            'role': 'PATIENT'
        }
        
        response = client.post('/api/v1/auth/register/', registration_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        user = User.objects.get(username='blocked')
        patient = Patient.objects.get(user=user)
        
        # Try to access portal
        with pytest.raises(PermissionDenied) as exc_info:
            get_patient_from_user(user)
        
        assert 'not been verified' in str(exc_info.value).lower()
    
    def test_verified_patient_can_access_portal(self, receptionist_token):
        """Test verified patient can access portal."""
        client = APIClient()
        
        # Register patient
        registration_data = {
            'username': 'verified',
            'email': 'verified@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Verified',
            'last_name': 'Patient',
            'role': 'PATIENT'
        }
        
        response = client.post('/api/v1/auth/register/', registration_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        user = User.objects.get(username='verified')
        patient = Patient.objects.get(user=user)
        
        # Verify patient as receptionist
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        response = client.post(f'/api/v1/patients/{patient.id}/verify/')
        assert response.status_code == status.HTTP_200_OK
        
        # Now patient should be able to access portal
        patient.refresh_from_db()
        assert patient.is_verified is True
        
        portal_patient = get_patient_from_user(user)
        assert portal_patient.id == patient.id
        assert portal_patient.is_verified is True
