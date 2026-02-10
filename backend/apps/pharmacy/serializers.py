"""
Prescription and Drug Serializers - role-based field visibility.

Per EMR Rules:
- Doctor: Can create prescriptions, view all fields
- Pharmacist: Can only dispense, cannot see diagnosis/consultation notes
- Pharmacist: Can create/manage drugs in catalog
- Data minimization: Pharmacist sees only what's needed for dispensing
"""
from rest_framework import serializers
from .models import Prescription, Drug, DrugInventory, StockMovement


class PrescriptionSerializer(serializers.ModelSerializer):
    """
    Base serializer for Prescription.
    
    Role-based field visibility:
    - Doctor: All fields visible
    - Pharmacist: Limited fields (no consultation details)
    """
    
    # Read-only fields
    visit_id = serializers.IntegerField(read_only=True)
    consultation_id = serializers.IntegerField(read_only=True)
    prescribed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    dispensed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    dispensed_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'drug',
            'drug_code',
            'dosage',
            'frequency',
            'duration',
            'quantity',
            'instructions',
            'status',
            'dispensed',
            'dispensed_date',
            'dispensing_notes',
            'prescribed_by',
            'dispensed_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'consultation_id',
            'prescribed_by',
            'dispensed_by',
            'created_at',
            'updated_at',
            'dispensed_date',
        ]


class PrescriptionCreateSerializer(PrescriptionSerializer):
    """
    Serializer for creating prescriptions (Doctor only).
    
    Doctor provides:
    - drug (required)
    - drug_code (optional)
    - dosage (required)
    - frequency (optional)
    - duration (optional)
    - quantity (optional)
    - instructions (optional)
    
    System sets:
    - visit_id (from URL)
    - consultation_id (from consultation context)
    - prescribed_by (from authenticated user)
    - status (defaults to PENDING)
    """
    
    def validate(self, attrs):
        """Ensure consultation context is provided."""
        # Consultation is set from context, not from request data
        if 'consultation' in attrs:
            raise serializers.ValidationError(
                "Consultation cannot be set directly. It is derived from consultation context."
            )
        
        return attrs


class PrescriptionReadSerializer(PrescriptionSerializer):
    """
    Serializer for reading prescriptions.
    
    Doctor sees all fields including dispensing information.
    Pharmacist sees limited fields (no consultation context).
    """
    pass


# Drug Serializers

class DrugSerializer(serializers.ModelSerializer):
    """
    Base serializer for Drug.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Drug
        fields = [
            'id',
            'name',
            'generic_name',
            'drug_code',
            'drug_class',
            'dosage_forms',
            'common_dosages',
            'cost_price',
            'sales_price',
            'profit',
            'profit_margin',
            'description',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_by_name',
            'profit',
            'profit_margin',
            'created_at',
            'updated_at',
        ]


class DrugCreateSerializer(DrugSerializer):
    """
    Serializer for creating drugs (Pharmacist only).
    
    Required fields:
    - name (required)
    
    Optional fields:
    - generic_name
    - drug_code
    - drug_class
    - dosage_forms
    - common_dosages
    - description
    - is_active (defaults to True)
    """
    
    def validate_name(self, value):
        """Ensure drug name is unique."""
        if Drug.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("A drug with this name already exists.")
        return value.strip()
    
    def validate_drug_code(self, value):
        """Ensure drug code is unique if provided."""
        if value:
            value = value.strip()
            if Drug.objects.filter(drug_code=value).exists():
                raise serializers.ValidationError("A drug with this code already exists.")
        return value


class DrugUpdateSerializer(DrugSerializer):
    """
    Serializer for updating drugs (Pharmacist only).
    """
    
    def validate_name(self, value):
        """Ensure drug name is unique (excluding current instance)."""
        if value:
            value = value.strip()
            # Check if another drug with this name exists (excluding current instance)
            if self.instance:
                if Drug.objects.filter(name__iexact=value).exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError("A drug with this name already exists.")
            else:
                if Drug.objects.filter(name__iexact=value).exists():
                    raise serializers.ValidationError("A drug with this name already exists.")
        return value
    
    def validate_drug_code(self, value):
        """Ensure drug code is unique if provided (excluding current instance)."""
        if value:
            value = value.strip()
            if self.instance:
                if Drug.objects.filter(drug_code=value).exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError("A drug with this code already exists.")
            else:
                if Drug.objects.filter(drug_code=value).exists():
                    raise serializers.ValidationError("A drug with this code already exists.")
        return value


# Inventory Serializers

class DrugInventorySerializer(serializers.ModelSerializer):
    """
    Serializer for Drug Inventory.
    """
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    drug_code = serializers.CharField(source='drug.drug_code', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    last_restocked_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DrugInventory
        fields = [
            'id',
            'drug',
            'drug_name',
            'drug_code',
            'current_stock',
            'unit',
            'reorder_level',
            'batch_number',
            'expiry_date',
            'location',
            'last_restocked_at',
            'last_restocked_by',
            'last_restocked_by_name',
            'is_low_stock',
            'is_out_of_stock',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_low_stock',
            'is_out_of_stock',
            'created_at',
            'updated_at',
        ]
    
    def get_last_restocked_by_name(self, obj):
        """Get last restocked by user's full name."""
        if obj.last_restocked_by:
            return f"{obj.last_restocked_by.first_name} {obj.last_restocked_by.last_name}".strip()
        return None


class DrugInventoryCreateSerializer(DrugInventorySerializer):
    """
    Serializer for creating inventory records (Pharmacist only).
    """
    
    class Meta(DrugInventorySerializer.Meta):
        read_only_fields = DrugInventorySerializer.Meta.read_only_fields + [
            'last_restocked_at',
            'last_restocked_by',
            'last_restocked_by_name',
        ]


class DrugInventoryUpdateSerializer(DrugInventorySerializer):
    """
    Serializer for updating inventory records (Pharmacist only).
    """
    pass


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for Stock Movement.
    """
    inventory_drug_name = serializers.CharField(source='inventory.drug.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    prescription_id = serializers.IntegerField(source='prescription.id', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id',
            'inventory',
            'inventory_drug_name',
            'movement_type',
            'quantity',
            'prescription',
            'prescription_id',
            'reference_number',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_by_name',
            'created_at',
        ]
    
    def get_created_by_name(self, obj):
        """Get created by user's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None


class StockMovementCreateSerializer(StockMovementSerializer):
    """
    Serializer for creating stock movements (Pharmacist only).
    """
    
    def validate_quantity(self, value):
        """Validate quantity based on movement type."""
        movement_type = self.initial_data.get('movement_type')
        
        if movement_type in ['IN', 'RETURNED'] and value <= 0:
            raise serializers.ValidationError("Stock IN and RETURNED movements must have positive quantity.")
        if movement_type in ['OUT', 'DISPENSED', 'EXPIRED', 'DAMAGED'] and value >= 0:
            raise serializers.ValidationError("Stock OUT, DISPENSED, EXPIRED, and DAMAGED movements must have negative quantity.")
        if movement_type == 'ADJUSTMENT' and value == 0:
            raise serializers.ValidationError("Adjustment quantity cannot be zero.")
        
        return value
