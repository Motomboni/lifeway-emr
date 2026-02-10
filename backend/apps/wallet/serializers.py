"""
Serializers for wallet app.
"""
from decimal import Decimal
from rest_framework import serializers
from .models import Wallet, WalletTransaction, PaymentChannel


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model."""
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_id',
            'balance',
            'currency',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
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


class PaymentChannelSerializer(serializers.ModelSerializer):
    """Serializer for PaymentChannel model."""
    
    class Meta:
        model = PaymentChannel
        fields = [
            'id',
            'name',
            'channel_type',
            'is_active',
            'config',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for WalletTransaction model."""
    wallet_patient_name = serializers.CharField(source='wallet.patient.full_name', read_only=True)
    payment_channel_name = serializers.CharField(source='payment_channel.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id',
            'wallet',
            'wallet_patient_name',
            'transaction_type',
            'amount',
            'balance_after',
            'status',
            'payment_channel',
            'payment_channel_name',
            'visit',
            'gateway_transaction_id',
            'description',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'balance_after',
            'created_at',
        ]
    
    def get_wallet_patient_name(self, obj):
        """Get patient's full name from wallet."""
        if obj.wallet and obj.wallet.patient:
            return obj.wallet.patient.get_full_name()
        return None
    
    def get_created_by_name(self, obj):
        """Get name of user who created the transaction."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None


class WalletTopUpSerializer(serializers.Serializer):
    """Serializer for wallet top-up requests."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    payment_channel_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
    callback_url = serializers.URLField(required=False, allow_blank=True)


class WalletPaymentSerializer(serializers.Serializer):
    """Serializer for wallet payment requests."""
    visit_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(required=False, allow_blank=True)
