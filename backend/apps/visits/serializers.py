"""
Visit serializers - visit management.

Per EMR Rules:
- Receptionist: Can create visits
- All roles: Can view visits (for clinical context)
- Doctor: Can close visits
"""
from rest_framework import serializers
from .models import Visit


class VisitSerializer(serializers.ModelSerializer):
    """
    Base serializer for Visit.
    """
    
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Visit
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_id',
            'visit_type',
            'chief_complaint',
            'appointment',
            'status',
            'payment_type',
            'payment_status',
            'closed_by',
            'closed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'closed_by',
            'closed_at',
            'created_at',
            'updated_at',
        ]
    
    def get_patient_name(self, obj):
        """Get patient's full name."""
        if obj.patient:
            return obj.patient.get_full_name()
        return None
    
    def get_patient_id(self, obj):
        """Get patient's ID."""
        if obj.patient:
            return obj.patient.patient_id
        return None


class VisitCreateSerializer(VisitSerializer):
    """
    Serializer for creating visits (Receptionist only).
    
    Receptionist provides:
    - patient (required - patient ID)
    - payment_type (optional, defaults to CASH) - CASH or INSURANCE
    - payment_status (optional, defaults based on payment_type)
    
    System sets:
    - status (defaults to OPEN)
    - payment_status (defaults to UNPAID for CASH, INSURANCE_PENDING for INSURANCE)
    - created_at, updated_at (auto)
    """
    
    payment_type = serializers.ChoiceField(
        choices=[('CASH', 'Cash Payment'), ('INSURANCE', 'Insurance/HMO')],
        default='CASH',
        required=False,
        help_text="Payment type: CASH or INSURANCE"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset dynamically to avoid circular import
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment
        
        self.fields['patient'] = serializers.PrimaryKeyRelatedField(
            queryset=Patient.objects.filter(is_active=True),
            help_text="Patient ID for this visit"
        )
        
        # Appointment field - optional, only show future or pending appointments
        self.fields['appointment'] = serializers.PrimaryKeyRelatedField(
            queryset=Appointment.objects.filter(
                status__in=['SCHEDULED', 'CONFIRMED']
            ),
            required=False,
            allow_null=True,
            help_text="Linked appointment (optional)"
        )
    
    def validate_patient(self, value):
        """Ensure patient exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot create visit for an inactive patient."
            )
        return value
    
    def validate(self, attrs):
        """Validate visit data and check for duplicates."""
        # Ensure patient is provided
        if 'patient' not in attrs:
            raise serializers.ValidationError(
                "Patient is required to create a visit."
            )
        
        # Auto-detect insurance: If patient has active insurance and payment_type not explicitly set,
        # automatically set payment_type to INSURANCE
        patient = attrs['patient']
        payment_type = attrs.get('payment_type')
        
        # Only auto-detect if payment_type is not explicitly provided (or is default CASH)
        if not payment_type or payment_type == 'CASH':
            from apps.billing.bill_models import InsurancePolicy
            from django.utils import timezone
            
            # Check if patient has active insurance policy
            active_insurance = InsurancePolicy.objects.filter(
                patient=patient,
                is_active=True
            ).first()
            
            # Check if insurance is still valid (valid_to is None or in the future)
            if active_insurance:
                today = timezone.now().date()
                is_valid = (
                    active_insurance.valid_from <= today and
                    (active_insurance.valid_to is None or active_insurance.valid_to >= today)
                )
                
                if is_valid:
                    # Patient has active, valid insurance - automatically set payment_type to INSURANCE
                    attrs['payment_type'] = 'INSURANCE'
        
        # Check for duplicate visit (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_visit_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            try:
                check_visit_duplicate(
                    patient=attrs['patient'],
                    visit_type=attrs.get('visit_type', 'CONSULTATION'),
                    visit_date=None  # Will default to today
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        
        return attrs


class VisitReadSerializer(VisitSerializer):
    """
    Serializer for reading visits.
    
    Includes patient details for clinical context.
    """
    patient_details = serializers.SerializerMethodField()
    patient_retainership = serializers.SerializerMethodField()
    
    class Meta(VisitSerializer.Meta):
        fields = list(VisitSerializer.Meta.fields) + ['patient_details', 'patient_retainership']
    
    def get_patient_details(self, obj):
        """Get patient details for consultation header."""
        if not obj.patient:
            return None
    
    def get_patient_retainership(self, obj):
        """Get patient retainership information."""
        if not obj.patient:
            return None
        
        from apps.patients.retainership_utils import get_retainership_info
        
        return get_retainership_info(obj.patient)
        
        try:
            patient = obj.patient
            return {
                'name': patient.get_full_name() or f"Patient #{patient.patient_id}",
                'age': patient.get_age() if patient.date_of_birth else None,
                'gender': patient.gender,
                'phone': patient.phone,
            }
        except Exception:
            # If patient data access fails, return None
            return None
