"""
User serializers for authentication and user management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data (read-only for most fields)."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'is_superuser',
            'date_joined',
        ]
        read_only_fields = [
            'id',
            'date_joined',
        ]


class LoginSerializer(serializers.Serializer):
    """Serializer for login requests."""
    
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate credentials and check account lockout."""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError(
                "Username and password are required."
            )
        
        # Get user (don't authenticate yet)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid username or password."
            )
        
        # Check if account is locked
        if user.is_locked():
            raise serializers.ValidationError(
                "Account is locked due to multiple failed login attempts. "
                "Please try again later."
            )
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            # Record failed login attempt
            try:
                user_obj = User.objects.get(username=username)
                user_obj.record_failed_login()
            except User.DoesNotExist:
                pass
            
            raise serializers.ValidationError(
                "Invalid username or password."
            )
        
        if not user.is_active:
            # Friendlier message for staff accounts that are created but not yet approved
            if getattr(user, "role", None) and user.role != "PATIENT":
                raise serializers.ValidationError(
                    "Your staff account is awaiting admin approval. Please contact an administrator."
                )
            raise serializers.ValidationError(
                "User account is disabled."
            )
        
        # Record successful login
        user.record_successful_login()
        
        attrs['user'] = user
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refresh token requests."""
    
    refresh = serializers.CharField(required=True)


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'role',
        ]
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }
    
    def validate_username(self, value):
        """Check if username already exists."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        """Check if email already exists."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_role(self, value):
        """Validate role is one of the allowed choices."""
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation matches."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Password fields didn't match."
            })
        return attrs
    
    def create(self, validated_data):
        """Create new user with hashed password."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        role = validated_data.get('role')
        # By default, user.is_active is True for Django's AbstractUser. We override below.
        user = User.objects.create_user(password=password, **validated_data)
        
        # If user registered as PATIENT, create a Patient record linked to this user
        if role == 'PATIENT':
            from apps.patients.models import Patient
            
            # Create Patient record with basic information from user
            # patient_id will be auto-generated by Patient.clean() if not provided
            # is_verified=False by default - requires Receptionist verification
            patient = Patient(
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                user=user,
                is_active=True,
                is_verified=False  # Requires Receptionist verification
            )
            # Call clean() to generate patient_id, then save
            patient.clean()
            patient.save()
        else:
            # For all non-PATIENT roles (staff accounts), require explicit admin approval
            # before the account can be used. Admin enables the account via Django admin
            # or a staff-management UI by setting is_active=True.
            if user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
        
        return user
