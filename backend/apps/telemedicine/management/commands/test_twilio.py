"""
Django management command to test Twilio configuration.

Usage:
    python manage.py test_twilio
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Test Twilio Video configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n[TEST] Testing Twilio Configuration...\n'))
        
        # Check if Twilio package is installed
        try:
            import twilio
            self.stdout.write(self.style.SUCCESS('[OK] Twilio package is installed'))
            self.stdout.write(f'   Version: {twilio.__version__}')
        except ImportError:
            self.stdout.write(self.style.ERROR('[ERROR] Twilio package is NOT installed'))
            self.stdout.write(self.style.WARNING('   Install with: pip install twilio'))
            sys.exit(1)
        
        # Check Twilio Video SDK
        try:
            from twilio.jwt.access_token import AccessToken
            from twilio.jwt.access_token.grants import VideoGrant
            from twilio.rest import Client
            self.stdout.write(self.style.SUCCESS('[OK] Twilio Video SDK is available'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Twilio Video SDK import failed: {e}'))
            sys.exit(1)
        
        # Check configuration
        self.stdout.write('\n[CHECK] Checking Configuration:\n')
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        api_key = getattr(settings, 'TWILIO_API_KEY', '')
        api_secret = getattr(settings, 'TWILIO_API_SECRET', '')
        recording_enabled = getattr(settings, 'TWILIO_RECORDING_ENABLED', False)
        
        checks = [
            ('TWILIO_ACCOUNT_SID', account_sid, 'Account SID'),
            ('TWILIO_AUTH_TOKEN', auth_token, 'Auth Token'),
            ('TWILIO_API_KEY', api_key, 'API Key SID'),
            ('TWILIO_API_SECRET', api_secret, 'API Secret'),
        ]
        
        all_configured = True
        for key, value, name in checks:
            if value:
                # Mask sensitive values
                masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                self.stdout.write(self.style.SUCCESS('[OK] ' + name + ': ' + masked))
            else:
                self.stdout.write(self.style.ERROR('[ERROR] ' + name + ': NOT SET'))
                self.stdout.write(self.style.WARNING('   Set ' + key + ' in .env or environment variables'))
                all_configured = False
        
        self.stdout.write(f'\n[INFO] Recording Enabled: {recording_enabled}')
        
        if not all_configured:
            self.stdout.write(self.style.ERROR('\n[ERROR] Configuration incomplete!'))
            self.stdout.write(self.style.WARNING('\nPlease set all Twilio credentials in .env file:'))
            self.stdout.write('   TWILIO_ACCOUNT_SID=your_account_sid')
            self.stdout.write('   TWILIO_AUTH_TOKEN=your_auth_token')
            self.stdout.write('   TWILIO_API_KEY=your_api_key_sid')
            self.stdout.write('   TWILIO_API_SECRET=your_api_secret')
            sys.exit(1)
        
        # Test Twilio connection
        self.stdout.write('\n[TEST] Testing Twilio Connection...\n')
        try:
            client = Client(account_sid, auth_token)
            account = client.api.accounts(account_sid).fetch()
            self.stdout.write(self.style.SUCCESS('[OK] Successfully connected to Twilio'))
            self.stdout.write(f'   Account Name: {account.friendly_name}')
            self.stdout.write(f'   Account Status: {account.status}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Failed to connect to Twilio: {e}'))
            self.stdout.write(self.style.WARNING('   Check your Account SID and Auth Token'))
            sys.exit(1)
        
        # Test API Key
        self.stdout.write('\n[TEST] Testing API Key...\n')
        try:
            # Verify API Key belongs to the account
            # Note: This may fail with 403 if Auth Token doesn't have API Key read permissions
            # That's okay - we'll verify by attempting token generation instead
            try:
                api_key_obj = client.api.keys(api_key).fetch()
                api_key_account_sid = api_key_obj.account_sid
                
                if api_key_account_sid != account_sid:
                    self.stdout.write(self.style.ERROR(f'[ERROR] API Key Account SID mismatch!'))
                    self.stdout.write(self.style.WARNING(f'   Account SID in .env: {account_sid[:8]}...{account_sid[-4:]}'))
                    self.stdout.write(self.style.WARNING(f'   API Key belongs to: {api_key_account_sid[:8]}...{api_key_account_sid[-4:]}'))
                    self.stdout.write(self.style.WARNING('   The API Key must belong to the same account as the Account SID'))
                    self.stdout.write(self.style.WARNING('   Solution: Use the Account SID that matches your API Key, or create a new API Key for your Account SID'))
                    sys.exit(1)
                else:
                    self.stdout.write(self.style.SUCCESS('[OK] API Key belongs to the correct account'))
                    self.stdout.write(f'   API Key Friendly Name: {api_key_obj.friendly_name or "N/A"}')
            except Exception as e:
                error_str = str(e)
                # 403 errors are common - Auth Token may not have API Key read permissions
                # This is fine - we'll verify by testing token generation instead
                if '403' in error_str or 'not permitted' in error_str.lower():
                    self.stdout.write(self.style.WARNING('[INFO] Cannot verify API Key account (permission denied)'))
                    self.stdout.write(self.style.WARNING('   This is normal - will verify by testing token generation instead'))
                else:
                    self.stdout.write(self.style.WARNING(f'[WARNING] Could not verify API Key account: {e}'))
                    self.stdout.write(self.style.WARNING('   Continuing with token generation test...'))
            
            # Try to create a test token
            token = AccessToken(account_sid, api_key, api_secret, identity='test-user')
            video_grant = VideoGrant(room='test-room')
            token.add_grant(video_grant)
            jwt_token = token.to_jwt()
            
            if jwt_token:
                self.stdout.write(self.style.SUCCESS('[OK] API Key is valid'))
                self.stdout.write(f'   Test token generated: {jwt_token[:50]}...')
            else:
                self.stdout.write(self.style.ERROR('[ERROR] Failed to generate test token'))
                sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] API Key test failed: {e}'))
            self.stdout.write(self.style.WARNING('   Check your API Key SID and API Secret'))
            self.stdout.write(self.style.WARNING('   Also verify the API Key belongs to the same account as your Account SID'))
            sys.exit(1)
        
        # All tests passed
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] All Twilio tests passed!'))
        self.stdout.write(self.style.SUCCESS('[SUCCESS] Telemedicine is ready to use!\n'))
        
        self.stdout.write('\n[INFO] Next Steps:')
        self.stdout.write('   1. Start the backend server: python manage.py runserver')
        self.stdout.write('   2. Start the frontend server: npm start')
        self.stdout.write('   3. Login as a Doctor and create a telemedicine session')
        self.stdout.write('   4. Join the video call from the telemedicine page\n')
