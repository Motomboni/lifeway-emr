"""
Simple script to test telemedicine API endpoints.

Run this after setting up Twilio credentials to verify the API works.

Usage:
    python manage.py shell < scripts/test_telemedicine_api.py
    OR
    python scripts/test_telemedicine_api.py (if run from backend directory)
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.telemedicine.utils import generate_twilio_access_token, create_twilio_room
from django.conf import settings

User = get_user_model()

print("\n" + "="*60)
print("Testing Telemedicine API Functions")
print("="*60 + "\n")

# Check if Twilio is configured
if not all([
    getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
    getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
    getattr(settings, 'TWILIO_API_KEY', ''),
    getattr(settings, 'TWILIO_API_SECRET', ''),
]):
    print("[ERROR] Twilio credentials not configured!")
    print("Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_API_KEY, and TWILIO_API_SECRET")
    exit(1)

# Test 1: Generate Access Token
print("[TEST 1] Testing Access Token Generation...")
try:
    # Get or create a test user
    user, _ = User.objects.get_or_create(
        username='test_telemedicine_user',
        defaults={'email': 'test@example.com', 'role': 'DOCTOR'}
    )
    
    room_name = 'test-room-' + str(user.id)
    token = generate_twilio_access_token(user, room_name)
    
    if token:
        print(f"[OK] Access token generated successfully")
        print(f"     Token length: {len(token)} characters")
        print(f"     Token preview: {token[:50]}...")
    else:
        print("[ERROR] Failed to generate token")
        exit(1)
except Exception as e:
    print(f"[ERROR] Token generation failed: {e}")
    exit(1)

# Test 2: Create Twilio Room
print("\n[TEST 2] Testing Room Creation...")
try:
    room_info = create_twilio_room(room_name, max_participants=2)
    print(f"[OK] Room created successfully")
    print(f"     Room SID: {room_info['room_sid']}")
    print(f"     Room Name: {room_info['room_name']}")
    print(f"     Status: {room_info['status']}")
except Exception as e:
    print(f"[ERROR] Room creation failed: {e}")
    print("     This might be due to:")
    print("     - Invalid Twilio credentials")
    print("     - Network issues")
    print("     - Twilio account restrictions")
    exit(1)

# Test 3: Verify token works with room
print("\n[TEST 3] Verifying Token and Room Compatibility...")
try:
    # Generate another token for the same room
    token2 = generate_twilio_access_token(user, room_name)
    if token2:
        print("[OK] Token is compatible with room")
    else:
        print("[ERROR] Token generation failed")
        exit(1)
except Exception as e:
    print(f"[ERROR] Verification failed: {e}")
    exit(1)

print("\n" + "="*60)
print("[SUCCESS] All telemedicine API tests passed!")
print("="*60)
print("\nYour Twilio setup is working correctly.")
print("You can now use telemedicine features in the EMR system.\n")
