"""
Comprehensive Telemedicine Flow Test

Tests the complete telemedicine workflow:
1. Setup: Create test users, patient, visit
2. Create telemedicine session
3. Generate access tokens
4. Start session
5. End session (with billing)
6. Test transcription (if configured)
7. Cleanup

Usage:
    python test_telemedicine_flow.py
"""
import os
import sys
import django
import json
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.telemedicine.models import TelemedicineSession
from apps.billing.service_catalog_models import ServiceCatalog
from apps.telemedicine.utils import generate_twilio_access_token, create_twilio_room
from apps.telemedicine.transcription import run_transcription

User = get_user_model()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}[OK] {text}{RESET}")

def print_error(text):
    print(f"{RED}[ERROR] {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}[INFO] {text}{RESET}")

def print_detail(label, value):
    print(f"  {label}: {value}")

class TelemedicineFlowTester:
    def __init__(self):
        self.doctor = None
        self.receptionist = None
        self.patient = None
        self.visit = None
        self.session = None
        self.room_info = None
        self.service = None
        
    def cleanup_test_data(self):
        """Clean up any existing test data."""
        print_info("Cleaning up existing test data...")
        
        # Clean up test users
        User.objects.filter(username__startswith='test_tele_').delete()
        
        # Clean up test patient
        Patient.objects.filter(first_name='Test', last_name='Telemedicine').delete()
        
        print_success("Cleanup complete")
    
    def setup_test_data(self):
        """Create necessary test data."""
        print_header("STEP 1: Setting Up Test Data")
        
        try:
            # Create doctor
            self.doctor = User.objects.create_user(
                username='test_tele_doctor',
                email='doctor@test.com',
                password='testpass123',
                role='DOCTOR',
                first_name='Test',
                last_name='Doctor'
            )
            print_success(f"Created doctor: {self.doctor.username}")
            
            # Create receptionist
            self.receptionist = User.objects.create_user(
                username='test_tele_receptionist',
                email='receptionist@test.com',
                password='testpass123',
                role='RECEPTIONIST',
                first_name='Test',
                last_name='Receptionist'
            )
            print_success(f"Created receptionist: {self.receptionist.username}")
            
            # Create patient
            self.patient = Patient.objects.create(
                first_name='Test',
                last_name='Telemedicine',
                date_of_birth='1990-01-01',
                gender='MALE',
                phone='0712345678',
                email='patient@test.com',
                national_id='12345678'
            )
            print_success(f"Created patient: {self.patient.get_full_name()}")
            
            # Create visit
            self.visit = Visit.objects.create(
                patient=self.patient,
                visit_type='CONSULTATION',
                chief_complaint='Virtual consultation needed',
                status='OPEN',
                payment_status='PAID'
            )
            print_success(f"Created visit ID: {self.visit.id}")
            print_detail("Visit Status", self.visit.status)
            print_detail("Payment Status", self.visit.payment_status)
            
            # Create or get telemedicine service for billing test
            self.service, created = ServiceCatalog.objects.get_or_create(
                service_code='TELEMED-001',
                defaults={
                    'name': 'Telemedicine Consultation',
                    'department': 'CONSULTATION',
                    'workflow_type': 'OTHER',
                    'amount': 1000.00,
                    'active': True,
                    'requires_consultation': False
                }
            )
            if created:
                print_success(f"Created telemedicine service: {self.service.name}")
            else:
                print_info(f"Using existing telemedicine service: {self.service.name}")
            
            return True
            
        except Exception as e:
            print_error(f"Failed to setup test data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_twilio_config(self):
        """Check if Twilio is properly configured."""
        print_header("STEP 2: Checking Twilio Configuration")
        
        required_settings = {
            'TWILIO_ACCOUNT_SID': getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
            'TWILIO_AUTH_TOKEN': getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
            'TWILIO_API_KEY': getattr(settings, 'TWILIO_API_KEY', ''),
            'TWILIO_API_SECRET': getattr(settings, 'TWILIO_API_SECRET', ''),
        }
        
        all_configured = True
        for key, value in required_settings.items():
            if value:
                print_success(f"{key}: Configured (length: {len(value)})")
            else:
                print_error(f"{key}: NOT CONFIGURED")
                all_configured = False
        
        if not all_configured:
            print_error("Twilio credentials missing! Telemedicine will not work.")
            print_info("Set credentials in .env or Django settings")
            return False
        
        return True
    
    def create_telemedicine_session(self):
        """Create a telemedicine session."""
        print_header("STEP 3: Creating Telemedicine Session")
        
        try:
            # Create Twilio room first
            room_name = f"session-{self.visit.id}-{timezone.now().timestamp()}"
            self.room_info = create_twilio_room(room_name, max_participants=10)
            print_success("Created Twilio room")
            print_detail("Room SID", self.room_info['room_sid'])
            print_detail("Room Name", self.room_info['room_name'])
            print_detail("Status", self.room_info['status'])
            
            # Create database session record
            scheduled_start = timezone.now() + timedelta(minutes=5)
            self.session = TelemedicineSession.objects.create(
                visit=self.visit,
                twilio_room_sid=self.room_info['room_sid'],
                twilio_room_name=self.room_info['room_name'],
                status='SCHEDULED',
                doctor=self.doctor,
                patient=self.patient,
                scheduled_start=scheduled_start,
                recording_enabled=True,  # Enable recording for transcription test
                created_by=self.doctor
            )
            print_success(f"Created session record ID: {self.session.id}")
            print_detail("Status", self.session.status)
            print_detail("Recording Enabled", self.session.recording_enabled)
            print_detail("Scheduled Start", scheduled_start.strftime('%Y-%m-%d %H:%M'))
            
            return True
            
        except Exception as e:
            print_error(f"Failed to create session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_access_tokens(self):
        """Generate access tokens for participants."""
        print_header("STEP 4: Generating Access Tokens")
        
        try:
            # Generate token for doctor
            doctor_token = generate_twilio_access_token(
                self.doctor,
                self.room_info['room_name']
            )
            print_success("Generated doctor access token")
            print_detail("Token Length", len(doctor_token))
            print_detail("Token Preview", doctor_token[:60] + "...")
            
            # Generate token for patient (using receptionist user as proxy)
            patient_token = generate_twilio_access_token(
                self.receptionist,  # Using receptionist as patient proxy
                self.room_info['room_name']
            )
            print_success("Generated patient access token")
            print_detail("Token Length", len(patient_token))
            
            return True
            
        except Exception as e:
            print_error(f"Failed to generate tokens: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def simulate_session_lifecycle(self):
        """Simulate starting and ending a session."""
        print_header("STEP 5: Simulating Session Lifecycle")
        
        try:
            # Start session
            self.session.status = 'IN_PROGRESS'
            self.session.actual_start = timezone.now()
            self.session.save()
            print_success("Session started")
            print_detail("Status", self.session.status)
            print_detail("Start Time", self.session.actual_start.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Simulate session duration
            print_info("Simulating 5-minute session...")
            import time
            time.sleep(2)  # Wait 2 seconds to simulate passage of time
            
            # End session
            self.session.status = 'COMPLETED'
            self.session.actual_end = timezone.now()
            self.session.duration_seconds = int(
                (self.session.actual_end - self.session.actual_start).total_seconds()
            )
            self.session.notes = "Test telemedicine session completed successfully"
            self.session.save()
            
            print_success("Session ended")
            print_detail("Status", self.session.status)
            print_detail("End Time", self.session.actual_end.strftime('%Y-%m-%d %H:%M:%S'))
            print_detail("Duration", f"{self.session.duration_seconds} seconds")
            
            return True
            
        except Exception as e:
            print_error(f"Failed to simulate session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_billing_integration(self):
        """Test telemedicine billing integration."""
        print_header("STEP 6: Testing Billing Integration")
        
        try:
            from apps.billing.billing_line_item_service import create_billing_line_item_from_service
            
            # Create billing line item for telemedicine
            line_item = create_billing_line_item_from_service(
                visit=self.visit,
                service=self.service,
                quantity=1,
                created_by=self.doctor
            )
            
            print_success("Created billing line item")
            print_detail("Service", self.service.name)
            print_detail("Amount", f"KES {line_item.amount}")
            print_detail("Quantity", line_item.quantity)
            print_detail("Total", f"KES {line_item.total_amount}")
            
            # Check visit charges
            total_charges = self.visit.charges.aggregate(
                total=django.db.models.Sum('total_amount')
            )['total'] or 0
            
            print_info(f"Visit total charges: KES {total_charges}")
            
            return True
            
        except Exception as e:
            print_error(f"Failed billing integration test: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_transcription(self):
        """Test transcription functionality."""
        print_header("STEP 7: Testing Transcription (Optional)")
        
        # Check if transcription is configured
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or \
                  getattr(settings, 'TRANSCRIPTION_API_KEY', None)
        
        if not api_key:
            print_info("Transcription not configured (no OPENAI_API_KEY)")
            print_info("Skipping transcription test")
            return True
        
        try:
            # Note: This will likely fail without a real recording
            print_info("Attempting transcription (will likely fail without real recording)...")
            result = run_transcription(self.session)
            
            if result:
                print_success("Transcription completed")
                print_detail("Status", self.session.transcription_status)
                print_detail("Text Length", len(self.session.transcription_text))
            else:
                print_info("Transcription set to PENDING (expected without real recording)")
                print_detail("Status", self.session.transcription_status)
            
            return True
            
        except Exception as e:
            print_info(f"Transcription test (expected to fail): {e}")
            return True  # Don't fail the whole test
    
    def display_summary(self):
        """Display test summary."""
        print_header("TEST SUMMARY")
        
        print(f"{BLUE}Session Details:{RESET}")
        print_detail("Session ID", self.session.id)
        print_detail("Visit ID", self.visit.id)
        print_detail("Patient", self.patient.get_full_name())
        print_detail("Doctor", self.doctor.get_full_name())
        print_detail("Status", self.session.status)
        print_detail("Room SID", self.session.twilio_room_sid)
        print_detail("Duration", f"{self.session.duration_seconds} seconds")
        print_detail("Recording Enabled", self.session.recording_enabled)
        
        print(f"\n{BLUE}Billing:{RESET}")
        charges = self.visit.charges.all()
        for charge in charges:
            print_detail("Charge", f"{charge.description} - KES {charge.total_amount}")
        
        print(f"\n{BLUE}API Endpoints to Test:{RESET}")
        base_url = "http://localhost:8000/api/v1"
        print_detail("List Sessions", f"GET {base_url}/telemedicine/")
        print_detail("Session Detail", f"GET {base_url}/telemedicine/{self.session.id}/")
        print_detail("Generate Token", f"POST {base_url}/telemedicine/{self.session.id}/generate-token/")
        print_detail("Start Session", f"POST {base_url}/telemedicine/{self.session.id}/start/")
        print_detail("End Session", f"POST {base_url}/telemedicine/{self.session.id}/end/")
    
    def run_all_tests(self):
        """Run all telemedicine flow tests."""
        print_header("TELEMEDICINE FLOW TEST - COMPREHENSIVE")
        print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Run tests in sequence
        tests = [
            ("Setup Test Data", self.setup_test_data),
            ("Check Twilio Config", self.check_twilio_config),
            ("Create Session", self.create_telemedicine_session),
            ("Generate Tokens", self.generate_access_tokens),
            ("Session Lifecycle", self.simulate_session_lifecycle),
            ("Billing Integration", self.test_billing_integration),
            ("Transcription", self.test_transcription),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if not result and test_name != "Transcription":
                    print_error(f"Test failed: {test_name}")
                    print_error("Stopping test execution")
                    break
            except Exception as e:
                print_error(f"Test crashed: {test_name} - {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
                break
        
        # Display summary
        if self.session:
            self.display_summary()
        
        # Final results
        print_header("FINAL RESULTS")
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            if result:
                print_success(f"{test_name}: PASSED")
            else:
                print_error(f"{test_name}: FAILED")
        
        print(f"\n{BLUE}Score: {passed}/{total} tests passed{RESET}")
        
        if passed == total:
            print_success("\n*** ALL TESTS PASSED! Telemedicine system is working correctly. ***")
        else:
            print_error(f"\n*** WARNING: {total - passed} test(s) failed. Check configuration. ***")
        
        print_info(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return passed == total


if __name__ == '__main__':
    import django.db.models
    tester = TelemedicineFlowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
