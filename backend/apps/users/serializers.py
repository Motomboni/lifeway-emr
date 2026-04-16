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
    """Serializer for login requests. Accepts username or email."""
    
    username = serializers.CharField(required=True, help_text="Username or email")
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate credentials and check account lockout."""
        username_or_email = attrs.get('username', '').strip()
        password = attrs.get('password')
        
        if not username_or_email or not password:
            raise serializers.ValidationError(
                "Username and password are required."
            )
        
        # Allow login with username or email
        username = username_or_email
        try:
            if '@' in username_or_email:
                user = User.objects.get(email__iexact=username_or_email)
                username = user.username
            else:
                user = User.objects.get(username=username_or_email)
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
            # before the account can be used. Admin approves via Dashboard or Django admin.
            if user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
        
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for initiating password reset via email or username."""

    identifier = serializers.CharField(
        required=True,
        help_text="Username or email for the account requesting a password reset"
    )


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for completing password reset using uid/token."""

    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Password fields didn't match."
            })
        return attrs


class AccountUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating account credentials (authenticated user).

    Supports changing password/email/username with current_password verification.
    """

    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Current password required to change account details",
    )
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={'input_type': 'password'},
    )
    new_email = serializers.EmailField(required=False, allow_blank=False)
    new_username = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        """
        Ensure:
        - At least one of new_password/new_email/new_username is provided
        - Password confirmation matches when provided
        """
        has_password_change = bool(attrs.get('new_password') or attrs.get('new_password_confirm'))
        has_email_change = 'new_email' in attrs
        has_username_change = 'new_username' in attrs

        if not (has_password_change or has_email_change or has_username_change):
            raise serializers.ValidationError(
                "No changes provided. Specify at least one of new_password, new_email, or new_username."
            )

        if attrs.get('new_password') or attrs.get('new_password_confirm'):
            if not attrs.get('new_password') or not attrs.get('new_password_confirm'):
                raise serializers.ValidationError(
                    {"new_password_confirm": "Both new_password and new_password_confirm are required."}
                )
            if attrs['new_password'] != attrs['new_password_confirm']:
                raise serializers.ValidationError(
                    {"new_password_confirm": "Password fields didn't match."}
                )

        return attrs

    def validate_new_email(self, value: str) -> str:
        user = self.context['request'].user
        if value and User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_new_username(self, value: str) -> str:
        user = self.context['request'].user
        if value and User.objects.filter(username__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def save(self, **kwargs):
        """
        Apply changes to the authenticated user instance.
        """
        user: User = self.context['request'].user
        current_password = self.validated_data['current_password']

        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )

        updated_fields = []

        new_email = self.validated_data.get('new_email')
        if new_email:
            user.email = new_email
            updated_fields.append('email')

        new_username = self.validated_data.get('new_username')
        if new_username:
            user.username = new_username
            updated_fields.append('username')

        new_password = self.validated_data.get('new_password')
        if new_password:
            user.set_password(new_password)
            # Password is saved via set_password; include it explicitly
            updated_fields.append('password')

        if updated_fields:
            user.save(update_fields=updated_fields)

        return user
