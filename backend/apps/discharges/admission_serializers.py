"""
Serializers for Admission, Ward, and Bed models.
"""
from rest_framework import serializers
from .admission_models import Ward, Bed, Admission
from apps.visits.models import Visit
from apps.consultations.models import Consultation


class WardSerializer(serializers.ModelSerializer):
    """Serializer for Ward model."""
    available_beds_count = serializers.IntegerField(read_only=True)
    occupied_beds_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Ward
        fields = [
            'id', 'name', 'code', 'description', 'capacity',
            'is_active', 'available_beds_count', 'occupied_beds_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BedSerializer(serializers.ModelSerializer):
    """Serializer for Bed model."""
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    ward_code = serializers.CharField(source='ward.code', read_only=True)
    
    class Meta:
        model = Bed
        fields = [
            'id', 'ward', 'ward_name', 'ward_code', 'bed_number',
            'bed_type', 'is_available', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BedListSerializer(serializers.ModelSerializer):
    """Simplified serializer for bed lists."""
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    
    class Meta:
        model = Bed
        fields = ['id', 'ward', 'ward_name', 'bed_number', 'bed_type', 'is_available']


class AdmissionSerializer(serializers.ModelSerializer):
    """Serializer for Admission model."""
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    ward_code = serializers.CharField(source='ward.code', read_only=True)
    bed_number = serializers.CharField(source='bed.bed_number', read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.CharField(source='visit.patient.patient_id', read_only=True)
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    admitting_doctor_name = serializers.SerializerMethodField()
    length_of_stay_days = serializers.SerializerMethodField()
    
    def get_patient_name(self, obj):
        """Get patient's full name."""
        if obj.visit and obj.visit.patient:
            patient = obj.visit.patient
            if patient.first_name or patient.last_name:
                return f"{patient.first_name or ''} {patient.last_name or ''}".strip()
            return patient.patient_id or 'Unknown'
        return 'Unknown'
    
    def get_admitting_doctor_name(self, obj):
        """Get admitting doctor's full name."""
        if obj.admitting_doctor:
            doctor = obj.admitting_doctor
            if doctor.first_name or doctor.last_name:
                return f"{doctor.first_name or ''} {doctor.last_name or ''}".strip()
            return doctor.username or 'Unknown'
        return 'Unknown'
    
    def get_length_of_stay_days(self, obj):
        """Calculate length of stay in days."""
        if obj.admission_date:
            from django.utils import timezone
            end_date = obj.discharge_date if obj.discharge_date else timezone.now()
            delta = end_date - obj.admission_date
            return delta.days
        return 0
    
    class Meta:
        model = Admission
        fields = [
            'id', 'visit', 'visit_id', 'ward', 'ward_name', 'ward_code',
            'bed', 'bed_number', 'admission_type', 'admission_source',
            'admission_date', 'admission_status', 'discharge_date',
            'discharge_summary', 'admitting_doctor', 'admitting_doctor_name',
            'chief_complaint', 'admission_notes', 'transferred_from',
            'patient_name', 'patient_id', 'length_of_stay_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'discharge_date', 'discharge_summary', 'transferred_from',
            'created_at', 'updated_at'
        ]


class AdmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new admissions."""
    
    class Meta:
        model = Admission
        fields = [
            'ward', 'bed', 'admission_type', 'admission_source',
            'admission_date', 'chief_complaint', 'admission_notes'
        ]
        # Note: 'visit' is set by the view, not from request data
    
    def validate_bed(self, value):
        """Ensure bed exists and is available."""
        # value should be a Bed object (DRF converts ID to object automatically)
        if not isinstance(value, Bed):
            # If it's still an ID, try to get the object
            try:
                value = Bed.objects.get(pk=value)
            except Bed.DoesNotExist:
                raise serializers.ValidationError("Selected bed does not exist.")
        
        if not value.is_available:
            raise serializers.ValidationError(f"Bed {value.bed_number} is not available.")
        
        if not value.is_active:
            raise serializers.ValidationError(f"Bed {value.bed_number} is not active.")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        ward = attrs.get('ward')
        bed = attrs.get('bed')
        
        if ward and bed:
            if bed.ward_id != ward.id:
                raise serializers.ValidationError({
                    'bed': "Bed must belong to the selected ward."
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create admission and mark bed as unavailable."""
        from django.db import transaction
        
        # Get visit - it may be passed via save() keyword argument or in validated_data
        visit = validated_data.get('visit')
        if not visit:
            # Try to get from context if not in validated_data
            visit = self.context.get('visit')
        
        if not visit:
            raise serializers.ValidationError("Visit is required for admission.")
        
        bed = validated_data.get('bed')
        if not bed:
            raise serializers.ValidationError("Bed is required for admission.")
        
        # Ensure visit has a consultation
        if not Consultation.objects.filter(visit=visit).exists():
            raise serializers.ValidationError(
                "Visit must have at least one consultation before admission."
            )
        
        # Use database transaction with row-level locking to prevent race conditions
        with transaction.atomic():
            # Lock the bed row to prevent concurrent allocations
            try:
                bed = Bed.objects.select_for_update().get(pk=bed.pk)
            except Bed.DoesNotExist:
                raise serializers.ValidationError("Selected bed does not exist.")
            
            # Double-check bed is still available (race condition protection)
            if not bed.is_available:
                raise serializers.ValidationError(
                    f"Bed {bed.bed_number} is no longer available. It may have been allocated to another patient."
                )
            
            if not bed.is_active:
                raise serializers.ValidationError(
                    f"Bed {bed.bed_number} is not active."
                )
            
            # Mark bed as unavailable BEFORE creating admission
            # This prevents the model's clean() from seeing it as available
            bed.is_available = False
            bed.save(update_fields=['is_available', 'updated_at'])
            
            # Refresh the bed object to ensure we have the latest state
            bed.refresh_from_db()
            
            # Get admitting doctor from context (passed by view)
            admitting_doctor = self.context.get('request').user if self.context.get('request') else None
            if not admitting_doctor:
                raise serializers.ValidationError("Admitting doctor is required.")
            
            # Create admission - ensure visit is included
            # Handle admission_date - use timezone.now() if not provided
            from django.utils import timezone as tz
            from datetime import datetime
            
            admission_date = validated_data.get('admission_date')
            if not admission_date:
                admission_date = tz.now()
            elif isinstance(admission_date, str):
                # Parse ISO format string if provided as string
                try:
                    # Try parsing ISO format
                    if 'T' in admission_date:
                        admission_date = datetime.fromisoformat(admission_date.replace('Z', '+00:00'))
                    else:
                        # Just date, add time
                        admission_date = datetime.fromisoformat(admission_date)
                    # Make timezone-aware if not already
                    if admission_date.tzinfo is None:
                        admission_date = tz.make_aware(admission_date)
                except (ValueError, AttributeError) as e:
                    # If parsing fails, use current time
                    admission_date = tz.now()
            
            # Ensure chief_complaint is provided (required field)
            chief_complaint = validated_data.get('chief_complaint', '').strip()
            if not chief_complaint:
                raise serializers.ValidationError({
                    'chief_complaint': 'Chief complaint is required.'
                })
            
            # Get ward from validated_data
            ward = validated_data.get('ward')
            if not ward:
                raise serializers.ValidationError("Ward is required for admission.")
            
            # Ensure ward is a Ward object
            if not isinstance(ward, Ward):
                try:
                    ward = Ward.objects.get(pk=ward)
                except Ward.DoesNotExist:
                    raise serializers.ValidationError("Selected ward does not exist.")
            
            # Create admission
            # Note: We've already validated bed availability and marked it as unavailable.
            # The model's clean() will check bed availability, but since we've already
            # marked it unavailable, we need to ensure clean() doesn't fail.
            # We'll use the bed object that we just updated.
            admission = Admission.objects.create(
                visit=visit,
                ward=ward,
                bed=bed,  # This bed object has is_available=False now
                admission_type=validated_data.get('admission_type', 'ELECTIVE'),
                admission_source=validated_data.get('admission_source', 'OUTPATIENT'),
                admission_date=admission_date,
                chief_complaint=chief_complaint,
                admission_notes=validated_data.get('admission_notes', ''),
                admitting_doctor=admitting_doctor,
                admission_status='ADMITTED'
            )
        
        return admission


class AdmissionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating admissions (limited fields)."""
    
    class Meta:
        model = Admission
        fields = [
            'admission_status', 'admission_notes', 'discharge_date'
        ]
    
    def validate_admission_status(self, value):
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.admission_status
            
            # Can only discharge if currently admitted
            if value == 'DISCHARGED' and current_status != 'ADMITTED':
                raise serializers.ValidationError(
                    f"Cannot discharge patient with status '{current_status}'."
                )
        
        return value
    
    def update(self, instance, validated_data):
        """Update admission and handle bed availability."""
        admission_status = validated_data.get('admission_status', instance.admission_status)
        
        # If discharging, free the bed
        if admission_status == 'DISCHARGED' and instance.admission_status != 'DISCHARGED':
            if not validated_data.get('discharge_date'):
                from django.utils import timezone
                validated_data['discharge_date'] = timezone.now()
            
            if instance.bed:
                instance.bed.is_available = True
                instance.bed.save(update_fields=['is_available', 'updated_at'])
        
        # Update admission
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class AdmissionTransferSerializer(serializers.Serializer):
    """Serializer for transferring patients to different ward/bed."""
    new_ward_id = serializers.IntegerField()
    new_bed_id = serializers.IntegerField()
    transfer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_new_bed_id(self, value):
        """Ensure new bed exists and is available."""
        try:
            bed = Bed.objects.get(id=value, is_active=True)
        except Bed.DoesNotExist:
            raise serializers.ValidationError("Bed not found or inactive.")
        
        if not bed.is_available:
            raise serializers.ValidationError(f"Bed {bed.bed_number} is not available.")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        new_ward_id = attrs.get('new_ward_id')
        new_bed_id = attrs.get('new_bed_id')
        
        try:
            new_ward = Ward.objects.get(id=new_ward_id, is_active=True)
            new_bed = Bed.objects.get(id=new_bed_id, is_active=True)
        except Ward.DoesNotExist:
            raise serializers.ValidationError({
                'new_ward_id': "Ward not found or inactive."
            })
        except Bed.DoesNotExist:
            raise serializers.ValidationError({
                'new_bed_id': "Bed not found or inactive."
            })
        
        if new_bed.ward_id != new_ward_id:
            raise serializers.ValidationError({
                'new_bed_id': "Bed must belong to the selected ward."
            })
        
        return attrs

