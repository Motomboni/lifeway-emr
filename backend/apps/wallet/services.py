"""
Payment gateway services for wallet transactions.

Supports multiple payment channels including Paystack.
"""
import requests
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.exceptions import ValidationError


class PaystackService:
    """
    Paystack payment gateway integration.
    
    Documentation: https://paystack.com/docs/api/
    """
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = 'https://api.paystack.co'
        
        if not self.secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY must be set in settings")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction.
        
        Args:
            email: Customer email
            amount: Amount in kobo (smallest currency unit for NGN)
            reference: Unique transaction reference
            metadata: Additional metadata
            callback_url: Callback URL after payment
        
        Returns:
            Dict with authorization_url and access_code
        """
        # Convert amount to kobo (NGN smallest unit)
        amount_in_kobo = int(amount * 100)
        
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'metadata': metadata or {}
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        
        response = requests.post(
            f'{self.base_url}/transaction/initialize',
            json=payload,
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json()
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a Paystack transaction.
        
        Args:
            reference: Transaction reference
        
        Returns:
            Transaction details
        """
        response = requests.get(
            f'{self.base_url}/transaction/verify/{reference}',
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json()
    
    def create_transfer_recipient(
        self,
        type: str,
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = 'NGN'
    ) -> Dict[str, Any]:
        """
        Create a transfer recipient (for payouts).
        
        Args:
            type: Recipient type ('nuban' for bank accounts)
            name: Account name
            account_number: Account number
            bank_code: Bank code
            currency: Currency code
        
        Returns:
            Recipient details
        """
        payload = {
            'type': type,
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': currency
        }
        
        response = requests.post(
            f'{self.base_url}/transferrecipient',
            json=payload,
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json()
    
    def initiate_transfer(
        self,
        source: str,
        amount: Decimal,
        recipient: str,
        reason: str = 'Wallet withdrawal'
    ) -> Dict[str, Any]:
        """
        Initiate a transfer (payout).
        
        Args:
            source: Transfer source ('balance')
            amount: Amount in kobo
            recipient: Recipient code
            reason: Transfer reason
        
        Returns:
            Transfer details
        """
        amount_in_kobo = int(amount * 100)
        
        payload = {
            'source': source,
            'amount': amount_in_kobo,
            'recipient': recipient,
            'reason': reason
        }
        
        response = requests.post(
            f'{self.base_url}/transfer',
            json=payload,
            headers=self._get_headers()
        )
        
        response.raise_for_status()
        return response.json()


class PaymentGatewayService:
    """
    Unified service for multiple payment gateways.
    """
    
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        
        if channel_type == 'PAYSTACK':
            self.gateway = PaystackService()
        else:
            raise ValueError(f"Unsupported payment channel: {channel_type}")
    
    def initialize_payment(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize payment with the configured gateway."""
        if self.channel_type == 'PAYSTACK':
            return self.gateway.initialize_transaction(
                email=email,
                amount=amount,
                reference=reference,
                metadata=metadata,
                callback_url=callback_url
            )
        else:
            raise ValueError(f"Payment initialization not supported for {self.channel_type}")
    
    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify payment with the configured gateway."""
        if self.channel_type == 'PAYSTACK':
            return self.gateway.verify_transaction(reference)
        else:
            raise ValueError(f"Payment verification not supported for {self.channel_type}")
