"""
Wallet models for patient payment management.

Per EMR Rules:
- Each patient has one wallet (auto-created)
- Wallet balance tracks available funds
- All transactions are immutable and audited
- Multiple payment channels supported
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class Wallet(models.Model):
    """
    Patient wallet for managing payment balance.
    
    Auto-created when a patient is created.
    """
    patient = models.OneToOneField(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='wallet',
        help_text="Patient this wallet belongs to"
    )
    
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current wallet balance"
    )
    
    currency = models.CharField(
        max_length=3,
        default='NGN',
        help_text="Currency code (e.g., NGN, USD)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether wallet is active"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When wallet was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When wallet was last updated"
    )
    
    class Meta:
        db_table = 'wallets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
    
    def __str__(self):
        return f"Wallet for {self.patient.get_full_name()} - {self.balance} {self.currency}"
    
    def credit(self, amount: Decimal, description: str = ''):
        """Credit amount to wallet."""
        if amount <= 0:
            raise ValidationError("Credit amount must be greater than zero")
        
        self.balance += amount
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='CREDIT',
            amount=amount,
            balance_after=self.balance,
            description=description
        )
    
    def debit(self, amount: Decimal, visit, description: str = '', created_by=None):
        """
        Debit amount from wallet for a visit payment.
        
        Per EMR Rules:
        - Wallet deductions MUST be visit-referenced
        - Wallet cannot auto-deduct without explicit billing action
        - Negative wallet balances are forbidden
        - Wallet usage MUST be auditable
        
        Args:
            amount: Amount to debit (must be > 0)
            visit: Visit instance (REQUIRED for DEBIT transactions)
            description: Transaction description
            created_by: User who initiated the transaction (for audit)
        
        Returns:
            WalletTransaction: Created transaction record
        """
        if amount <= 0:
            raise ValidationError("Debit amount must be greater than zero")
        
        if self.balance < amount:
            raise ValidationError(
                f"Insufficient wallet balance. Current balance: {self.balance}, "
                f"Requested amount: {amount}"
            )
        
        # Ensure visit is provided (REQUIRED for DEBIT)
        if not visit:
            raise ValidationError(
                "Visit is REQUIRED for wallet DEBIT transactions. "
                "Wallet deductions MUST be visit-referenced per EMR rules."
            )
        
        # Ensure visit is not CLOSED
        if visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot debit wallet for a CLOSED visit. Closed visits are immutable."
            )
        
        # Prevent negative balance (enforced by check above, but double-check)
        if self.balance - amount < 0:
            raise ValidationError("Debit would result in negative balance, which is forbidden.")
        
        # Perform debit
        self.balance -= amount
        self.save(update_fields=['balance', 'updated_at'])
        
        # Create transaction record (MUST be visit-referenced)
        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type='DEBIT',
            amount=amount,
            balance_after=self.balance,
            visit=visit,  # REQUIRED for DEBIT
            description=description or f'Payment for Visit {visit.id}',
            created_by=created_by,
            status='COMPLETED'
        )
        
        return transaction


class PaymentChannel(models.Model):
    """
    Payment channel configuration (Paystack, Mobile Money, etc.).
    """
    CHANNEL_TYPES = [
        ('PAYSTACK', 'Paystack'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('INSURANCE', 'Insurance'),
    ]
    
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Channel name"
    )
    
    channel_type = models.CharField(
        max_length=20,
        choices=CHANNEL_TYPES,
        help_text="Type of payment channel"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether channel is active"
    )
    
    # Configuration (JSON field for channel-specific settings)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Channel-specific configuration (API keys, etc.)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = 'payment_channels'
        ordering = ['name']
        verbose_name = 'Payment Channel'
        verbose_name_plural = 'Payment Channels'
    
    def __str__(self):
        return f"{self.name} ({self.channel_type})"


class WalletTransaction(models.Model):
    """
    Immutable transaction record for wallet operations.
    
    Per EMR Rules:
    - Append-only (no edits/deletes)
    - All transactions are audited
    """
    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Wallet this transaction belongs to"
    )
    
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Wallet balance after this transaction"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='COMPLETED',
        help_text="Transaction status"
    )
    
    payment_channel = models.ForeignKey(
        PaymentChannel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Payment channel used"
    )
    
    # Reference to visit if transaction is visit-related
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
        help_text="Visit this transaction is related to (if applicable)"
    )
    
    # Payment gateway references
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Transaction ID from payment gateway (e.g., Paystack reference)"
    )
    
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response from payment gateway"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Transaction description"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
        help_text="User who initiated the transaction"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When transaction was created"
    )
    
    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['visit']),
            models.Index(fields=['status']),
            models.Index(fields=['gateway_transaction_id']),
        ]
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
    
    def __str__(self):
        return f"{self.transaction_type} {self.amount} - {self.wallet.patient.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Prevent updates - transactions are append-only."""
        if self.pk:
            raise ValueError("Wallet transactions are append-only and cannot be modified.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - transactions are immutable."""
        raise ValueError("Wallet transactions cannot be deleted.")
