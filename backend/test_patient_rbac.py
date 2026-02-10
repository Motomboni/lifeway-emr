"""
Test Patient Portal RBAC

Verify that PATIENT role users can only access their own data.

Usage:
    python test_patient_rbac.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.patients.patient_permissions import (
    IsPatientOwner,
    IsPatientOwnerOrStaff,
    PatientPortalAccess,
    filter_queryset_for_patient
)
from apps.visits.models import Visit

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
    print_info("Cleaning up test data...")
    User.objects.filter(username__startswith='rbac_test_').delete()
    Patient.objects.filter(first_name='RBACTest').delete()
    print_success("Cleanup complete")


def test_patient_access_own_data():
    """Test PATIENT user can access their own data."""
    print_header("TEST 1: PATIENT Can Access Own Data")
    
    try:
        # Setup
        patient = Patient.objects.create(
            first_name='RBACTest',
            last_name='OwnData',
            patient_id='RBAC-001'
        )
        user = User.objects.create_user(
            username='rbac_test_patient1@example.com',
            password='pass',
            role='PATIENT',
            patient=patient
        )
        visit = Visit.objects.create(patient=patient, status='OPEN')
        
        # Create mock request
        factory = RequestFactory()
        request = factory.get('/')
        request.user = user
        
        # Test permission
        permission = IsPatientOwner()
        
        # View-level permission (GET)
        has_perm = permission.has_permission(request, None)
        assert has_perm == True, "Should allow GET for PATIENT"
        
        print_success("View-level permission granted for GET")
        
        # Object-level permission (own visit)
        has_obj_perm = permission.has_object_permission(request, None, visit)
        assert has_obj_perm == True, "Should allow access to own visit"
        
        print_success("Object-level permission granted for own data")
        print(f"  User patient ID: {user.patient.id}")
        print(f"  Visit patient ID: {visit.patient.id}")
        print(f"  Match: {user.patient.id == visit.patient.id}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_cannot_access_other_data():
    """Test PATIENT user cannot access another patient's data."""
    print_header("TEST 2: PATIENT Cannot Access Other Patient's Data")
    
    try:
        # Setup two patients
        patient1 = Patient.objects.create(
            first_name='RBACTest',
            last_name='Patient1',
            patient_id='RBAC-002'
        )
        patient2 = Patient.objects.create(
            first_name='RBACTest',
            last_name='Patient2',
            patient_id='RBAC-003'
        )
        
        user1 = User.objects.create_user(
            username='rbac_test_patient2@example.com',
            password='pass',
            role='PATIENT',
            patient=patient1
        )
        
        visit2 = Visit.objects.create(patient=patient2, status='OPEN')
        
        # Create mock request from user1
        factory = RequestFactory()
        request = factory.get('/')
        request.user = user1
        
        # Test permission
        permission = IsPatientOwner()
        
        # Try to access patient2's visit
        has_obj_perm = permission.has_object_permission(request, None, visit2)
        assert has_obj_perm == False, "Should deny access to other patient's data"
        
        print_success("Access denied to other patient's data")
        print(f"  User patient ID: {user1.patient.id}")
        print(f"  Visit patient ID: {visit2.patient.id}")
        print(f"  Match: {user1.patient.id == visit2.patient.id}")
        print(f"  Access: DENIED (correct)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_read_only():
    """Test PATIENT user is read-only (cannot POST/PUT/DELETE)."""
    print_header("TEST 3: PATIENT Is Read-Only")
    
    try:
        patient = Patient.objects.create(
            first_name='RBACTest',
            last_name='ReadOnly',
            patient_id='RBAC-004'
        )
        user = User.objects.create_user(
            username='rbac_test_patient3@example.com',
            password='pass',
            role='PATIENT',
            patient=patient
        )
        
        factory = RequestFactory()
        permission = IsPatientOwner()
        
        # Test GET (should allow)
        request_get = factory.get('/')
        request_get.user = user
        assert permission.has_permission(request_get, None) == True
        print_success("GET allowed")
        
        # Test POST (should deny)
        request_post = factory.post('/')
        request_post.user = user
        assert permission.has_permission(request_post, None) == False
        print_success("POST denied")
        
        # Test PUT (should deny)
        request_put = factory.put('/')
        request_put.user = user
        assert permission.has_permission(request_put, None) == False
        print_success("PUT denied")
        
        # Test DELETE (should deny)
        request_delete = factory.delete('/')
        request_delete.user = user
        assert permission.has_permission(request_delete, None) == False
        print_success("DELETE denied")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_staff_access_all():
    """Test staff (DOCTOR) can access all patient data."""
    print_header("TEST 4: Staff Can Access All Data")
    
    try:
        patient = Patient.objects.create(
            first_name='RBACTest',
            last_name='StaffAccess',
            patient_id='RBAC-005'
        )
        doctor = User.objects.create_user(
            username='rbac_test_doctor@example.com',
            password='pass',
            role='DOCTOR'
        )
        visit = Visit.objects.create(patient=patient, status='OPEN')
        
        # Create mock request from doctor
        factory = RequestFactory()
        request = factory.get('/')
        request.user = doctor
        
        # Test permission
        permission = IsPatientOwner()
        
        # View-level (should pass through)
        has_perm = permission.has_permission(request, None)
        assert has_perm == True
        print_success("Staff has view-level permission")
        
        # Object-level (should pass through)
        has_obj_perm = permission.has_object_permission(request, None, visit)
        assert has_obj_perm == True
        print_success("Staff has object-level permission")
        print(f"  Staff role: {doctor.role}")
        print(f"  Can access any patient's data: Yes")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_queryset_filtering():
    """Test queryset filtering for PATIENT users."""
    print_header("TEST 5: Queryset Filtering")
    
    try:
        # Setup
        patient1 = Patient.objects.create(
            first_name='RBACTest',
            last_name='Filter1',
            patient_id='RBAC-006'
        )
        patient2 = Patient.objects.create(
            first_name='RBACTest',
            last_name='Filter2',
            patient_id='RBAC-007'
        )
        
        user1 = User.objects.create_user(
            username='rbac_test_filter@example.com',
            password='pass',
            role='PATIENT',
            patient=patient1
        )
        
        # Create visits for both patients
        visit1 = Visit.objects.create(patient=patient1)
        visit2 = Visit.objects.create(patient=patient2)
        
        # Get all visits
        all_visits = Visit.objects.all()
        print_info(f"Total visits in DB: {all_visits.count()}")
        
        # Filter for patient1
        filtered = filter_queryset_for_patient(all_visits, user1)
        filtered_ids = list(filtered.values_list('id', flat=True))
        
        print_success(f"Filtered queryset: {filtered.count()} visit(s)")
        print(f"  User patient ID: {user1.patient.id}")
        print(f"  Filtered visit IDs: {filtered_ids}")
        
        # Verify only patient1's visit
        assert visit1.id in filtered_ids
        assert visit2.id not in filtered_ids
        
        print_success("Queryset correctly filtered to user's own data")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portal_access_permission():
    """Test PatientPortalAccess permission."""
    print_header("TEST 6: Portal Access Permission")
    
    try:
        patient = Patient.objects.create(
            first_name='RBACTest',
            last_name='PortalAccess',
            patient_id='RBAC-008'
        )
        
        # Patient user
        patient_user = User.objects.create_user(
            username='rbac_test_portal@example.com',
            password='pass',
            role='PATIENT',
            patient=patient
        )
        
        # Doctor user
        doctor = User.objects.create_user(
            username='rbac_test_doctor2@example.com',
            password='pass',
            role='DOCTOR'
        )
        
        factory = RequestFactory()
        permission = PatientPortalAccess()
        
        # Patient user should have access
        request_patient = factory.get('/')
        request_patient.user = patient_user
        assert permission.has_permission(request_patient, None) == True
        print_success("PATIENT user granted portal access")
        
        # Doctor user should NOT have access (portal is for patients only)
        request_doctor = factory.get('/')
        request_doctor.user = doctor
        assert permission.has_permission(request_doctor, None) == False
        print_success("Staff user denied portal access (portal is patient-only)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def run_all_tests():
    """Run all RBAC tests."""
    print_header("PATIENT PORTAL RBAC TESTS")
    
    cleanup()
    
    tests = [
        ("PATIENT access own data", test_patient_access_own_data),
        ("PATIENT denied other data", test_patient_cannot_access_other_data),
        ("PATIENT read-only", test_patient_read_only),
        ("Staff access all data", test_staff_access_all),
        ("Queryset filtering", test_queryset_filtering),
        ("Portal access permission", test_portal_access_permission),
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
        print_success("\n*** ALL RBAC TESTS PASSED! Access control working correctly. ***")
    else:
        print_error(f"\n*** {total - passed} test(s) failed. ***")
    
    cleanup()
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
