"""
Test Patient Portal Setup

Verify that patient portal accounts work correctly with the new schema.

Usage:
    python test_patient_portal_setup.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.patients.models import Patient

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
    print_info("Cleaning up existing test data...")
    User.objects.filter(username__startswith='test_portal_').delete()
    Patient.objects.filter(first_name='TestPortal').delete()
    print_success("Cleanup complete")


def test_patient_model_has_portal_enabled():
    """Test that Patient model has portal_enabled field."""
    print_header("TEST 1: Verify Patient.portal_enabled Field")
    
    try:
        patient = Patient(
            first_name='TestPortal',
            last_name='Patient',
            patient_id='TEST-PORTAL-001',
            portal_enabled=False
        )
        assert hasattr(patient, 'portal_enabled'), "Patient model missing portal_enabled field"
        assert patient.portal_enabled == False, "Default value should be False"
        print_success("Patient.portal_enabled field exists with correct default")
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def test_user_model_has_patient_field():
    """Test that User model has patient OneToOneField."""
    print_header("TEST 2: Verify User.patient Field")
    
    try:
        user = User(username='test', password='pass', role='DOCTOR')
        assert hasattr(user, 'patient'), "User model missing patient field"
        assert user.patient is None, "Default value should be None"
        print_success("User.patient field exists with correct default")
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def test_create_patient_with_portal_enabled():
    """Test creating a patient with portal enabled."""
    print_header("TEST 3: Create Patient with Portal Enabled")
    
    try:
        patient = Patient.objects.create(
            first_name='TestPortal',
            last_name='User',
            email='testportal@example.com',
            phone='0712345678',
            patient_id='TEST-PORTAL-002',
            portal_enabled=True
        )
        
        assert patient.portal_enabled == True
        print_success(f"Created patient {patient.patient_id} with portal_enabled=True")
        print(f"  Patient ID: {patient.id}")
        print(f"  Portal Enabled: {patient.portal_enabled}")
        return patient
    except Exception as e:
        print_error(f"Failed: {e}")
        return None


def test_create_patient_user():
    """Test creating a user with PATIENT role and patient link."""
    print_header("TEST 4: Create User with PATIENT Role")
    
    # First create a patient
    patient = Patient.objects.create(
        first_name='TestPortal',
        last_name='UserLinked',
        email='testportal2@example.com',
        patient_id='TEST-PORTAL-003',
        portal_enabled=True
    )
    
    try:
        user = User.objects.create_user(
            username='test_portal_patient',
            password='TestPass123!',
            email=patient.email,
            role='PATIENT',
            patient=patient,
            first_name=patient.first_name,
            last_name=patient.last_name
        )
        
        print_success(f"Created patient user: {user.username}")
        print(f"  User ID: {user.id}")
        print(f"  Role: {user.role}")
        print(f"  Linked Patient: {user.patient.patient_id if user.patient else None}")
        print(f"  Patient Portal User: {patient.portal_user.username if hasattr(patient, 'portal_user') else None}")
        
        # Verify relationships
        assert user.patient == patient, "User->Patient relationship broken"
        assert patient.portal_user == user, "Patient->User relationship broken"
        
        print_success("One-to-one relationship verified")
        return user
    except Exception as e:
        print_error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_validation_patient_role_requires_patient():
    """Test that PATIENT role requires patient link."""
    print_header("TEST 5: Validation - PATIENT Role Requires Patient Link")
    
    try:
        user = User(
            username='test_portal_invalid',
            role='PATIENT',
            patient=None  # Should fail validation
        )
        user.full_clean()  # This should raise ValidationError
        
        print_error("Validation failed to catch missing patient link")
        return False
    except ValidationError as e:
        if 'patient' in str(e).lower() or 'link' in str(e).lower():
            print_success("Validation correctly requires patient link for PATIENT role")
            print(f"  Error message: {e}")
            return True
        else:
            print_error(f"Unexpected validation error: {e}")
            return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_validation_non_patient_cannot_link():
    """Test that non-PATIENT roles cannot link to patient."""
    print_header("TEST 6: Validation - Non-PATIENT Cannot Link to Patient")
    
    patient = Patient.objects.create(
        first_name='TestPortal',
        last_name='InvalidLink',
        patient_id='TEST-PORTAL-004',
        portal_enabled=False
    )
    
    try:
        user = User(
            username='test_portal_doctor',
            role='DOCTOR',
            patient=patient  # Should fail validation
        )
        user.full_clean()  # This should raise ValidationError
        
        print_error("Validation failed to catch invalid patient link")
        return False
    except ValidationError as e:
        if 'patient' in str(e).lower() or 'role' in str(e).lower():
            print_success("Validation correctly prevents non-PATIENT roles from linking")
            print(f"  Error message: {e}")
            return True
        else:
            print_error(f"Unexpected validation error: {e}")
            return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_one_to_one_constraint():
    """Test that one patient can only have one portal user."""
    print_header("TEST 7: One-to-One Constraint")
    
    patient = Patient.objects.create(
        first_name='TestPortal',
        last_name='OneToOne',
        patient_id='TEST-PORTAL-005',
        portal_enabled=True
    )
    
    try:
        # Create first user
        user1 = User.objects.create_user(
            username='test_portal_user1',
            password='pass',
            role='PATIENT',
            patient=patient
        )
        print_success(f"Created first user: {user1.username}")
        
        # Try to create second user for same patient
        try:
            user2 = User.objects.create_user(
                username='test_portal_user2',
                password='pass',
                role='PATIENT',
                patient=patient
            )
            print_error("Second user created - one-to-one constraint not enforced!")
            return False
        except Exception as e:
            print_success("One-to-one constraint enforced - second user creation failed")
            print(f"  Error: {type(e).__name__}")
            return True
            
    except Exception as e:
        print_error(f"Test setup failed: {e}")
        return False


def test_database_schema():
    """Verify database schema changes."""
    print_header("TEST 8: Database Schema Verification")
    
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check Patient table
        cursor.execute("PRAGMA table_info(patients)")
        patient_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'portal_enabled' in patient_columns:
            print_success("Patient.portal_enabled column exists in database")
            print(f"  Type: {patient_columns['portal_enabled']}")
        else:
            print_error("Patient.portal_enabled column missing from database")
            return False
        
        # Check User table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'patient_id' in user_columns:
            print_success("User.patient_id column exists in database")
            print(f"  Type: {user_columns['patient_id']}")
        else:
            print_error("User.patient_id column missing from database")
            return False
    
    return True


def run_all_tests():
    """Run all patient portal tests."""
    print_header("PATIENT PORTAL SETUP VERIFICATION")
    print_info(f"Testing patient portal account implementation...")
    
    # Cleanup first
    cleanup()
    
    tests = [
        ("Patient.portal_enabled field", test_patient_model_has_portal_enabled),
        ("User.patient field", test_user_model_has_patient_field),
        ("Create patient with portal", test_create_patient_with_portal_enabled),
        ("Create patient user account", test_create_patient_user),
        ("Validation: PATIENT requires link", test_validation_patient_role_requires_patient),
        ("Validation: Non-PATIENT cannot link", test_validation_non_patient_cannot_link),
        ("One-to-one constraint", test_one_to_one_constraint),
        ("Database schema", test_database_schema),
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
        print_success("\n*** ALL TESTS PASSED! Patient portal setup is working correctly. ***")
    else:
        print_error(f"\n*** {total - passed} test(s) failed. Review errors above. ***")
    
    # Cleanup
    cleanup()
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
