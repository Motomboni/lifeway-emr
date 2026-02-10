"""
Admin for wallet app.
"""
from django.contrib import admin
from .models import Wallet, WalletTransaction, PaymentChannel


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'balance', 'currency', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'transaction_type', 'amount', 'status', 'created_at')
    search_fields = ('wallet__patient__first_name', 'wallet__patient__last_name', 'gateway_transaction_id')


@admin.register(PaymentChannel)
class PaymentChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel_type', 'is_active', 'created_at')
    search_fields = ('name',)
