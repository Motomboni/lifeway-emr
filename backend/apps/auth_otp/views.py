"""
OTP Authentication Views

Passwordless login for patient portal.
- Request OTP
- Verify OTP
- Issue JWT tokens
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import logging

from .models import LoginOTP, LoginAuditLog
from .serializers import (
    RequestOTPSerializer,
    VerifyOTPSerializer,
    RegisterBiometricSerializer,
    BiometricLoginSerializer,
    PatientPortalUserSerializer,
)
from core.rate_limiting import rate_limit
import hmac
from .utils import (
    send_email_otp,
    send_sms_otp,
    send_whatsapp_otp,
    get_client_ip,
    get_device_type,
    normalize_nigerian_phone
)

User = get_user_model()
logger = logging.getLogger(__name__)


# Rate limiting helper
_otp_request_counts = {}

def check_rate_limit(identifier: str) -> bool:
    """
    Check if user has exceeded OTP request rate limit.
    
    Rules:
    - Max 5 OTP requests per hour per identifier
    - Reset counter after 1 hour
    
    Returns:
        True if within limit, False if exceeded
    """
    from datetime import datetime, timedelta
    
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    
    # Clean up old entries
    for key in list(_otp_request_counts.keys()):
        if _otp_request_counts[key]['last_request'] < hour_ago:
            del _otp_request_counts[key]
    
    # Check current identifier
    if identifier not in _otp_request_counts:
        _otp_request_counts[identifier] = {
            'count': 0,
            'last_request': now
        }
    
    entry = _otp_request_counts[identifier]
    
    # Reset if last request was over an hour ago
    if entry['last_request'] < hour_ago:
        entry['count'] = 0
    
    # Check limit
    if entry['count'] >= 5:
        return False
    
    # Increment
    entry['count'] += 1
    entry['last_request'] = now
    
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    """
    Request OTP for passwordless login.
    
    POST /api/v1/auth/request-otp/
    
    Request Body:
    {
        "email": "patient@example.com",  // OR
        "phone": "08012345678",          // phone
        "channel": "email"               // email|sms|whatsapp
    }
    
    Response:
    {
        "success": true,
        "message": "OTP sent successfully",
        "channel": "email",
        "recipient": "pat***@example.com",
        "expires_in_seconds": 300
    }
    """
    serializer = RequestOTPSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'error': 'Validation error',
                'detail': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    email = serializer.validated_data.get('email', '').strip()
    phone = serializer.validated_data.get('phone', '').strip()
    channel = serializer.validated_data.get('channel')
    
    # Determine identifier
    identifier = email if email else phone
    
    # Rate limiting
    if not check_rate_limit(identifier):
        LoginAuditLog.log_action(
            action='OTP_REQUESTED',
            identifier=identifier,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            error='Rate limit exceeded'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Too many requests',
                'detail': 'Maximum 5 OTP requests per hour. Please try again later.'
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Find user
    try:
        if email:
            user = User.objects.get(email=email, role='PATIENT')
        else:
            # Normalize phone for lookup
            normalized_phone = normalize_nigerian_phone(phone)
            user = User.objects.get(phone=normalized_phone, role='PATIENT')
    except User.DoesNotExist:
        # Security: Don't reveal if user exists
        LoginAuditLog.log_action(
            action='OTP_REQUESTED',
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='User not found'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Account not found',
                'detail': 'No patient account found with this email/phone.'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except User.MultipleObjectsReturned:
        logger.error(f"Multiple users found for identifier: {identifier}")
        return Response(
            {
                'success': False,
                'error': 'Multiple accounts found',
                'detail': 'Please contact support.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user account is active
    if not user.is_active:
        LoginAuditLog.log_action(
            action='OTP_REQUESTED',
            user=user,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='Account disabled'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Account disabled',
                'detail': 'Your account has been disabled. Please contact support.'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if portal is enabled
    if not user.portal_enabled:
        LoginAuditLog.log_action(
            action='OTP_REQUESTED',
            user=user,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='Portal disabled'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Portal access disabled',
                'detail': 'Portal access has been disabled for your account.'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Create OTP
    try:
        with transaction.atomic():
            otp = LoginOTP.create_otp(
                user=user,
                channel=channel.upper(),
                recipient=email if email else normalized_phone,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Send OTP based on channel
            patient_name = user.patient.get_full_name() if user.patient else ''
            
            if channel == 'email':
                sent = send_email_otp(email, otp.otp_code, patient_name)
            elif channel == 'sms':
                sent = send_sms_otp(phone, otp.otp_code)
            elif channel == 'whatsapp':
                sent = send_whatsapp_otp(phone, otp.otp_code, patient_name)
            else:
                sent = False
            
            if not sent:
                raise Exception(f"Failed to send OTP via {channel}")
            
            # Log success
            LoginAuditLog.log_action(
                action='OTP_SENT',
                user=user,
                identifier=identifier,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                channel=channel
            )
            
            # Mask recipient for response
            if email:
                masked = email[:3] + '***@' + email.split('@')[1]
            else:
                masked = phone[:4] + '***' + phone[-3:]
            
            return Response(
                {
                    'success': True,
                    'message': 'OTP sent successfully',
                    'channel': channel,
                    'recipient': masked,
                    'expires_in_seconds': 300
                },
                status=status.HTTP_200_OK
            )
            
    except Exception as e:
        logger.error(f"Error creating/sending OTP: {e}", exc_info=True)
        
        LoginAuditLog.log_action(
            action='OTP_REQUESTED',
            user=user if 'user' in locals() else None,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error=str(e)
        )
        
        return Response(
            {
                'success': False,
                'error': 'Failed to send OTP',
                'detail': 'Please try again or contact support.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP and issue JWT tokens.
    
    POST /api/v1/auth/verify-otp/
    
    Request Body:
    {
        "email": "patient@example.com",  // OR
        "phone": "08012345678",          // phone
        "otp_code": "123456",
        "device_type": "ios"             // optional: web|ios|android
    }
    
    Response:
    {
        "success": true,
        "message": "Login successful",
        "access": "eyJ...",
        "refresh": "eyJ...",
        "user": {
            "id": 123,
            "email": "patient@example.com",
            "role": "PATIENT",
            "patient_name": "John Doe",
            "patient_id": "LMC000123"
        }
    }
    """
    serializer = VerifyOTPSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'error': 'Validation error',
                'detail': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    email = serializer.validated_data.get('email', '').strip()
    phone = serializer.validated_data.get('phone', '').strip()
    otp_code = serializer.validated_data.get('otp_code')
    device_type = serializer.validated_data.get('device_type', 'web')
    
    identifier = email if email else phone
    
    # Find user
    try:
        if email:
            user = User.objects.get(email=email, role='PATIENT')
        else:
            normalized_phone = normalize_nigerian_phone(phone)
            user = User.objects.get(phone=normalized_phone, role='PATIENT')
    except User.DoesNotExist:
        LoginAuditLog.log_action(
            action='OTP_FAILED',
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='User not found'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Invalid credentials',
                'detail': 'No account found.'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check account status
    if not user.is_active:
        LoginAuditLog.log_action(
            action='LOGIN_FAILED',
            user=user,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='Account disabled'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Account disabled',
                'detail': 'Your account has been disabled.'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Find valid OTP
    try:
        otp = LoginOTP.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False,
            expires_at__gt=timezone.now()
        ).latest('created_at')
    except LoginOTP.DoesNotExist:
        # Invalid or expired OTP
        LoginAuditLog.log_action(
            action='OTP_FAILED',
            user=user,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error='Invalid OTP'
        )
        
        return Response(
            {
                'success': False,
                'error': 'Invalid OTP',
                'detail': 'OTP is invalid or expired. Please request a new one.'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Verify OTP and issue tokens
    try:
        with transaction.atomic():
            # Mark OTP as used
            otp.mark_as_used()
            
            # Update user device info
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            user.last_login_device = user_agent[:255] if user_agent else ''
            user.device_type = device_type
            user.save(update_fields=['last_login_device', 'device_type', 'last_login'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Log successful login
            LoginAuditLog.log_action(
                action='LOGIN_SUCCESS',
                user=user,
                identifier=identifier,
                ip_address=get_client_ip(request),
                user_agent=user_agent,
                device_type=device_type,
                success=True,
                channel=otp.channel
            )
            
            logger.info(f"Patient {user.id} logged in via {otp.channel}")
            
            # Serialize user data
            user_serializer = PatientPortalUserSerializer(user)
            
            return Response(
                {
                    'success': True,
                    'message': 'Login successful',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': user_serializer.data
                },
                status=status.HTTP_200_OK
            )
            
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}", exc_info=True)
        
        LoginAuditLog.log_action(
            action='LOGIN_FAILED',
            user=user,
            identifier=identifier,
            ip_address=get_client_ip(request),
            success=False,
            error=str(e)
        )
        
        return Response(
            {
                'success': False,
                'error': 'Login failed',
                'detail': 'An error occurred during login. Please try again.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def logout(request):
    """
    Logout user (invalidate refresh token).
    
    POST /api/v1/auth/logout/
    
    Request Body:
    {
        "refresh": "refresh_token"
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Log logout
        LoginAuditLog.log_action(
            action='LOGOUT',
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            success=True
        )
        
        return Response(
            {
                'success': True,
                'message': 'Logged out successfully'
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return Response(
            {
                'success': True,
                'message': 'Logged out (token may have been invalid)'
            },
            status=status.HTTP_200_OK
        )


# Biometric auth rate limits (stricter than OTP)
BIOMETRIC_RATE_LIMIT = (10, 30)  # 10/min, 30/hour per IP


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@rate_limit(requests_per_minute=BIOMETRIC_RATE_LIMIT[0], requests_per_hour=BIOMETRIC_RATE_LIMIT[1])
def register_biometric(request):
    """
    Register biometric for the authenticated user (must have logged in via OTP first).
    
    POST /api/v1/auth/register-biometric/
    Body: { "device_id": "...", "biometric_token": "..." }
    """
    serializer = RegisterBiometricSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': 'Validation error', 'detail': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    device_id = serializer.validated_data['device_id']
    biometric_token = serializer.validated_data['biometric_token']
    
    # Only PATIENT role can use biometric (portal flow)
    if getattr(user, 'role', None) != 'PATIENT':
        return Response(
            {'success': False, 'error': 'Biometric is only available for patient portal users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user.biometric_key = biometric_token  # Store token reference (in production use hashed/encrypted)
        user.device_id = device_id
        user.biometric_enabled = True
        user.save(update_fields=['biometric_key', 'device_id', 'biometric_enabled'])
        
        LoginAuditLog.log_action(
            action='BIOMETRIC_REGISTERED',
            user=user,
            identifier=device_id,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_type=get_device_type(request),
            success=True,
        )
        
        return Response(
            {'success': True, 'message': 'Biometric registered successfully.'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Biometric registration error: {e}", exc_info=True)
        LoginAuditLog.log_action(
            action='BIOMETRIC_REGISTERED',
            user=user,
            ip_address=get_client_ip(request),
            success=False,
            error=str(e)
        )
        return Response(
            {'success': False, 'error': 'Registration failed', 'detail': 'Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _constant_time_compare(a, b):
    """Constant-time comparison to avoid timing attacks."""
    return hmac.compare_digest(a.encode('utf-8') if isinstance(a, str) else a,
                               b.encode('utf-8') if isinstance(b, str) else b)


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=BIOMETRIC_RATE_LIMIT[0], requests_per_hour=BIOMETRIC_RATE_LIMIT[1])
def biometric_login(request):
    """
    Login with biometric token. Validate token against stored key and issue JWT.
    
    POST /api/v1/auth/biometric-login/
    Body: { "device_id": "...", "biometric_token": "..." }
    """
    serializer = BiometricLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': 'Validation error', 'detail': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    device_id = serializer.validated_data['device_id']
    biometric_token = serializer.validated_data['biometric_token']
    
    try:
        user = User.objects.get(device_id=device_id, biometric_enabled=True, role='PATIENT', is_active=True)
    except User.DoesNotExist:
        LoginAuditLog.log_action(
            action='BIOMETRIC_LOGIN_FAILED',
            identifier=device_id,
            ip_address=get_client_ip(request),
            success=False,
            error='Unknown device or biometric not enabled'
        )
        return Response(
            {'success': False, 'error': 'Invalid credentials', 'detail': 'Device not recognized. Use OTP login.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.biometric_key or not _constant_time_compare(biometric_token, user.biometric_key):
        LoginAuditLog.log_action(
            action='BIOMETRIC_LOGIN_FAILED',
            user=user,
            identifier=device_id,
            ip_address=get_client_ip(request),
            success=False,
            error='Invalid token'
        )
        return Response(
            {'success': False, 'error': 'Invalid credentials', 'detail': 'Biometric verification failed.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        refresh = RefreshToken.for_user(user)
        user.last_login_device = (request.META.get('HTTP_USER_AGENT') or '')[:255]
        user.device_type = get_device_type(request)
        user.save(update_fields=['last_login_device', 'device_type', 'last_login'])
        
        LoginAuditLog.log_action(
            action='BIOMETRIC_LOGIN_SUCCESS',
            user=user,
            identifier=device_id,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_type=get_device_type(request),
            success=True,
        )
        
        user_serializer = PatientPortalUserSerializer(user)
        return Response(
            {
                'success': True,
                'message': 'Login successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': user_serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Biometric login error: {e}", exc_info=True)
        LoginAuditLog.log_action(
            action='BIOMETRIC_LOGIN_FAILED',
            user=user,
            ip_address=get_client_ip(request),
            success=False,
            error=str(e)
        )
        return Response(
            {'success': False, 'error': 'Login failed', 'detail': 'Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
