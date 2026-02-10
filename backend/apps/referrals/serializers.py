"""
Serializers for Referral model.
"""
from rest_framework import serializers
from .models import Referral


class ReferralSerializer(serializers.ModelSerializer):
    """Base serializer for Referral."""
    
    referred_by_name = serializers.CharField(
        source='referred_by.get_full_name',
        read_only=True
    )
    
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    consultation_id = serializers.IntegerField(source='consultation.id', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'specialty',
            'specialist_name',
            'specialist_contact',
            'reason',
            'clinical_summary',
            'urgency',
            'status',
            'referred_by',
            'referred_by_name',
            'accepted_at',
            'completed_at',
            'specialist_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'referred_by',
            'referred_by_name',
            'accepted_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]


class ReferralCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating referrals (Doctor only)."""
    
    class Meta:
        model = Referral
        fields = [
            'consultation',
            'specialty',
            'specialist_name',
            'specialist_contact',
            'reason',
            'clinical_summary',
            'urgency',
        ]
    
    def validate_consultation(self, value):
        """Ensure consultation belongs to the visit."""
        visit_id = self.context.get('visit_id')
        if visit_id and value.visit_id != visit_id:
            raise serializers.ValidationError(
                "Consultation must belong to the same visit."
            )
        return value
    
    def create(self, validated_data):
        """Create referral with visit and doctor context."""
        visit_id = self.context.get('visit_id')
        user = self.context['request'].user
        
        validated_data['visit_id'] = visit_id
        validated_data['referred_by'] = user
        
        return super().create(validated_data)


class ReferralUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating referral status and notes."""
    
    class Meta:
        model = Referral
        fields = [
            'status',
            'specialist_notes',
        ]
    
    def validate_status(self, value):
        """Validate status transitions."""
        instance = self.instance
        
        # Allow status updates even for closed visits
        if instance.visit.status == 'CLOSED':
            # Only allow status updates, not other field changes
            allowed_statuses = ['ACCEPTED', 'REJECTED', 'COMPLETED', 'CANCELLED']
            if value not in allowed_statuses:
                raise serializers.ValidationError(
                    "For closed visits, only status updates are allowed."
                )
        
        # Validate status transitions
        current_status = instance.status
        
        # Valid transitions
        valid_transitions = {
            'PENDING': ['ACCEPTED', 'REJECTED', 'CANCELLED'],
            'ACCEPTED': ['COMPLETED', 'CANCELLED'],
            'REJECTED': [],  # Cannot change from rejected
            'COMPLETED': [],  # Cannot change from completed
            'CANCELLED': [],  # Cannot change from cancelled
        }
        
        if value != current_status:
            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot change status from {current_status} to {value}."
                )
        
        return value
    
    def update(self, instance, validated_data):
        """Update referral with status change handling."""
        status = validated_data.get('status')
        
        if status == 'ACCEPTED' and instance.status != 'ACCEPTED':
            instance.accept()
        elif status == 'COMPLETED' and instance.status != 'COMPLETED':
            instance.complete()
        elif status == 'CANCELLED' and instance.status != 'CANCELLED':
            instance.cancel()
        else:
            # Update other fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        
        return instance
