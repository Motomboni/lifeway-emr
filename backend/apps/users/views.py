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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.rate_limiting import rate_limit
from .serializers import LoginSerializer, UserSerializer, RefreshTokenSerializer, RegisterSerializer

User = get_user_model()

# Clinic-grade: strict rate limits on auth endpoints (per IP)
AUTH_RATE_LIMIT_LOGIN = (5, 20)   # 5/min, 20/hour per IP
AUTH_RATE_LIMIT_REFRESH = (30, 200)
AUTH_RATE_LIMIT_REGISTER = (3, 10)  # 3/min, 10/hour


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
    """Deactivate a staff user. Superuser only. Cannot deactivate yourself."""
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
            {'detail': 'Use patient management to deactivate patient accounts.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not user.is_active:
        return Response(
            {'detail': 'User is already deactivated.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.is_active = False
    user.save(update_fields=['is_active'])
    serializer = UserSerializer(user)
    return Response(serializer.data)
