"""
Pytest tests for Visit Closure API enforcement.

Tests EMR rule compliance:
- Unauthenticated access denied
- Non-doctor role denied
- Consultation required before closure
- Cannot close already closed visit
- Cannot modify CLOSED visit
- Audit log created on closure
- Immutability enforcement at DB and API level

Per EMR RULE LOCK: No mocking away security logic.
"""
import pytest
import json
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.audit import AuditLog

User = get_user_model()


def get_response_data(response):
    """Helper to get response data from both DRF Response and JsonResponse."""
    if hasattr(response, 'data'):
        return response.data
    else:
        return json.loads(response.content.decode())


@pytest.mark.django_db
class TestVisitClosureAuthentication:
    """Test A1: Unauthenticated access denied."""
    
    def test_unauthenticated_close_denied(self, open_visit_with_payment, consultation):
        """A1: Unauthenticated user cannot close visit."""
        client = APIClient()
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestVisitClosureRoleEnforcement:
    """Test R1: Role-based access control."""
    
    def test_receptionist_cannot_close(self, open_visit_with_payment, consultation, receptionist_token):
        """R1: Receptionist cannot close visit - only Doctor can."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {receptionist_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Check for role-related error (may be generic permission error)
        response_data = get_response_data(response)
        error_text = str(response_data).lower()
        assert 'doctor' in error_text or 'permission' in error_text or 'role' in error_text
    
    def test_lab_tech_cannot_close(self, open_visit_with_payment, consultation, lab_tech_token):
        """R1: Lab Tech cannot close visit."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {lab_tech_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_pharmacist_cannot_close(self, open_visit_with_payment, consultation, pharmacist_token):
        """R1: Pharmacist cannot close visit."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {pharmacist_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_doctor_can_close(self, open_visit_with_payment, consultation, doctor_user, doctor_token):
        """R1: Doctor can close visit."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('message') == 'Visit closed successfully.'
        
        # Verify visit was closed
        open_visit_with_payment.refresh_from_db()
        assert open_visit_with_payment.status == 'CLOSED'
        assert open_visit_with_payment.closed_by == doctor_user
        assert open_visit_with_payment.closed_at is not None


@pytest.mark.django_db
class TestVisitClosureConsultationEnforcement:
    """Test C1: Consultation required before closure."""
    
    def test_cannot_close_without_consultation(self, open_visit_with_payment, doctor_token):
        """C1: Cannot close visit without consultation."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'consultation' in str(response.data).lower()
    
    def test_can_close_with_consultation(self, open_visit_with_payment, consultation, doctor_token):
        """C1: Can close visit with consultation."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVisitClosureAlreadyClosed:
    """Test A2: Cannot close already closed visit."""
    
    def test_cannot_close_already_closed_visit(self, closed_visit_with_payment, consultation, doctor_token):
        """A2: Cannot close a visit that is already CLOSED."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{closed_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = get_response_data(response)
        error_text = str(response_data).lower()
        assert 'already closed' in error_text or 'already closed' in error_text


@pytest.mark.django_db
class TestVisitClosureImmutability:
    """Test I1: Immutability enforcement."""
    
    def test_cannot_update_closed_visit(self, closed_visit_with_payment, doctor_token):
        """I1: Cannot update CLOSED visit via API."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{closed_visit_with_payment.id}/"
        
        response = client.patch(url, {
            'payment_status': 'PENDING'
        })
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT]
        assert 'CLOSED' in str(response.data) or 'immutable' in str(response.data).lower()
    
    def test_cannot_partial_update_closed_visit(self, closed_visit_with_payment, doctor_token):
        """I1: Cannot partially update CLOSED visit via API."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{closed_visit_with_payment.id}/"
        
        response = client.patch(url, {
            'payment_status': 'PENDING'
        })
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT]
    
    def test_cannot_reopen_closed_visit_at_db_level(self, closed_visit_with_payment):
        """I1: Cannot change CLOSED visit to OPEN at DB level."""
        closed_visit_with_payment.status = 'OPEN'
        
        with pytest.raises(ValidationError) as exc_info:
            closed_visit_with_payment.save()
        
        assert 'immutable' in str(exc_info.value).lower() or 'reopen' in str(exc_info.value).lower()
    
    def test_cannot_create_new_consultation_for_closed_visit(self, closed_visit_with_payment, doctor_user):
        """I1: Cannot create new consultation for CLOSED visit."""
        from apps.consultations.models import Consultation
        
        with pytest.raises(ValidationError):
            Consultation.objects.create(
                visit=closed_visit_with_payment,
                created_by=doctor_user,
                history='Test',
                examination='Test',
                diagnosis='Test',
                clinical_notes='Test'
            )


@pytest.mark.django_db
class TestVisitClosureAuditLogging:
    """Test A3: Audit log created on closure."""
    
    def test_audit_log_created_on_close(self, open_visit_with_payment, consultation, doctor_user, doctor_token):
        """A3: Audit log created when visit is closed."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        # Count audit logs before
        initial_count = AuditLog.objects.filter(
            visit_id=open_visit_with_payment.id,
            resource_type='visit'
        ).count()
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify audit log was created
        audit_logs = AuditLog.objects.filter(
            visit_id=open_visit_with_payment.id,
            resource_type='visit',
            action='visit.close'
        )
        
        assert audit_logs.count() > initial_count
        
        # Verify audit log details
        latest_log = audit_logs.latest('timestamp')
        assert latest_log.action == 'visit.close'
        assert latest_log.user == doctor_user
        assert latest_log.user_role == 'DOCTOR'
        assert latest_log.visit_id == open_visit_with_payment.id
        assert latest_log.resource_id == open_visit_with_payment.id


@pytest.mark.django_db
class TestVisitClosureSuccessPath:
    """Test successful closure path."""
    
    def test_successful_closure(self, open_visit_with_payment, consultation, doctor_user, doctor_token):
        """Successful closure when all conditions are met."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{open_visit_with_payment.id}/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('message') == 'Visit closed successfully.'
        assert response.data.get('visit', {}).get('status') == 'CLOSED'
        
        # Verify visit was updated
        open_visit_with_payment.refresh_from_db()
        assert open_visit_with_payment.status == 'CLOSED'
        assert open_visit_with_payment.closed_by == doctor_user
        assert open_visit_with_payment.closed_at is not None


@pytest.mark.django_db
class TestVisitClosureFailureScenarios:
    """Test failure scenarios."""
    
    def test_close_nonexistent_visit(self, doctor_token):
        """Failure: Cannot close nonexistent visit."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = "/api/v1/visits/99999/close/"
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_close_visit_without_consultation_db_level(self, open_visit_with_payment, doctor_user):
        """Failure: Cannot close visit without consultation at DB level."""
        open_visit_with_payment.status = 'CLOSED'
        open_visit_with_payment.closed_by = doctor_user
        
        with pytest.raises(ValidationError) as exc_info:
            open_visit_with_payment.save()
        
        assert 'consultation' in str(exc_info.value).lower()
    
    def test_cannot_create_new_orders_for_closed_visit(self, closed_visit_with_payment, consultation, doctor_user, doctor_token):
        """Failure: Cannot create new orders for CLOSED visit."""
        from apps.laboratory.models import LabOrder
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{closed_visit_with_payment.id}/laboratory/"
        
        response = client.post(url, {
            'test_name': 'Blood Test',
            'test_code': 'BT001',
            'instructions': 'Fasting required'
        })
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT]
        # Check that closed visit error is present (may be in detail or error message)
        response_data = get_response_data(response)
        error_text = str(response_data).lower()
        assert 'closed' in error_text
    
    def test_cannot_create_new_prescription_for_closed_visit(self, closed_visit_with_payment, consultation, doctor_user, doctor_token):
        """Failure: Cannot create new prescription for CLOSED visit."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        url = f"/api/v1/visits/{closed_visit_with_payment.id}/prescriptions/"
        
        response = client.post(url, {
            'drug': 'Amoxicillin',
            'dosage': '500mg'
        })
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT]
        # Check that closed visit error is present (may be in detail or error message)
        response_data = get_response_data(response)
        error_text = str(response_data).lower()
        assert 'closed' in error_text
