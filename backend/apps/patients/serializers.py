"""
Patient serializers - PHI data protection.

Per EMR Rules:
- Receptionist: Can create and search patients
- All fields are PHI - must be protected
- Data minimization: Only return necessary fields
"""
from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """
    Base serializer for Patient.
    
    All fields are PHI and must be protected.
    """
    
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    has_active_insurance = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_id',
            'first_name',
            'last_name',
            'middle_name',
            'full_name',
            'date_of_birth',
            'age',
            'gender',
            'phone',
            'email',
            'address',
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',
            'national_id',
            'blood_group',
            'allergies',
            'medical_history',
            'has_retainership',
            'retainership_type',
            'retainership_start_date',
            'retainership_end_date',
            'retainership_amount',
            'has_active_insurance',
            'portal_enabled',
            'is_active',
            'is_verified',
            'verified_by',
            'verified_at',
            'user',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'patient_id',
            'is_verified',
            'verified_by',
            'verified_at',
            'created_at',
            'updated_at',
        ]
    
    def get_full_name(self, obj):
        """Get patient's full name."""
        return obj.get_full_name()
    
    def get_age(self, obj):
        """Get patient's age."""
        return obj.get_age()
    
    def get_has_active_insurance(self, obj):
        """Check if patient has active insurance policy."""
        from apps.billing.bill_models import InsurancePolicy
        from django.utils import timezone
        
        active_insurance = InsurancePolicy.objects.filter(
            patient=obj,
            is_active=True
        ).first()
        
        if not active_insurance:
            return False
        
        # Check if insurance is still valid (valid_to is None or in the future)
        today = timezone.now().date()
        return (
            active_insurance.valid_from <= today and
            (active_insurance.valid_to is None or active_insurance.valid_to >= today)
        )


class PatientCreateSerializer(PatientSerializer):
    """
    Serializer for creating patients (Receptionist only).
    
    Receptionist provides:
    - first_name (required)
    - last_name (required)
    - middle_name (optional)
    - date_of_birth (optional)
    - gender (optional)
    - phone (optional)
    - email (optional)
    - address (optional)
    - national_id (optional, must be unique)
    - blood_group (optional)
    - allergies (optional)
    - medical_history (optional)
    - Insurance details (optional):
      - has_insurance (boolean)
      - insurance_provider_id (if has_insurance)
      - insurance_policy_number (if has_insurance)
      - insurance_coverage_type (if has_insurance)
      - insurance_coverage_percentage (if has_insurance)
      - insurance_valid_from (if has_insurance)
      - insurance_valid_to (if has_insurance, optional)
    - Retainership details (optional):
      - has_retainership (boolean)
      - retainership_type (if has_retainership)
      - retainership_start_date (if has_retainership)
      - retainership_end_date (if has_retainership, optional)
      - retainership_amount (if has_retainership)
    
    System sets:
    - patient_id (auto-generated if not provided)
    - is_active (defaults to True)
    """
    
    class Meta(PatientSerializer.Meta):
        # Include all fields from parent, plus insurance, retainership, and portal fields
        fields = PatientSerializer.Meta.fields + [
            'has_insurance',
            'insurance_provider_id',
            'insurance_policy_number',
            'insurance_coverage_type',
            'insurance_coverage_percentage',
            'insurance_valid_from',
            'insurance_valid_to',
            'has_retainership',
            'retainership_type',
            'retainership_start_date',
            'retainership_end_date',
            'retainership_amount',
            'create_portal_account',
            'portal_enabled',
            'portal_email',
            'portal_phone',
            'portal_created',
            'temporary_password',
        ]
        read_only_fields = PatientSerializer.Meta.read_only_fields + [
            'portal_created',
            'temporary_password',
        ]
    
    # patient_id is auto-generated, so it's read-only and not required
    patient_id = serializers.CharField(required=False, read_only=True)
    
    # Insurance fields (nested, optional)
    has_insurance = serializers.BooleanField(required=False, default=False, write_only=True)
    insurance_provider_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    insurance_policy_number = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    insurance_coverage_type = serializers.ChoiceField(
        choices=[('FULL', 'Full Coverage'), ('PARTIAL', 'Partial Coverage')],
        required=False,
        allow_null=True,
        write_only=True
    )
    insurance_coverage_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True
    )
    insurance_valid_from = serializers.DateField(required=False, allow_null=True, write_only=True)
    insurance_valid_to = serializers.DateField(required=False, allow_null=True, write_only=True)
    
    # Retainership fields (optional)
    has_retainership = serializers.BooleanField(required=False, default=False, write_only=True)
    retainership_type = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    retainership_start_date = serializers.DateField(required=False, allow_null=True, write_only=True)
    retainership_end_date = serializers.DateField(required=False, allow_null=True, write_only=True)
    retainership_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True
    )
    
    # Patient Portal fields (optional)
    create_portal_account = serializers.BooleanField(required=False, default=False, write_only=True)
    portal_enabled = serializers.BooleanField(required=False, default=False, write_only=True)
    portal_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True, write_only=True)
    portal_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    
    # Portal response fields (read-only, returned after creation)
    portal_created = serializers.BooleanField(read_only=True)
    temporary_password = serializers.CharField(read_only=True)
    
    def validate_national_id(self, value):
        """Ensure national_id is unique if provided."""
        if value:
            if Patient.objects.filter(national_id=value).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise serializers.ValidationError(
                    "A patient with this national ID already exists."
                )
        return value
    
    def validate(self, attrs):
        """Validate patient data."""
        # Ensure first_name and last_name are provided
        first_name = attrs.get('first_name', '').strip() if attrs.get('first_name') else ''
        last_name = attrs.get('last_name', '').strip() if attrs.get('last_name') else ''
        
        if not first_name or not last_name:
            raise serializers.ValidationError(
                "First name and last name are required."
            )
        
        # Validate insurance fields if has_insurance is True
        has_insurance = attrs.get('has_insurance', False)
        if has_insurance:
            if not attrs.get('insurance_provider_id'):
                raise serializers.ValidationError(
                    "Insurance provider is required when patient has insurance."
                )
            if not attrs.get('insurance_policy_number'):
                raise serializers.ValidationError(
                    "Insurance policy number is required when patient has insurance."
                )
            if not attrs.get('insurance_valid_from'):
                raise serializers.ValidationError(
                    "Insurance validity start date is required when patient has insurance."
                )
            # Set default coverage if not provided
            if not attrs.get('insurance_coverage_type'):
                attrs['insurance_coverage_type'] = 'FULL'
            if not attrs.get('insurance_coverage_percentage'):
                attrs['insurance_coverage_percentage'] = 100.00
        
        # Validate retainership fields if has_retainership is True
        has_retainership = attrs.get('has_retainership', False)
        if has_retainership:
            if not attrs.get('retainership_type'):
                raise serializers.ValidationError(
                    "Retainership type is required when patient has retainership."
                )
            if not attrs.get('retainership_start_date'):
                raise serializers.ValidationError(
                    "Retainership start date is required when patient has retainership."
                )
            if not attrs.get('retainership_amount'):
                raise serializers.ValidationError(
                    "Retainership amount is required when patient has retainership."
                )
        
        # Validate patient portal fields if create_portal_account is True
        create_portal_account = attrs.get('create_portal_account', False)
        if create_portal_account:
            portal_email = attrs.get('portal_email', '').strip() if attrs.get('portal_email') else ''
            if not portal_email:
                raise serializers.ValidationError(
                    "Email is required when creating a patient portal account."
                )
            
            # Validate email format
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, portal_email):
                raise serializers.ValidationError(
                    "Invalid email format for patient portal account."
                )
            
            # Check if email already used by another user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=portal_email).exists():
                raise serializers.ValidationError(
                    f"A portal account with email {portal_email} already exists."
                )
        
        # Check for duplicate patient (if creating new)
        if self.instance is None:
            from core.duplicate_prevention import check_patient_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            try:
                check_patient_duplicate(
                    first_name=attrs.get('first_name'),
                    last_name=attrs.get('last_name'),
                    date_of_birth=attrs.get('date_of_birth'),
                    phone=attrs.get('phone'),
                    email=attrs.get('email'),
                    national_id=attrs.get('national_id')
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        
        # Clean up empty strings - convert to None for optional fields
        optional_fields = [
            'middle_name', 'phone', 'email', 'address', 
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'national_id', 'allergies', 'medical_history',
            'insurance_policy_number', 'retainership_type'
        ]
        for field in optional_fields:
            if field in attrs and attrs[field] == '':
                attrs[field] = None
        
        # Clean up empty strings for date fields
        date_fields = ['date_of_birth', 'insurance_valid_from', 'insurance_valid_to', 
                      'retainership_start_date', 'retainership_end_date']
        for field in date_fields:
            if field in attrs and attrs[field] == '':
                attrs[field] = None
        
        # Clean up empty strings for gender and blood_group
        if 'gender' in attrs and attrs['gender'] == '':
            attrs['gender'] = None
        if 'blood_group' in attrs and attrs['blood_group'] == '':
            attrs['blood_group'] = None
        
        return attrs
    
    def create(self, validated_data):
        """Create patient with auto-generated patient_id and handle insurance/retainership/portal."""
        import logging
        from django.db import transaction
        from django.contrib.auth import get_user_model
        import secrets
        
        logger = logging.getLogger(__name__)
        User = get_user_model()
        
        # Extract insurance and retainership data (they're not Patient model fields)
        # Use .pop() with defaults to safely extract fields - these won't raise KeyError
        has_insurance = validated_data.pop('has_insurance', False)
        insurance_provider_id = validated_data.pop('insurance_provider_id', None)
        insurance_policy_number = validated_data.pop('insurance_policy_number', None)
        insurance_coverage_type = validated_data.pop('insurance_coverage_type', None)
        insurance_coverage_percentage = validated_data.pop('insurance_coverage_percentage', None)
        insurance_valid_from = validated_data.pop('insurance_valid_from', None)
        insurance_valid_to = validated_data.pop('insurance_valid_to', None)
        
        has_retainership = validated_data.pop('has_retainership', False)
        retainership_type = validated_data.pop('retainership_type', None)
        retainership_start_date = validated_data.pop('retainership_start_date', None)
        retainership_end_date = validated_data.pop('retainership_end_date', None)
        retainership_amount = validated_data.pop('retainership_amount', None)
        
        # Extract patient portal data
        create_portal_account = validated_data.pop('create_portal_account', False)
        portal_enabled = validated_data.pop('portal_enabled', False)
        portal_email = validated_data.pop('portal_email', None)
        portal_phone = validated_data.pop('portal_phone', None)
        
        # Variables to track portal account creation
        portal_created = False
        temporary_password = None
        portal_user = None
        
        # Generate patient_id if not provided
        if 'patient_id' not in validated_data or not validated_data.get('patient_id'):
            # Generate sequential patient ID in format LMC000001
            validated_data['patient_id'] = Patient.generate_patient_id()
        
        # Ensure is_active defaults to True
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        
        # Use atomic transaction to ensure all-or-nothing creation
        try:
            with transaction.atomic():
                logger.info(f"Creating patient with data: {list(validated_data.keys())}")
                
                # Create patient
                patient = super().create(validated_data)
                logger.info(f"Patient created successfully with ID: {patient.id}")
                
                # Create patient portal account if requested
                if create_portal_account and portal_email:
                    try:
                        # Generate secure temporary password (12 characters, URL-safe)
                        temporary_password = secrets.token_urlsafe(12)[:12]
                        
                        # Create portal user account
                        portal_user = User.objects.create_user(
                            username=portal_email.strip(),
                            email=portal_email.strip(),
                            password=temporary_password,
                            role='PATIENT',
                            patient=patient,
                            first_name=patient.first_name,
                            last_name=patient.last_name,
                            is_active=True
                        )
                        
                        # Enable portal on patient record
                        patient.portal_enabled = True
                        patient.save(update_fields=['portal_enabled'])
                        
                        portal_created = True
                        logger.info(f"Patient portal account created for patient {patient.id}, user {portal_user.id}")
                        
                    except Exception as e:
                        logger.error(f"Error creating portal account: {str(e)}", exc_info=True)
                        # Raise to rollback transaction
                        raise serializers.ValidationError(
                            f"Failed to create portal account: {str(e)}"
                        )
                
                # Set portal_enabled even if not creating account (for future creation)
                elif portal_enabled:
                    patient.portal_enabled = True
                    patient.save(update_fields=['portal_enabled'])
        
        except Exception as e:
            logger.error(f"Error in patient creation transaction: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise serializers.ValidationError(f"Failed to create patient: {str(e)}")
        
        # Create insurance policy if provided
        if has_insurance:
            if not insurance_provider_id or not insurance_policy_number or not insurance_valid_from:
                # Log warning but don't fail patient creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Patient {patient.id} marked as having insurance but required fields missing. "
                    f"provider_id={insurance_provider_id}, policy_number={insurance_policy_number}, valid_from={insurance_valid_from}"
                )
            else:
                from apps.billing.bill_models import InsuranceProvider, InsurancePolicy
                from decimal import Decimal
                
                try:
                    provider = InsuranceProvider.objects.get(pk=insurance_provider_id)
                    InsurancePolicy.objects.create(
                        patient=patient,
                        provider=provider,
                        policy_number=insurance_policy_number,
                        coverage_type=insurance_coverage_type or 'FULL',
                        coverage_percentage=Decimal(str(insurance_coverage_percentage)) if insurance_coverage_percentage else Decimal('100.00'),
                        valid_from=insurance_valid_from,
                        valid_to=insurance_valid_to,
                        is_active=True
                    )
                except InsuranceProvider.DoesNotExist:
                    # Log error but don't fail patient creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Insurance provider with ID {insurance_provider_id} does not exist.")
                    raise serializers.ValidationError(
                        f"Insurance provider with ID {insurance_provider_id} does not exist."
                    )
                except Exception as e:
                    # Log error but don't fail patient creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error creating insurance policy: {str(e)}", exc_info=True)
                    # Don't fail patient creation if insurance policy creation fails
                    # The patient is already created, we can add insurance later
                    pass
        
        # Set retainership fields if provided
        if has_retainership:
            from decimal import Decimal
            try:
                patient.has_retainership = True
                patient.retainership_type = retainership_type
                patient.retainership_start_date = retainership_start_date
                patient.retainership_end_date = retainership_end_date
                if retainership_amount:
                    patient.retainership_amount = Decimal(str(retainership_amount))
                patient.save(update_fields=[
                    'has_retainership', 'retainership_type', 'retainership_start_date',
                    'retainership_end_date', 'retainership_amount'
                ])
            except Exception as e:
                # Log error but don't fail patient creation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error setting retainership: {str(e)}", exc_info=True)
                # Don't fail patient creation if retainership setting fails
                pass
        
        # Add portal account info to patient instance for serializer response
        patient.portal_created = portal_created
        patient.temporary_password = temporary_password if portal_created else None
        
        return patient
    
    def to_representation(self, instance):
        """Add portal account info to response."""
        data = super().to_representation(instance)
        
        # Add portal creation info if available
        if hasattr(instance, 'portal_created'):
            data['portal_created'] = instance.portal_created
        else:
            data['portal_created'] = False
        
        # Only include temporary password if it was just created
        if hasattr(instance, 'temporary_password') and instance.temporary_password:
            data['temporary_password'] = instance.temporary_password
        
        return data


class PatientVerificationSerializer(serializers.ModelSerializer):
    """
    Serializer for patient verification (includes user info).
    Used for pending verification list.
    """
    full_name = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'is_verified',
            'verified_by',
            'verified_at',
            'user',
            'user_username',
            'user_email',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'patient_id',
            'is_verified',
            'verified_by',
            'verified_at',
            'created_at',
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_user_username(self, obj):
        return obj.user.username if obj.user else None
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


class PatientSearchSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for patient search results.
    
    Data minimization: Only return essential fields for search.
    """
    
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_id',
            'full_name',
            'age',
            'gender',
            'phone',
            'national_id',
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()
