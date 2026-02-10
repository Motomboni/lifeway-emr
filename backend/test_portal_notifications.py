"""
Test Patient Portal Notifications

Verify that notification messages are properly formatted.

Usage:
    python test_portal_notifications.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.patients.models import Patient
from apps.patients.portal_notifications import (
    prepare_portal_welcome_message,
    notify_portal_account_created,
    notify_new_portal_account
)

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


def test_prepare_message():
    """Test message preparation."""
    print_header("TEST 1: Prepare Welcome Message")
    
    try:
        messages = prepare_portal_welcome_message(
            patient_name='John Doe',
            username='john@example.com',
            temporary_password='xK9mP2nQ7vR3'
        )
        
        # Verify structure
        assert 'subject' in messages
        assert 'email_body' in messages
        assert 'sms_body' in messages
        assert 'login_url' in messages
        
        print_success("Message structure correct")
        print(f"  Subject: {messages['subject']}")
        print(f"  Email length: {len(messages['email_body'])} chars")
        print(f"  SMS length: {len(messages['sms_body'])} chars")
        print(f"  Login URL: {messages['login_url']}")
        
        # Verify content
        assert 'john@example.com' in messages['email_body']
        assert 'xK9mP2nQ7vR3' in messages['email_body']
        assert 'John Doe' in messages['email_body']
        
        assert 'john@example.com' in messages['sms_body']
        assert 'xK9mP2nQ7vR3' in messages['sms_body']
        
        print_success("Message content includes credentials")
        
        # Verify SMS is short
        if len(messages['sms_body']) <= 160:
            print_success(f"SMS body is SMS-friendly ({len(messages['sms_body'])} chars)")
        else:
            print_info(f"SMS body might be split ({len(messages['sms_body'])} chars)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notify_with_patient():
    """Test notification with actual patient object."""
    print_header("TEST 2: Notify with Patient Object")
    
    try:
        # Create test patient
        patient = Patient.objects.create(
            first_name='NotifyTest',
            last_name='Patient',
            email='notifytest@example.com',
            phone='0712345678',
            patient_id='NOTIFY-TEST-001'
        )
        
        # Prepare notifications
        result = notify_portal_account_created(
            patient=patient,
            username='notifytest@example.com',
            temporary_password='testPass456',
            send_email=True,
            send_sms=True,
            phone_number='0712345678'
        )
        
        # Verify result
        assert result['success'] == True
        assert result['patient_id'] == patient.id
        assert result['patient_name'] == 'NotifyTest Patient'
        assert result['username'] == 'notifytest@example.com'
        assert 'notifications_sent' in result
        assert len(result['notifications_sent']) == 2
        
        print_success("Notification prepared successfully")
        print(f"  Patient: {result['patient_name']}")
        print(f"  Username: {result['username']}")
        print(f"  Notifications: {len(result['notifications_sent'])}")
        
        # Verify email notification
        email_notif = next((n for n in result['notifications_sent'] if n['type'] == 'email'), None)
        assert email_notif is not None
        assert email_notif['to'] == 'notifytest@example.com'
        assert email_notif['status'] == 'prepared'
        
        print_success("Email notification prepared")
        print(f"  To: {email_notif['to']}")
        print(f"  Subject: {email_notif['subject']}")
        
        # Verify SMS notification
        sms_notif = next((n for n in result['notifications_sent'] if n['type'] == 'sms'), None)
        assert sms_notif is not None
        assert sms_notif['to'] == '0712345678'
        
        print_success("SMS notification prepared")
        print(f"  To: {sms_notif['to']}")
        print(f"  Body length: {len(sms_notif['body'])} chars")
        
        # Cleanup
        patient.delete()
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convenience_function():
    """Test convenience wrapper function."""
    print_header("TEST 3: Convenience Function")
    
    try:
        patient = Patient.objects.create(
            first_name='ConvTest',
            last_name='User',
            email='convtest@example.com',
            patient_id='CONV-TEST-001'
        )
        
        # Use convenience function
        result = notify_new_portal_account(
            patient=patient,
            username='convtest@example.com',
            temporary_password='convPass789',
            phone='0723456789'
        )
        
        assert result['success'] == True
        assert result['patient_id'] == patient.id
        
        print_success("Convenience function works")
        print(f"  Prepared: {len(result['notifications_sent'])} notification(s)")
        
        # Cleanup
        patient.delete()
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_message_content():
    """Test that messages contain all required elements."""
    print_header("TEST 4: Message Content Validation")
    
    try:
        messages = prepare_portal_welcome_message(
            patient_name='Test User',
            username='test@example.com',
            temporary_password='testPass'
        )
        
        # Check email contains required elements
        email = messages['email_body']
        required_in_email = [
            'Test User',
            'test@example.com',
            'testPass',
            'change your password',
            'first login'
        ]
        
        for required in required_in_email:
            assert required in email, f"Email missing: {required}"
        
        print_success("Email contains all required elements")
        
        # Check SMS contains required elements
        sms = messages['sms_body']
        required_in_sms = [
            'test@example.com',
            'testPass',
            'change'
        ]
        
        for required in required_in_sms:
            assert required in sms, f"SMS missing: {required}"
        
        print_success("SMS contains all required elements")
        
        # Print sample messages
        print(f"\n{BLUE}Sample Email:{RESET}")
        print("─" * 70)
        print(email[:300] + "...")
        
        print(f"\n{BLUE}Sample SMS:{RESET}")
        print("─" * 70)
        print(sms)
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def run_all_tests():
    """Run all notification utility tests."""
    print_header("PATIENT PORTAL NOTIFICATION UTILITY TESTS")
    
    tests = [
        ("Prepare welcome message", test_prepare_message),
        ("Notify with patient object", test_notify_with_patient),
        ("Convenience function", test_convenience_function),
        ("Message content validation", test_message_content),
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
        print_success("\n*** ALL TESTS PASSED! Notification utility working correctly. ***")
    else:
        print_error(f"\n*** {total - passed} test(s) failed. ***")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
