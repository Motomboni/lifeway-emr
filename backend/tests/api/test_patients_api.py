"""
Comprehensive API tests for Patient endpoints.
Tests CRUD operations, search, and permissions.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.patients.models import Patient


@pytest.mark.django_db
class TestPatientSearchAPI:
    """Test patient search functionality."""
    
    def test_search_patients_by_name(self, receptionist_token):
        """Test searching patients by name."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        
        # Create test patient
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            patient_id='PAT001'
        )
        
        response = client.get('/api/v1/patients/?search=John')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_search_patients_by_id(self, receptionist_token):
        """Test searching patients by patient ID."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        
        Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            patient_id='PAT002'
        )
        
        response = client.get('/api/v1/patients/?search=PAT002')
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPatientCreateAPI:
    """Test patient creation."""
    
    def test_create_patient_receptionist(self, receptionist_token):
        """Test receptionist can create patient."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        
        data = {
            'first_name': 'Test',
            'last_name': 'Patient',
            'date_of_birth': '1990-01-01',
            'gender': 'MALE',
            'phone': '1234567890'
        }
        
        response = client.post('/api/v1/patients/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['first_name'] == 'Test'
    
    def test_create_patient_duplicate_national_id(self, receptionist_token):
        """Test creating patient with duplicate national ID."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {receptionist_token}")
        
        # Create first patient
        Patient.objects.create(
            first_name='First',
            last_name='Patient',
            national_id='NID123'
        )
        
        # Try to create duplicate
        data = {
            'first_name': 'Second',
            'last_name': 'Patient',
            'national_id': 'NID123'
        }
        
        response = client.post('/api/v1/patients/', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
