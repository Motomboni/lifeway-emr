"""
Test Patient Portal Serializer

Verify that PatientCreateSerializer handles portal account creation correctly.

Usage:
    python test_portal_serializer.py
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
from apps.patients.serializers import PatientCreateSerializer

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
    User.objects.filter(username__startswith='serializer_test_').delete()
    Patient.objects.filter(first_name='SerializerTest').delete()
    print_success("Cleanup complete")


def test_basic_patient_creation():
    """Test creating a basic patient without portal."""
    print_header("TEST 1: Basic Patient Creation (No Portal)")
    
    try:
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'BasicPatient',
            'date_of_birth': '1990-01-01',
            'gender': 'MALE',
        }
        
        serializer = PatientCreateSerializer(data=data)
        if not serializer.is_valid():
            print_error(f"Validation failed: {serializer.errors}")
            return False
        
        patient = serializer.save()
        response_data = serializer.data
        
        assert patient.id is not None
        assert response_data['portal_created'] == False
        assert 'temporary_password' not in response_data or response_data.get('temporary_password') is None
        
        print_success(f"Created patient ID: {patient.id}")
        print(f"  Portal Created: {response_data.get('portal_created', False)}")
        print(f"  Portal Enabled: {patient.portal_enabled}")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portal_account_creation():
    """Test creating a patient with portal account."""
    print_header("TEST 2: Patient with Portal Account")
    
    try:
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'PortalUser',
            'date_of_birth': '1985-05-15',
            'gender': 'FEMALE',
            'create_portal_account': True,
            'portal_email': 'serializer_test_portal@example.com',
            'portal_phone': '0712345678',
        }
        
        serializer = PatientCreateSerializer(data=data)
        if not serializer.is_valid():
            print_error(f"Validation failed: {serializer.errors}")
            return False
        
        patient = serializer.save()
        response_data = serializer.data
        
        # Verify patient created
        assert patient.id is not None
        print_success(f"Created patient ID: {patient.id}")
        
        # Verify portal settings
        assert patient.portal_enabled == True
        print_success("Patient.portal_enabled = True")
        
        # Verify response data
        assert response_data['portal_created'] == True
        assert 'temporary_password' in response_data
        assert response_data['temporary_password'] is not None
        assert len(response_data['temporary_password']) == 12
        
        print_success("Portal account created")
        print(f"  Portal Created: {response_data['portal_created']}")
        print(f"  Temp Password: {response_data['temporary_password']}")
        print(f"  Password Length: {len(response_data['temporary_password'])}")
        
        # Verify user created
        portal_user = User.objects.get(username='serializer_test_portal@example.com')
        assert portal_user.role == 'PATIENT'
        assert portal_user.patient == patient
        assert portal_user.email == 'serializer_test_portal@example.com'
        
        print_success("User account created and linked")
        print(f"  User ID: {portal_user.id}")
        print(f"  Username: {portal_user.username}")
        print(f"  Role: {portal_user.role}")
        print(f"  Linked Patient: {portal_user.patient.patient_id}")
        
        # Verify one-to-one relationship
        assert patient.portal_user == portal_user
        print_success("One-to-one relationship verified")
        
        # Verify password is hashed (not plaintext)
        assert portal_user.password.startswith('pbkdf2_sha256$') or portal_user.password.startswith('bcrypt')
        print_success("Password is properly hashed")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_missing_email():
    """Test that portal creation without email fails validation."""
    print_header("TEST 3: Validation - Missing Email")
    
    try:
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'NoEmail',
            'create_portal_account': True,
            # Missing portal_email
        }
        
        serializer = PatientCreateSerializer(data=data)
        is_valid = serializer.is_valid()
        
        if is_valid:
            print_error("Validation should have failed for missing email")
            return False
        
        error_message = str(serializer.errors)
        if 'email' in error_message.lower() and 'required' in error_message.lower():
            print_success("Validation correctly requires email")
            print(f"  Error: {serializer.errors}")
            return True
        else:
            print_error(f"Unexpected error message: {serializer.errors}")
            return False
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_validation_invalid_email():
    """Test that invalid email format fails validation."""
    print_header("TEST 4: Validation - Invalid Email Format")
    
    try:
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'InvalidEmail',
            'create_portal_account': True,
            'portal_email': 'not-an-email',
        }
        
        serializer = PatientCreateSerializer(data=data)
        is_valid = serializer.is_valid()
        
        if is_valid:
            print_error("Validation should have failed for invalid email")
            return False
        
        error_message = str(serializer.errors)
        if 'email' in error_message.lower() and ('invalid' in error_message.lower() or 'format' in error_message.lower()):
            print_success("Validation correctly rejects invalid email format")
            print(f"  Error: {serializer.errors}")
            return True
        else:
            print_error(f"Unexpected error message: {serializer.errors}")
            return False
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_validation_duplicate_email():
    """Test that duplicate email fails validation."""
    print_header("TEST 5: Validation - Duplicate Email")
    
    try:
        # First, create a user with an email
        existing_user = User.objects.create_user(
            username='serializer_test_existing@example.com',
            password='testpass123',
            role='DOCTOR'
        )
        print_info(f"Created existing user: {existing_user.username}")
        
        # Try to create patient with same email
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'DuplicateEmail',
            'create_portal_account': True,
            'portal_email': 'serializer_test_existing@example.com',
        }
        
        serializer = PatientCreateSerializer(data=data)
        is_valid = serializer.is_valid()
        
        if is_valid:
            print_error("Validation should have failed for duplicate email")
            return False
        
        error_message = str(serializer.errors)
        if 'already exists' in error_message.lower():
            print_success("Validation correctly prevents duplicate email")
            print(f"  Error: {serializer.errors}")
            return True
        else:
            print_error(f"Unexpected error message: {serializer.errors}")
            return False
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atomic_transaction():
    """Test that transaction rollback works on failure."""
    print_header("TEST 6: Atomic Transaction Rollback")
    
    try:
        # Count patients before
        patient_count_before = Patient.objects.count()
        user_count_before = User.objects.count()
        
        print_info(f"Before: {patient_count_before} patients, {user_count_before} users")
        
        # Try to create with duplicate email (should fail after patient creation)
        existing_user = User.objects.get_or_create(
            username='serializer_test_rollback@example.com',
            defaults={'password': 'test', 'role': 'DOCTOR'}
        )[0]
        
        data = {
            'first_name': 'SerializerTest',
            'last_name': 'Rollback',
            'create_portal_account': True,
            'portal_email': 'serializer_test_rollback@example.com',  # Duplicate
        }
        
        serializer = PatientCreateSerializer(data=data)
        if serializer.is_valid():
            try:
                patient = serializer.save()
                print_error("Should have failed due to duplicate email")
                return False
            except Exception:
                # Expected to fail
                pass
        
        # Count after - should be same (rollback occurred)
        patient_count_after = Patient.objects.count()
        user_count_after = User.objects.count()
        
        print_info(f"After: {patient_count_after} patients, {user_count_after} users")
        
        if patient_count_after == patient_count_before:
            print_success("Transaction rolled back correctly - no orphaned patient")
            return True
        else:
            print_error(f"Patient count changed: {patient_count_before} -> {patient_count_after}")
            return False
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all serializer tests."""
    print_header("PATIENT PORTAL SERIALIZER TESTS")
    
    cleanup()
    
    tests = [
        ("Basic patient creation", test_basic_patient_creation),
        ("Portal account creation", test_portal_account_creation),
        ("Validation: Missing email", test_validation_missing_email),
        ("Validation: Invalid email", test_validation_invalid_email),
        ("Validation: Duplicate email", test_validation_duplicate_email),
        ("Atomic transaction rollback", test_atomic_transaction),
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
        print_success("\n*** ALL TESTS PASSED! Serializer is working correctly. ***")
    else:
        print_error(f"\n*** {total - passed} test(s) failed. Review errors above. ***")
    
    cleanup()
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
