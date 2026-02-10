"""
Radiology Request Serializers - role-based field visibility.

Per EMR Rules:
- Doctor: Can create requests, view all fields including reports
- Radiology Tech: Can only update reports, cannot see diagnosis/consultation notes
- Data minimization: Radiology Tech sees only what's needed for their role
"""
from rest_framework import serializers
from .models import RadiologyRequest, RadiologyOrder


class RadiologyRequestSerializer(serializers.ModelSerializer):
    """
    Base serializer for Radiology Request.
    
    Role-based field visibility:
    - Doctor: All fields visible
    - Radiology Tech: Limited fields (no consultation details)
    """
    
    # Read-only fields
    visit_id = serializers.IntegerField(read_only=True)
    consultation_id = serializers.IntegerField(read_only=True)
    ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
    reported_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    report_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = RadiologyRequest
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'study_type',
            'study_code',
            'clinical_indication',
            'instructions',
            'status',
            'report',
            'report_date',
            'finding_flag',
            'image_count',
            'image_metadata',
            'ordered_by',
            'reported_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'consultation_id',
            'ordered_by',
            'reported_by',
            'created_at',
            'updated_at',
            'report_date',
        ]


class RadiologyRequestCreateSerializer(RadiologyRequestSerializer):
    """
    Serializer for creating radiology requests (Doctor only).
    
    Doctor provides:
    - study_type (optional - defaults to 'General Study' if not provided)
    - study_code (optional)
    - clinical_indication (optional)
    - instructions (optional)
    
    System sets:
    - visit_id (from URL)
    - consultation_id (from consultation context)
    - ordered_by (from authenticated user)
    - status (defaults to PENDING)
    """
    
    study_type = serializers.CharField(required=False, allow_blank=True, default='General Study')
    
    def validate(self, attrs):
        """Ensure consultation context is provided."""
        # Consultation is set from context, not from request data
        if 'consultation' in attrs:
            raise serializers.ValidationError(
                "Consultation cannot be set directly. It is derived from consultation context."
            )
        
        # Set default study_type if not provided
        if not attrs.get('study_type'):
            attrs['study_type'] = 'General Study'
        
        return attrs


class RadiologyRequestReportSerializer(serializers.ModelSerializer):
    """
    Serializer for Radiology Tech to post reports (RadiologyRequest only).
    PATCH payload: { report: string, image_count?: number }.
    Backend sets: reported_by, report_date, status=COMPLETED.
    Finding flag persistence is only valid for legacy RadiologyResult flow; not accepted here.
    """
    report = serializers.CharField(required=True, allow_blank=False)
    image_count = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    study_type = serializers.CharField(read_only=True)
    study_code = serializers.CharField(read_only=True)
    clinical_indication = serializers.CharField(read_only=True)
    instructions = serializers.CharField(read_only=True)
    ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
    reported_by = serializers.PrimaryKeyRelatedField(read_only=True)
    report_date = serializers.DateTimeField(read_only=True)
    visit_id = serializers.IntegerField(read_only=True)
    consultation_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    image_metadata = serializers.JSONField(read_only=True)

    class Meta:
        model = RadiologyRequest
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'study_type',
            'study_code',
            'clinical_indication',
            'instructions',
            'status',
            'report',
            'report_date',
            'finding_flag',  # read-only: not persisted for Service Catalog
            'image_count',
            'image_metadata',
            'ordered_by',
            'reported_by',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'consultation_id',
            'study_type',
            'study_code',
            'clinical_indication',
            'instructions',
            'status',
            'report_date',
            'finding_flag',
            'image_metadata',
            'ordered_by',
            'reported_by',
        ]

    def validate_report(self, value):
        """Report is required when posting radiology results."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Report is required when posting radiology results."
            )
        return value.strip()


class RadiologyRequestReadSerializer(RadiologyRequestSerializer):
    """
    Serializer for reading radiology requests.
    
    Doctor sees all fields including reports.
    Radiology Tech sees limited fields (no consultation context).
    """
    pass


# === Radiology Orders (aligned with frontend expectations) ===

class RadiologyOrderSerializer(serializers.ModelSerializer):
    """Read serializer for radiology orders (visit-scoped)."""

    visit_id = serializers.IntegerField(read_only=True)
    ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = RadiologyOrder
        fields = [
            'id',
            'visit_id',
            'imaging_type',
            'body_part',
            'clinical_indication',
            'priority',
            'status',
            'created_at',
            'ordered_by',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'status',
            'created_at',
            'ordered_by',
        ]


class RadiologyOrderCreateSerializer(serializers.ModelSerializer):
    """Create serializer for radiology orders (Doctor only)."""

    class Meta:
        model = RadiologyOrder
        fields = [
            'imaging_type',
            'body_part',
            'clinical_indication',
            'priority',
        ]

    def validate(self, attrs):
        """Validate radiology order data and check for duplicates."""
        # Check for duplicate radiology order (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_radiology_order_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            visit = self.context.get('visit')
            study_code = attrs.get('imaging_type')  # Assuming imaging_type is the study code
            
            if visit and study_code:
                try:
                    check_radiology_order_duplicate(
                        visit=visit,
                        study_code=study_code,
                        window_minutes=5
                    )
                except DjangoValidationError as e:
                    raise serializers.ValidationError(str(e))
        
        return attrs
    
    def create(self, validated_data):
        """
        Create radiology order using visit and user from context.
        Context must provide: visit, request.
        """
        visit = self.context.get('visit')
        request = self.context.get('request')

        if not visit or not request:
            raise serializers.ValidationError("Visit context is required to create radiology order.")

        return RadiologyOrder.objects.create(
            visit=visit,
            ordered_by=request.user,
            status='ORDERED',
            **validated_data
        )
