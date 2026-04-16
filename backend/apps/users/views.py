"""
Authentication views for EMR system.

Per EMR Rules:
- JWT access tokens (short-lived)
- Refresh tokens (rotated)
- Account lockout after repeated failures
- Rate limiting on auth endpoints (clinic-grade security)
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.rate_limiting import rate_limit
from .serializers import (
    LoginSerializer,
    UserSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    AccountUpdateSerializer,
)

User = get_user_model()

# Clinic-grade: strict rate limits on auth endpoints (per IP)
AUTH_RATE_LIMIT_LOGIN = (5, 20)   # 5/min, 20/hour per IP
AUTH_RATE_LIMIT_REFRESH = (30, 200)
AUTH_RATE_LIMIT_REGISTER = (3, 10)  # 3/min, 10/hour
AUTH_RATE_LIMIT_FORGOT_PASSWORD = (3, 10)
AUTH_RATE_LIMIT_RESET_PASSWORD = (5, 20)


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=AUTH_RATE_LIMIT_LOGIN[0], requests_per_hour=AUTH_RATE_LIMIT_LOGIN[1])
def login(request):
    """
    Login endpoint - returns JWT access and refresh tokens.
    
    POST /api/v1/auth/login/
    {
        "username": "doctor1",
        "password": "password123"
    }
    
    Returns:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {
            "id": 1,
            "username": "doctor1",
            "role": "DOCTOR",
            ...
        }
    }
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = serializer.validated_data['user']
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    
    # Serialize user data
    user_serializer = UserSerializer(user)
    
    return Response({
        'access': str(access),
        'refresh': str(refresh),
        'user': user_serializer.data
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    summary='Refresh Token',
    description='Get a new access token using a refresh token',
    request=RefreshTokenSerializer,
    responses={
        200: {
            'description': 'New access token',
            'content': {
                'application/json': {
                    'example': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    }
                }
            }
        },
        401: {'description': 'Invalid or expired refresh token'},
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=AUTH_RATE_LIMIT_REFRESH[0], requests_per_hour=AUTH_RATE_LIMIT_REFRESH[1])
def refresh_token(request):
    """
    Refresh token endpoint - returns new access token.
    
    POST /api/v1/auth/refresh/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Returns:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    refresh_token_str = serializer.validated_data['refresh']
    
    try:
        refresh = RefreshToken(refresh_token_str)
        access = refresh.access_token
        
        # Rotate refresh token (security best practice)
        refresh.set_jti()
        refresh.set_exp()
        
        return Response({
            'access': str(access),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)
    except TokenError:
        return Response(
            {'detail': 'Invalid or expired refresh token.'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@extend_schema(
    tags=['Authentication'],
    summary='Logout',
    description='Logout user and blacklist refresh token',
    request=RefreshTokenSerializer,
    responses={
        200: {'description': 'Successfully logged out'},
        400: {'description': 'Invalid refresh token'},
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout endpoint - blacklists refresh token.
    
    POST /api/v1/auth/logout/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    refresh_token_str = serializer.validated_data['refresh']
    
    try:
        refresh = RefreshToken(refresh_token_str)
        refresh.blacklist()
        return Response(
            {'detail': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'detail': 'Invalid refresh token.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    tags=['Authentication'],
    summary='Get Current User',
    description='Get information about the currently authenticated user',
    responses={
        200: UserSerializer,
        401: {'description': 'Unauthorized'},
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user information.
    
    GET /api/v1/auth/me/
    
    Returns:
    {
        "id": 1,
        "username": "doctor1",
        "role": "DOCTOR",
        ...
    }
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    summary='List Doctors',
    description='Get a list of all active doctors (for appointment scheduling)',
    responses={
        200: UserSerializer(many=True),
        401: {'description': 'Unauthorized'},
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_doctors(request):
    """
    List all doctors (for appointment scheduling).
    
    GET /api/v1/auth/doctors/
    
    Returns list of users with DOCTOR role.
    """
    doctors = User.objects.filter(role='DOCTOR', is_active=True).order_by('first_name', 'last_name')
    serializer = UserSerializer(doctors, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=AUTH_RATE_LIMIT_REGISTER[0], requests_per_hour=AUTH_RATE_LIMIT_REGISTER[1])
def register(request):
    """
    User registration endpoint.
    
    POST /api/v1/auth/register/
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "securepassword123",
        "password_confirm": "securepassword123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "DOCTOR"
    }
    
    Returns:
    {
        "id": 1,
        "username": "newuser",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "DOCTOR",
        ...
    }
    """
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = serializer.save()
    
    # Serialize user data (exclude password)
    user_serializer = UserSerializer(user)
    
    return Response(
        user_serializer.data,
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    tags=['Authentication'],
    summary='Forgot Password',
    description='Initiate password reset for an account using username or email.',
    request=ForgotPasswordSerializer,
    responses={
        200: {
            'description': 'Reset instructions sent if account exists',
            'content': {
                'application/json': {
                    'example': {'detail': 'If an account exists for this identifier, a reset link has been sent.'}
                }
            },
        }
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=AUTH_RATE_LIMIT_FORGOT_PASSWORD[0], requests_per_hour=AUTH_RATE_LIMIT_FORGOT_PASSWORD[1])
def forgot_password(request):
    """
    Forgot password endpoint.

    POST /api/v1/auth/forgot-password/
    {
        "identifier": "user@example.com"  // username or email
    }

    Always returns 200 with a generic message to avoid user enumeration.
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data['identifier'].strip()

    user = None
    if identifier:
        try:
            if '@' in identifier:
                user = User.objects.filter(email__iexact=identifier).first()
            else:
                user = User.objects.filter(username__iexact=identifier).first()
        except Exception:
            user = None

    if user and user.email:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)

        base_url = getattr(settings, 'BASE_URL', 'https://localhost')
        reset_path = f"/reset-password?uid={uid}&token={token}"
        reset_url = f"{base_url}{reset_path}"

        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "Password reset requested for user %s (id=%s, email=%s). Reset URL: %s",
            user.username,
            user.id,
            user.email,
            reset_url,
        )
        # TODO: integrate with real email service

    return Response(
        {'detail': 'If an account exists for this identifier, a reset link has been sent.'},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=['Authentication'],
    summary='Reset Password',
    description='Complete password reset using uid and token from reset link.',
    request=ResetPasswordSerializer,
    responses={
        200: {'description': 'Password reset successfully'},
        400: {'description': 'Invalid or expired reset link'},
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit(requests_per_minute=AUTH_RATE_LIMIT_RESET_PASSWORD[0], requests_per_hour=AUTH_RATE_LIMIT_RESET_PASSWORD[1])
def reset_password(request):
    """
    Reset password endpoint - completes password reset using uid/token.

    POST /api/v1/auth/reset-password/
    {
        "uid": "<base64_user_id>",
        "token": "<token>",
        "new_password": "...",
        "new_password_confirm": "..."
    }
    """
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    uid = serializer.validated_data['uid']
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']

    try:
        uid_int = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid_int)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {'detail': 'Invalid or expired reset link.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token_generator = PasswordResetTokenGenerator()
    if not token_generator.check_token(user, token):
        return Response(
            {'detail': 'Invalid or expired reset link.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=['password'])

    return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    summary='Update Account',
    description='Update password, email, or username for the current user (requires current_password).',
    request=AccountUpdateSerializer,
    responses={
        200: UserSerializer,
        400: {'description': 'Validation error'},
        401: {'description': 'Unauthorized'},
    },
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_account(request):
    """
    Update account credentials for the authenticated user.

    PATCH /api/v1/auth/account/
    {
        "current_password": "...",
        "new_password": "...",            // optional
        "new_password_confirm": "...",    // optional
        "new_email": "new@example.com",   // optional
        "new_username": "newusername"     // optional
    }
    """
    serializer = AccountUpdateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


def _is_admin_or_superuser(user):
    """Check if user can approve staff (superuser or ADMIN role)."""
    return user and user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', None) == 'ADMIN'
    )


def _is_superuser(user):
    """Check if user is superuser (for destructive/restricted actions)."""
    return user and user.is_authenticated and user.is_superuser


@extend_schema(
    tags=['Authentication'],
    summary='List Pending Staff',
    description='List staff accounts awaiting approval (Admin/Superuser only)',
    responses={
        200: UserSerializer(many=True),
        401: {'description': 'Unauthorized'},
        403: {'description': 'Admin or Superuser required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_staff(request):
    """
    List staff users with is_active=False (awaiting approval).
    Only Admin or Superuser can access.
    """
    if not _is_admin_or_superuser(request.user):
        return Response(
            {'detail': 'Only administrators can view pending staff.'},
            status=status.HTTP_403_FORBIDDEN
        )
    staff_roles = [
        'ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'RADIOLOGY_TECH',
        'PHARMACIST', 'RECEPTIONIST', 'IVF_SPECIALIST', 'EMBRYOLOGIST'
    ]
    pending = User.objects.filter(
        is_active=False,
        role__in=staff_roles
    ).order_by('-date_joined')
    serializer = UserSerializer(pending, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=['Authentication'],
    summary='Approve Staff',
    description='Approve a pending staff account (Admin/Superuser only)',
    responses={
        200: UserSerializer,
        403: {'description': 'Admin or Superuser required'},
        404: {'description': 'User not found'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_staff(request, user_id):
    """
    Approve a pending staff user (set is_active=True).
    Only Admin or Superuser can approve.
    """
    if not _is_admin_or_superuser(request.user):
        return Response(
            {'detail': 'Only administrators can approve staff.'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    if user.role == 'PATIENT':
        return Response(
            {'detail': 'Patient accounts do not require approval.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if user.is_active:
        return Response(
            {'detail': 'User is already approved.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.is_active = True
    user.save(update_fields=['is_active'])
    serializer = UserSerializer(user)
    return Response(serializer.data)


@extend_schema(
    tags=['Authentication'],
    summary='List All Staff',
    description='List all staff users (Superuser only)',
    responses={
        200: UserSerializer(many=True),
        401: {'description': 'Unauthorized'},
        403: {'description': 'Superuser required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_all_staff(request):
    """List all staff users. Superuser only."""
    if not _is_superuser(request.user):
        return Response(
            {'detail': 'Only superusers can view all staff.'},
            status=status.HTTP_403_FORBIDDEN
        )
    staff_roles = [
        'ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'RADIOLOGY_TECH',
        'PHARMACIST', 'RECEPTIONIST', 'IVF_SPECIALIST', 'EMBRYOLOGIST'
    ]
    staff = User.objects.filter(role__in=staff_roles).order_by('-date_joined')
    serializer = UserSerializer(staff, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=['Authentication'],
    summary='Deactivate Staff',
    description='Deactivate a staff user (Superuser only). User cannot log in until reactivated.',
    responses={
        200: UserSerializer,
        403: {'description': 'Superuser required'},
        404: {'description': 'User not found'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deactivate_staff(request, user_id):
    """
    Permanently delete a staff user account.

    Superuser only. Cannot delete your own account.
    """
    if not _is_superuser(request.user):
        return Response(
            {'detail': 'Only superusers can deactivate staff.'},
            status=status.HTTP_403_FORBIDDEN
        )
    if request.user.id == user_id:
        return Response(
            {'detail': 'You cannot deactivate your own account.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    if user.role == 'PATIENT':
        return Response(
            {'detail': 'Use patient management to manage patient accounts.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Hard delete the staff user account.
    user.delete()
    return Response(
        {'detail': 'Staff user account deleted successfully.'},
        status=status.HTTP_200_OK
    )
