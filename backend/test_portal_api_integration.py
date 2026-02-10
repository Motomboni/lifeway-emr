"""
Patient Portal API Integration Test

Test the complete flow: View → Serializer → Database

Usage:
    python test_portal_api_integration.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.patients.views import PatientViewSet

User = get_user_model()

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(text):
    print(f"{GREEN}[OK] {text}{RESET}")

def print_error(text):
    print(f"{RED}[ERROR] {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}[INFO] {text}{RESET}")

def print_header(text):
    print(f"\n{BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{RESET}\n")


def cleanup():
    """Clean up test data."""
    from core.audit import AuditLog
    print_info("Cleaning up test data...")
    
    # Delete audit logs for test users first (they protect the users from deletion)
    test_users = User.objects.filter(username__startswith='api_test_')
    AuditLog.objects.filter(user__in=test_users).delete()
    
    # Delete patients first (may cascade to portal users)
    Patient.objects.filter(first_name='APITest').delete()
    
    # Now delete test users
    User.objects.filter(username__startswith='api_test_').delete()
    
    print_success("Cleanup complete")


def test_api_without_portal():
    """Test API creates patient without portal."""
    print_header("TEST 1: Create Patient Without Portal (API)")
    
    try:
        # Setup
        receptionist = User.objects.create_user(
            username='api_test_receptionist1',
            password='testpass',
            role='RECEPTIONIST'
        )
        
        # Create API request
        factory = APIRequestFactory()
        request = factory.post('/api/v1/patients/', {
            'first_name': 'APITest',
            'last_name': 'NoPortal',
            'date_of_birth': '1990-01-01',
            'gender': 'MALE',
        }, format='json')
        
        # Authenticate request
        force_authenticate(request, user=receptionist)
        
        # Call view
        view = PatientViewSet.as_view({'post': 'create'})
        response = view(request)
        
        # Verify response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        assert response.data['success'] == True
        assert response.data['portal_created'] == False
        assert 'portal_credentials' not in response.data
        
        print_success("API call successful")
        print(f"  Status: {response.status_code}")
        print(f"  Message: {response.data['message']}")
        print(f"  Patient ID: {response.data['patient']['id']}")
        print(f"  Portal Created: {response.data['portal_created']}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_with_portal():
    """Test API creates patient with portal account."""
    print_header("TEST 2: Create Patient With Portal Account (API)")
    
    try:
        # Setup
        receptionist = User.objects.create_user(
            username='api_test_receptionist2',
            password='testpass',
            role='RECEPTIONIST'
        )
        
        # Create API request
        factory = APIRequestFactory()
        request = factory.post('/api/v1/patients/', {
            'first_name': 'APITest',
            'last_name': 'WithPortal',
            'date_of_birth': '1985-05-15',
            'gender': 'FEMALE',
            'create_portal_account': True,
            'portal_email': 'api_test_portal@example.com',
            'portal_phone': '0712345678',
        }, format='json')
        
        # Authenticate request
        force_authenticate(request, user=receptionist)
        
        # Call view
        view = PatientViewSet.as_view({'post': 'create'})
        response = view(request)
        
        # Verify response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        assert response.data['success'] == True
        assert response.data['portal_created'] == True
        assert 'portal_credentials' in response.data
        assert 'temporary_password' in response.data['portal_credentials']
        assert len(response.data['portal_credentials']['temporary_password']) == 12
        
        print_success("API call successful")
        print(f"  Status: {response.status_code}")
        print(f"  Message: {response.data['message']}")
        print(f"  Patient ID: {response.data['patient']['id']}")
        print(f"  Portal Created: {response.data['portal_created']}")
        print(f"  Username: {response.data['portal_credentials']['username']}")
        print(f"  Password Length: {len(response.data['portal_credentials']['temporary_password'])}")
        
        # Verify database
        patient = Patient.objects.get(id=response.data['patient']['id'])
        assert patient.portal_enabled == True
        assert hasattr(patient, 'portal_user')
        assert patient.portal_user.username == 'api_test_portal@example.com'
        assert patient.portal_user.role == 'PATIENT'
        
        print_success("Database verification passed")
        print(f"  User ID: {patient.portal_user.id}")
        print(f"  User Role: {patient.portal_user.role}")
        print(f"  Patient Link: {patient.portal_user.patient.patient_id}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_duplicate_email_error():
    """Test API handles duplicate email gracefully."""
    print_header("TEST 3: Duplicate Email Error Handling (API)")
    
    try:
        # Setup - create existing user
        existing_user = User.objects.create_user(
            username='api_test_existing@example.com',
            password='testpass',
            role='DOCTOR'
        )
        print_info(f"Created existing user: {existing_user.username}")
        
        receptionist = User.objects.create_user(
            username='api_test_receptionist3',
            password='testpass',
            role='RECEPTIONIST'
        )
        
        # Try to create patient with duplicate email
        factory = APIRequestFactory()
        request = factory.post('/api/v1/patients/', {
            'first_name': 'APITest',
            'last_name': 'DuplicateEmail',
            'create_portal_account': True,
            'portal_email': 'api_test_existing@example.com',  # Duplicate
        }, format='json')
        
        force_authenticate(request, user=receptionist)
        
        # Call view
        view = PatientViewSet.as_view({'post': 'create'})
        response = view(request)
        
        # Verify error response
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert response.data['success'] == False
        # Check in either 'error' or 'detail' field
        error_text = (response.data.get('error', '') + response.data.get('detail', '')).lower()
        assert 'already exists' in error_text or 'exist' in error_text
        
        print_success("API correctly rejected duplicate email")
        print(f"  Status: {response.status_code}")
        print(f"  Error: {response.data['error']}")
        print(f"  Detail: {response.data['detail']}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_missing_email_error():
    """Test API validates missing email."""
    print_header("TEST 4: Missing Email Validation (API)")
    
    try:
        receptionist = User.objects.create_user(
            username='api_test_receptionist4',
            password='testpass',
            role='RECEPTIONIST'
        )
        
        # Try to create portal without email
        factory = APIRequestFactory()
        request = factory.post('/api/v1/patients/', {
            'first_name': 'APITest',
            'last_name': 'NoEmail',
            'create_portal_account': True,
            # Missing portal_email
        }, format='json')
        
        force_authenticate(request, user=receptionist)
        
        view = PatientViewSet.as_view({'post': 'create'})
        response = view(request)
        
        # Verify error response
        assert response.status_code == 400
        assert response.data['success'] == False
        assert 'email' in response.data['detail'].lower()
        assert 'required' in response.data['detail'].lower()
        
        print_success("API correctly validates missing email")
        print(f"  Status: {response.status_code}")
        print(f"  Error: {response.data['error']}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_response_format():
    """Test response format is consistent."""
    print_header("TEST 5: Response Format Consistency")
    
    try:
        receptionist = User.objects.create_user(
            username='api_test_receptionist5',
            password='testpass',
            role='RECEPTIONIST'
        )
        
        factory = APIRequestFactory()
        request = factory.post('/api/v1/patients/', {
            'first_name': 'APITest',
            'last_name': 'ResponseTest',
            'create_portal_account': True,
            'portal_email': 'api_test_response@example.com',
        }, format='json')
        
        force_authenticate(request, user=receptionist)
        
        view = PatientViewSet.as_view({'post': 'create'})
        response = view(request)
        
        # Verify response structure
        assert 'success' in response.data
        assert 'message' in response.data
        assert 'patient' in response.data
        assert 'portal_created' in response.data
        
        if response.data['portal_created']:
            assert 'portal_credentials' in response.data
            assert 'username' in response.data['portal_credentials']
            assert 'temporary_password' in response.data['portal_credentials']
            assert 'login_url' in response.data['portal_credentials']
        
        print_success("Response format is correct")
        print(f"  Has 'success': {response.data.get('success')}")
        print(f"  Has 'message': {response.data.get('message')}")
        print(f"  Has 'patient': {'patient' in response.data}")
        print(f"  Has 'portal_created': {'portal_created' in response.data}")
        print(f"  Has 'portal_credentials': {'portal_credentials' in response.data}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all API integration tests."""
    print_header("PATIENT PORTAL API INTEGRATION TESTS")
    
    cleanup()
    
    tests = [
        ("Create without portal", test_api_without_portal),
        ("Create with portal", test_api_with_portal),
        ("Duplicate email error", test_api_duplicate_email_error),
        ("Missing email validation", test_api_missing_email_error),
        ("Response format", test_response_format),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {test_name}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print_header("TEST RESULTS SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{BLUE}Score: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_success("\n*** ALL API TESTS PASSED! View integration working correctly. ***")
    else:
        print_error(f"\n*** {total - passed} test(s) failed. Review errors above. ***")
    
    cleanup()
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
