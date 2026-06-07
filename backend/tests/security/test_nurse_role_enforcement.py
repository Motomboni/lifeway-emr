"""
Test Nurse Role Enforcement - Strict RBAC

Per EMR Rules:
- Nurse CAN: Vital Signs, Nursing Notes, View Visits/Appointments
- Nurse CANNOT: Create Consultations, Prescriptions, Lab/Radiology Orders, 
                Enter Results, Close Visits, Process Payments, Create Discharges/Referrals
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import json
from apps.visits.models import Visit
from apps.patients.models import Patient
from apps.consultations.models import Consultation

from tests.conftest import _ensure_user_org

User = get_user_model()


def get_response_data(response):
    """Helper to get response data from both DRF Response and JsonResponse."""
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode())


def _vital_signs_payload():
    return {
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "pulse": 72,
        "temperature": 37.0,
        "respiratory_rate": 16,
        "oxygen_saturation": 98,
        "height": 170,
        "weight": 70,
    }


@pytest.fixture
def nurse_user(db, test_org):
    """Create a nurse user for testing."""
    user = User.objects.create_user(
        username='nurse_test',
        email='nurse@test.com',
        password='testpass123',
        first_name='Nurse',
        last_name='Test',
        role='NURSE',
    )
    _ensure_user_org(user)
    return user


@pytest.fixture
def doctor_user(db, test_org):
    """Create a doctor user for testing."""
    user = User.objects.create_user(
        username='doctor_test',
        email='doctor@test.com',
        password='testpass123',
        first_name='Doctor',
        last_name='Test',
        role='DOCTOR',
    )
    _ensure_user_org(user)
    return user


@pytest.fixture
def receptionist_user(db, test_org):
    """Create a receptionist user for testing."""
    user = User.objects.create_user(
        username='receptionist_test',
        email='receptionist@test.com',
        password='testpass123',
        first_name='Receptionist',
        last_name='Test',
        role='RECEPTIONIST',
    )
    _ensure_user_org(user)
    return user


@pytest.fixture
def patient(db, test_org):
    """Create a test patient."""
    return Patient.objects.create(
        patient_id='PAT001',
        first_name='Test',
        last_name='Patient',
        date_of_birth='1990-01-01',
        gender='MALE',
        phone='1234567890',
        organization=test_org,
    )


@pytest.fixture
def open_visit(db, patient):
    """Create an open visit with paid status."""
    return Visit.objects.create(
        patient=patient,
        organization=patient.organization,
        status='OPEN',
        payment_status='PAID',
    )


class TestNurseProhibitedActions:
    """Test that Nurse is explicitly denied from prohibited actions."""
    
    def test_nurse_cannot_create_consultation(self, nurse_user, open_visit, api_client):
        """Nurse should be denied from creating consultations."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/consultation/'
        response = client.post(url, {
            'history': 'Test history',
            'examination': 'Test examination',
            'diagnosis': 'Test diagnosis',
            'clinical_notes': 'Test notes'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'nurse_prohibited' in str(response.data) or 'Nurses are not permitted' in str(response.data)
    
    def test_nurse_cannot_create_prescription(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from creating prescriptions."""
        # First create a consultation (doctor only)
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/prescriptions/'
        response = client.post(url, {
            'drug': 1,
            'dosage': '10mg',
            'frequency': 'Daily',
            'duration': '7 days'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'nurse_prohibited' in str(response.data) or 'Nurses are not permitted' in str(response.data)
    
    def test_nurse_cannot_create_lab_order(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from creating lab orders."""
        # First create a consultation (doctor only)
        consultation = Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/laboratory/'
        response = client.post(url, {
            'consultation': consultation.id,
            'tests_requested': ['CBC', 'Blood Sugar']
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'nurse_prohibited' in str(response.data) or 'Nurses are not permitted' in str(response.data)
    
    def test_nurse_cannot_create_radiology_order(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from creating radiology orders."""
        # First create a consultation (doctor only)
        consultation = Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/radiology/'
        response = client.post(url, {
            'consultation': consultation.id,
            'imaging_type': 'X-Ray',
            'body_part': 'Chest'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'nurse_prohibited' in str(response.data) or 'Nurses are not permitted' in str(response.data)
    
    def test_nurse_cannot_close_visit(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from closing visits."""
        # First create a consultation (doctor only)
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/close/'
        response = client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'nurse_prohibited' in str(response.data) or 'Nurses are not permitted' in str(response.data)
    
    def test_nurse_cannot_process_payment(self, nurse_user, open_visit, api_client):
        """Nurse should be denied from processing payments."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/payments/'
        response = client.post(url, {
            'amount': 1000,
            'payment_method': 'CASH'
        })
        
        # Should be denied (Receptionist only)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    def test_nurse_cannot_enter_lab_results(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from entering lab results."""
        # First create a consultation and lab order (doctor only)
        consultation = Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        from apps.laboratory.models import LabOrder
        lab_order = LabOrder.objects.create(
            visit=open_visit,
            consultation=consultation,
            ordered_by=doctor_user,
            tests_requested=['CBC', 'Blood Sugar'],
            status='SAMPLE_COLLECTED'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/laboratory/results/'
        response = client.post(url, {
            'lab_order': lab_order.id,
            'results': {
                'CBC': {'value': '5.0', 'unit': 'million/uL', 'normal_range': '4.5-5.5'},
                'Blood Sugar': {'value': '90', 'unit': 'mg/dL', 'normal_range': '70-100'}
            }
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Lab results can only be entered by LAB_TECH
        assert 'LAB_TECH' in str(response.data) or 'permission' in str(response.data).lower()
    
    def test_nurse_cannot_discharge_patient(self, nurse_user, open_visit, doctor_user, api_client):
        """Nurse should be denied from creating discharge summaries."""
        # First create a consultation (doctor only)
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/discharge-summaries/'
        response = client.post(url, {
            'summary': 'Patient discharged in stable condition',
            'discharge_instructions': 'Follow up in 2 weeks',
            'discharge_date': '2025-12-30'
        })
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestNurseVisitStatusEnforcement:
    """Test that Nurse cannot act on CLOSED or unpaid visits."""
    
    @pytest.fixture
    def closed_visit(self, db, patient, doctor_user):
        """Create a closed visit with paid status."""
        visit = Visit.objects.create(
            patient=patient,
            organization=patient.organization,
            status='OPEN',
            payment_status='PAID',
        )
        # Create consultation and close visit
        Consultation.objects.create(
            visit=visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        visit.status = 'CLOSED'
        visit.save()
        return visit
    
    @pytest.fixture
    def unpaid_visit(self, db, patient):
        """Create an open visit with unpaid status."""
        return Visit.objects.create(
            patient=patient,
            organization=patient.organization,
            status='OPEN',
            payment_status='UNPAID',
        )
    
    def test_nurse_cannot_act_on_closed_visit(self, nurse_user, closed_visit, api_client):
        """Nurse should be denied when trying to act on CLOSED visit."""
        client = api_client(user=nurse_user, organization=closed_visit.organization)
        
        url = f'/api/v1/visits/{closed_visit.id}/clinical/vital-signs/'
        response = client.post(url, _vital_signs_payload(), format='json')
        
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
        ]
    
    def test_nurse_cannot_act_on_unpaid_visit(self, nurse_user, unpaid_visit, api_client):
        """Nurse should be denied when trying to act on unpaid visit."""
        client = api_client(user=nurse_user, organization=unpaid_visit.organization)
        
        url = f'/api/v1/visits/{unpaid_visit.id}/clinical/vital-signs/'
        response = client.post(url, _vital_signs_payload(), format='json')
        
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ]
    
    def test_nurse_cannot_create_nursing_note_on_closed_visit(self, nurse_user, closed_visit, api_client):
        """Nurse should receive 409 Conflict when trying to create nursing note on CLOSED visit."""
        client = api_client(user=nurse_user, organization=closed_visit.organization)
        
        url = f'/api/v1/visits/{closed_visit.id}/nursing-notes/'
        response = client.post(url, {
            'note_type': 'General',
            'note_content': 'Test note',
            'patient_condition': 'Stable',
            'care_provided': 'Routine care',
            'patient_response': 'Good'
        })
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'CLOSED' in str(response.data) or 'closed' in str(response.data).lower()
    
    def test_nurse_cannot_create_nursing_note_on_unpaid_visit(self, nurse_user, unpaid_visit, api_client):
        """Nurse should be denied when trying to create nursing note on unpaid visit."""
        client = api_client(user=nurse_user, organization=unpaid_visit.organization)
        
        url = f'/api/v1/visits/{unpaid_visit.id}/nursing-notes/'
        response = client.post(url, {
            'note_type': 'General',
            'note_content': 'Test note',
            'patient_condition': 'Stable',
            'care_provided': 'Routine care',
            'patient_response': 'Good'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_data = get_response_data(response)
        assert 'payment' in str(response_data).lower() or 'cleared' in str(response_data).lower()


class TestNurseVisitAccessControl:
    """Test that Nurse cannot access visits they shouldn't have access to."""
    
    @pytest.fixture
    def other_patient(self, db, test_org):
        """Create another patient for access control testing."""
        return Patient.objects.create(
            patient_id='PAT002',
            first_name='Other',
            last_name='Patient',
            date_of_birth='1985-05-15',
            gender='FEMALE',
            phone='0987654321',
            organization=test_org,
        )
    
    @pytest.fixture
    def other_visit(self, db, other_patient):
        """Create another visit for access control testing."""
        return Visit.objects.create(
            patient=other_patient,
            organization=other_patient.organization,
            status='OPEN',
            payment_status='PAID',
        )
    
    def test_nurse_can_view_own_visit(self, nurse_user, open_visit, api_client):
        """Nurse should be able to view visits (read access is allowed)."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/'
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_nurse_can_view_other_visit(self, nurse_user, other_visit, api_client):
        """Nurse should be able to view other visits (read access is allowed for clinical staff)."""
        client = api_client(user=nurse_user, organization=other_visit.organization)
        
        url = f'/api/v1/visits/{other_visit.id}/'
        response = client.get(url)
        
        # Nurses can view visits (read-only access for clinical staff)
        assert response.status_code == status.HTTP_200_OK
    
    def test_nurse_can_act_on_accessible_visit(self, nurse_user, open_visit, api_client):
        """Nurse should be able to act on visits they have access to (OPEN and paid)."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/clinical/vital-signs/'
        response = client.post(url, _vital_signs_payload(), format='json')
        
        assert response.status_code == status.HTTP_201_CREATED


class TestNurseAllowedActions:
    """Test that Nurse can perform allowed actions."""
    
    def test_nurse_can_view_visits(self, nurse_user, open_visit, api_client):
        """Nurse should be able to view visits (read-only)."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/'
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_nurse_can_record_vital_signs(self, nurse_user, open_visit, api_client):
        """Nurse should be able to record vital signs."""
        client = api_client(user=nurse_user, organization=open_visit.organization)
        
        url = f'/api/v1/visits/{open_visit.id}/clinical/vital-signs/'
        response = client.post(url, _vital_signs_payload(), format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_nurse_can_view_appointments(self, nurse_user, test_org, api_client):
        """Nurse should be able to view appointments (read-only)."""
        client = api_client(user=nurse_user, organization=test_org)
        
        url = '/api/v1/appointments/'
        response = client.get(url)
        
        # Should allow read access
        assert response.status_code == status.HTTP_200_OK


