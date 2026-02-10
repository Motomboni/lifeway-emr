"""
Test Portal Access Toggle

Verify admin can enable/disable patient portal and it blocks login.

Usage:
    python test_portal_toggle.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.patients.views import PatientViewSet

User = get_user_model()

GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(text):
    print(f"{GREEN}[OK] {text}{RESET}")

def print_error(text):
    print(f"{RED}[ERROR] {text}{RESET}")

def print_header(text):
    print(f"\n{BLUE}{'='*70}\n{text}\n{'='*70}{RESET}\n")


def test_toggle_portal():
    """Test complete toggle flow."""
    print_header("PORTAL ACCESS TOGGLE TEST")
    
    # Cleanup
    User.objects.filter(username__startswith='toggle_test_').delete()
    Patient.objects.filter(first_name='ToggleTest').delete()
    
    # Setup
    admin = User.objects.create_user(
        username='toggle_test_admin',
        password='pass',
        role='ADMIN'
    )
    
    patient = Patient.objects.create(
        first_name='ToggleTest',
        last_name='Patient',
        patient_id='TOGGLE-001',
        portal_enabled=False
    )
    
    portal_user = User.objects.create_user(
        username='toggle_test_patient@example.com',
        password='pass',
        role='PATIENT',
        patient=patient
    )
    
    patient.portal_enabled = True
    portal_user.is_active = True
    patient.save()
    portal_user.save()
    
    print_success(f"Setup complete: Patient {patient.id}, User {portal_user.id}")
    print(f"  Initial: portal_enabled={patient.portal_enabled}, user.is_active={portal_user.is_active}")
    
    # Test 1: Disable portal
    print_header("TEST 1: Disable Portal")
    
    factory = APIRequestFactory()
    request = factory.post(f'/api/v1/patients/{patient.id}/toggle-portal/', {
        'enabled': False
    }, format='json')
    force_authenticate(request, user=admin)
    
    view = PatientViewSet.as_view({'post': 'toggle_portal'})
    response = view(request, pk=patient.id)
    
    assert response.status_code == 200
    assert response.data['success'] == True
    assert response.data['portal_enabled'] == False
    assert response.data['portal_user_active'] == False
    
    # Verify database
    patient.refresh_from_db()
    portal_user.refresh_from_db()
    
    assert patient.portal_enabled == False
    assert portal_user.is_active == False
    
    print_success("Portal disabled successfully")
    print(f"  patient.portal_enabled: {patient.portal_enabled}")
    print(f"  user.is_active: {portal_user.is_active}")
    print(f"  Patient CANNOT login")
    
    # Test 2: Enable portal
    print_header("TEST 2: Enable Portal")
    
    request = factory.post(f'/api/v1/patients/{patient.id}/toggle-portal/', {
        'enabled': True
    }, format='json')
    force_authenticate(request, user=admin)
    
    response = view(request, pk=patient.id)
    
    assert response.status_code == 200
    assert response.data['success'] == True
    assert response.data['portal_enabled'] == True
    assert response.data['portal_user_active'] == True
    
    # Verify database
    patient.refresh_from_db()
    portal_user.refresh_from_db()
    
    assert patient.portal_enabled == True
    assert portal_user.is_active == True
    
    print_success("Portal enabled successfully")
    print(f"  patient.portal_enabled: {patient.portal_enabled}")
    print(f"  user.is_active: {portal_user.is_active}")
    print(f"  Patient CAN login")
    
    # Test 3: Non-admin cannot toggle
    print_header("TEST 3: Non-Admin Cannot Toggle")
    
    receptionist = User.objects.create_user(
        username='toggle_test_receptionist',
        password='pass',
        role='RECEPTIONIST'
    )
    
    request = factory.post(f'/api/v1/patients/{patient.id}/toggle-portal/', {
        'enabled': False
    }, format='json')
    force_authenticate(request, user=receptionist)
    
    response = view(request, pk=patient.id)
    
    assert response.status_code == 403
    
    print_success("Non-admin correctly denied")
    print(f"  Receptionist access: DENIED")
    print(f"  Status: {response.status_code}")
    
    # Cleanup
    User.objects.filter(username__startswith='toggle_test_').delete()
    Patient.objects.filter(first_name='ToggleTest').delete()
    
    print_header("ALL TESTS PASSED")
    print_success("Portal toggle feature working correctly!")
    
    return True


if __name__ == '__main__':
    try:
        success = test_toggle_portal()
        sys.exit(0 if success else 1)
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
