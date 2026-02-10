"""
Paystack service for Visit billing - NO PHI exposure.

Per EMR Rules:
- Paystack transactions MUST be visit-scoped
- Paystack reference MUST map to a Visit
- No PHI may be sent to Paystack
- Verification must occur server-side
- Payment records are immutable once verified
"""
import requests
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.exceptions import ValidationError


class PaystackVisitService:
    """
    Paystack service for Visit-scoped payment processing.
    
    Security Rules:
    - NO PHI in metadata (no patient names, medical records, etc.)
    - Only visit_id and system identifiers in metadata
    - All verification server-side only
    - Webhook signature validation required
    """
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = 'https://api.paystack.co'
        
        if not self.secret_key or self.secret_key.strip() == '':
            raise ValueError(
                "PAYSTACK_SECRET_KEY must be set in settings. "
                "Please configure PAYSTACK_SECRET_KEY in your environment variables or settings."
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(
        self,
        visit_id: int,
        amount: Decimal,
        reference: str,
        callback_url: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction for a Visit.
        
        Security: NO PHI in metadata - only visit_id and system identifiers.
        
        Args:
            visit_id: Visit ID (system identifier, not PHI)
            amount: Amount in NGN
            reference: Unique transaction reference
            callback_url: Optional callback URL after payment
            customer_email: Optional customer email (generic, not PHI)
        
        Returns:
            Dict with authorization_url and access_code
        """
        # Convert amount to kobo (NGN smallest unit)
        amount_in_kobo = int(amount * 100)
        
        # Metadata: ONLY system identifiers, NO PHI
        # Do NOT include: patient name, medical records, diagnosis, etc.
        metadata = {
            'visit_id': visit_id,  # System identifier only
            'reference': reference,  # System reference
            'source': 'emr_visit_billing'  # System identifier
        }
        
        payload = {
            'amount': amount_in_kobo,
            'reference': reference,
            'metadata': metadata
        }
        
        # Email is optional and should be generic (not patient email)
        if customer_email:
            payload['email'] = customer_email
        
        if callback_url:
            payload['callback_url'] = callback_url
        
        try:
            response = requests.post(
                f'{self.base_url}/transaction/initialize',
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Try to get more details from Paystack error response
            error_detail = str(e)
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_detail = f"Paystack error: {error_data['message']}"
            except (ValueError, TypeError):
                pass
            raise ValidationError(f"Paystack initialization failed: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Paystack initialization failed: {str(e)}")
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a Paystack transaction (server-side only).
        
        This MUST be called server-side. Frontend verification is NOT trusted.
        
        Args:
            reference: Transaction reference
        
        Returns:
            Transaction details from Paystack
        """
        try:
            response = requests.get(
                f'{self.base_url}/transaction/verify/{reference}',
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Paystack verification failed: {str(e)}")
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify Paystack webhook signature.
        
        This MUST be called for all webhook requests to prevent tampering.
        
        Args:
            payload: Raw request body (bytes)
            signature: X-Paystack-Signature header value
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            return False
        
        # Compute expected signature
        computed_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_signature, signature)
    
    def is_transaction_successful(self, paystack_response: Dict[str, Any]) -> bool:
        """
        Check if Paystack transaction is successful.
        
        Args:
            paystack_response: Paystack API response
        
        Returns:
            True if transaction is successful, False otherwise
        """
        if not paystack_response.get('status'):
            return False
        
        data = paystack_response.get('data', {})
        
        # Transaction is successful if:
        # 1. Status is True
        # 2. Gateway response is 'successful'
        # 3. Status field is 'success'
        return (
            paystack_response.get('status') is True and
            data.get('status') == 'success' and
            data.get('gateway_response') == 'Successful'
        )
    
    def extract_visit_id_from_metadata(
        self,
        paystack_response: Dict[str, Any]
    ) -> Optional[int]:
        """
        Extract visit_id from Paystack metadata.
        
        Args:
            paystack_response: Paystack API response
        
        Returns:
            Visit ID if found, None otherwise
        """
        data = paystack_response.get('data', {})
        metadata = data.get('metadata', {})
        visit_id = metadata.get('visit_id')
        
        if visit_id:
            try:
                return int(visit_id)
            except (ValueError, TypeError):
                return None
        
        return None

