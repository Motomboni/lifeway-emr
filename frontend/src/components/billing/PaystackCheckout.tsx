/**
 * Paystack Checkout Component
 * 
 * Handles Paystack payment flow with redirect handling and idempotency.
 * Per EMR Rules: Receptionist-only, visit-scoped, server-side verification.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../../hooks/useToast';
import {
  initializePaystackPayment,
  verifyPaystackPayment,
  getPaymentIntents,
  BillingSummary,
} from '../../api/billing';
import { Visit } from '../../types/visit';
import { logger } from '../../utils/logger';

interface PaystackCheckoutProps {
  visitId: number;
  visit: Visit;
  billingSummary: BillingSummary | null;
  onPaymentSuccess: () => void;
}

interface PaymentIntent {
  id: number;
  visit_id: number;
  amount: string;
  paystack_reference: string;
  authorization_url?: string;
  access_code?: string;
  status: 'INITIALIZED' | 'PENDING' | 'VERIFIED' | 'FAILED';
  created_at: string;
  updated_at: string;
}

export default function PaystackCheckout({
  visitId,
  visit,
  billingSummary,
  onPaymentSuccess,
}: PaystackCheckoutProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showSuccess, showError } = useToast();
  const [initializing, setInitializing] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [paymentIntent, setPaymentIntent] = useState<PaymentIntent | null>(null);
  const processedReferences = React.useRef<Set<string>>(new Set());

  // Check for Paystack callback parameters
  const reference = searchParams.get('reference');
  const trxref = searchParams.get('trxref');
  const paystackReference = reference || trxref;

  // Check if we're returning from Paystack
  const isReturningFromPaystack = !!paystackReference;

  useEffect(() => {
    // If returning from Paystack, verify the payment
    if (isReturningFromPaystack && paystackReference) {
      handlePaystackReturn(paystackReference);
    }
  }, [isReturningFromPaystack, paystackReference]);

  // Check for existing payment intents on mount
  useEffect(() => {
    if (!isReturningFromPaystack) {
      loadPaymentIntents();
    }
  }, [visitId, isReturningFromPaystack]);

  const loadPaymentIntents = async () => {
    try {
      const intents = await getPaymentIntents(visitId);
      // Find the most recent INITIALIZED or PENDING intent
      const activeIntent = intents.find(
        (intent: PaymentIntent) =>
          intent.status === 'INITIALIZED' || intent.status === 'PENDING'
      );
      if (activeIntent) {
        setPaymentIntent(activeIntent);
      }
    } catch (error) {
      console.error('Failed to load payment intents:', error);
    }
  };

  const handlePaystackReturn = async (reference: string) => {
    // Idempotency check: Don't process the same reference twice
    if (processedReferences.current.has(reference)) {
      console.log('Payment reference already processed:', reference);
      // Still redirect to remove query params
      navigate(`/visits/${visitId}`, { replace: true });
      return;
    }

    try {
      setVerifying(true);

      // Find the payment intent with this reference
      const intents = await getPaymentIntents(visitId);
      const intent = intents.find(
        (intent: PaymentIntent) => intent.paystack_reference === reference
      );

      if (!intent) {
        showError('Payment intent not found. Please contact support.');
        navigate(`/visits/${visitId}`, { replace: true });
        return;
      }

      // Mark reference as processed (idempotency)
      processedReferences.current.add(reference);

      // Verify the payment
      await verifyPaystackPayment(visitId, intent.id, reference);

      // Success - show confirmation and refresh
      showSuccess('Payment verified successfully!');
      onPaymentSuccess();

      // Redirect to billing dashboard (remove query params)
      navigate(`/visits/${visitId}`, { replace: true });
    } catch (error: any) {
      console.error('Payment verification failed:', error);
      showError(error.message || 'Failed to verify payment. Please contact support.');
      // Still redirect to remove query params
      navigate(`/visits/${visitId}`, { replace: true });
    } finally {
      setVerifying(false);
    }
  };

  const handleInitializePaystack = async (amount: string, customerEmail?: string) => {
    if (!amount || parseFloat(amount) <= 0) {
      showError('Please enter a valid payment amount');
      return;
    }

    const outstandingBalance = billingSummary
      ? parseFloat(billingSummary.outstanding_balance)
      : 0;

    if (parseFloat(amount) > outstandingBalance) {
      showError('Payment amount cannot exceed outstanding balance');
      return;
    }

    try {
      setInitializing(true);

      const response = await initializePaystackPayment(visitId, {
        visit_id: visitId,
        amount: amount,
        callback_url: `${window.location.origin}/visits/${visitId}?paystack=return`,
        customer_email: customerEmail,
      });

      if (response.authorization_url) {
        // Store payment intent for reference
        if (response.payment_intent) {
          setPaymentIntent(response.payment_intent);
        }

        // Store reference in sessionStorage for idempotency
        if (response.paystack_reference) {
          const pendingPayments = JSON.parse(
            sessionStorage.getItem('pending_paystack_payments') || '[]'
          );
          pendingPayments.push({
            reference: response.paystack_reference,
            visitId: visitId,
            timestamp: Date.now(),
          });
          sessionStorage.setItem('pending_paystack_payments', JSON.stringify(pendingPayments));
        }

        // Redirect to Paystack checkout
        window.location.href = response.authorization_url;
      } else {
        showError('Failed to initialize Paystack payment');
      }
    } catch (error: any) {
      console.error('Paystack initialization failed:', error);
      showError(error.message || 'Failed to initialize Paystack payment');
    } finally {
      setInitializing(false);
    }
  };

  // Clean up old pending payments from sessionStorage (older than 1 hour)
  useEffect(() => {
    const cleanup = () => {
      try {
        const pendingPayments = JSON.parse(
          sessionStorage.getItem('pending_paystack_payments') || '[]'
        );
        const oneHourAgo = Date.now() - 60 * 60 * 1000;
        const recentPayments = pendingPayments.filter(
          (p: any) => p.timestamp > oneHourAgo
        );
        sessionStorage.setItem('pending_paystack_payments', JSON.stringify(recentPayments));
      } catch (error) {
        console.error('Failed to cleanup pending payments:', error);
      }
    };

    cleanup();
    const interval = setInterval(cleanup, 5 * 60 * 1000); // Cleanup every 5 minutes
    return () => clearInterval(interval);
  }, []);

  // If returning from Paystack, show verification status
  if (isReturningFromPaystack) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          {verifying ? (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-lg font-medium text-gray-900">Verifying payment...</p>
              <p className="text-sm text-gray-600 mt-2">Please wait while we confirm your payment</p>
            </>
          ) : (
            <>
              <div className="text-5xl mb-4">✅</div>
              <p className="text-lg font-medium text-gray-900">Payment verification complete</p>
              <p className="text-sm text-gray-600 mt-2">Redirecting to billing dashboard...</p>
            </>
          )}
        </div>
      </div>
    );
  }

  // Expose initialization function via ref or return component that can be used
  return null;
}

/**
 * Hook to use Paystack checkout functionality
 */
export function usePaystackCheckout(
  visitId: number,
  billingSummary: BillingSummary | null,
  onPaymentSuccess: () => void
) {
  const { showError } = useToast();
  const [initializing, setInitializing] = useState(false);

  const initializePayment = async (amount: string, customerEmail?: string) => {
    if (!amount || parseFloat(amount) <= 0) {
      showError('Please enter a valid payment amount');
      return;
    }

    const outstandingBalance = billingSummary
      ? parseFloat(billingSummary.outstanding_balance)
      : 0;

    if (parseFloat(amount) > outstandingBalance) {
      showError('Payment amount cannot exceed outstanding balance');
      return;
    }

    try {
      setInitializing(true);

      const response = await initializePaystackPayment(visitId, {
        visit_id: visitId,
        amount: amount,
        callback_url: `${window.location.origin}/visits/${visitId}?paystack=return`,
        customer_email: customerEmail,
      });

      if (response.authorization_url) {
        // Store reference for idempotency
        if (response.paystack_reference) {
          const pendingPayments = JSON.parse(
            sessionStorage.getItem('pending_paystack_payments') || '[]'
          );
          pendingPayments.push({
            reference: response.paystack_reference,
            visitId: visitId,
            timestamp: Date.now(),
          });
          sessionStorage.setItem('pending_paystack_payments', JSON.stringify(pendingPayments));
        }

        // Redirect to Paystack checkout
        window.location.href = response.authorization_url;
      } else {
        showError('Failed to initialize Paystack payment');
      }
    } catch (error: any) {
      console.error('Paystack initialization failed:', error);
      showError(error.message || 'Failed to initialize Paystack payment');
    } finally {
      setInitializing(false);
    }
  };

  return {
    initializePayment,
    initializing,
  };
}

/**
 * Paystack Return Handler Component
 * 
 * Place this component in the visit details page to handle Paystack redirects
 */
export function PaystackReturnHandler({
  visitId,
  onPaymentSuccess,
}: {
  visitId: number;
  onPaymentSuccess: () => void;
}) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showSuccess, showError } = useToast();
  const [verifying, setVerifying] = useState(false);
  const processedRef = useRef<Set<string>>(new Set());

  const reference = searchParams.get('reference') || searchParams.get('trxref');
  const isReturning = searchParams.get('paystack') === 'return' && !!reference;

  useEffect(() => {
    if (isReturning && reference) {
      handleReturn(reference);
    }
  }, [isReturning, reference]);

  const handleReturn = async (ref: string) => {
    // Idempotency: Don't process same reference twice
    if (processedRef.current.has(ref)) {
      logger.debug('Reference already processed:', ref);
      navigate(`/visits/${visitId}`, { replace: true });
      return;
    }

    try {
      setVerifying(true);
      processedRef.current.add(ref);

      // Find payment intent
      const intents = await getPaymentIntents(visitId);
      const intent = intents.find((i: PaymentIntent) => i.paystack_reference === ref);

      if (!intent) {
        showError('Payment intent not found');
        navigate(`/visits/${visitId}`, { replace: true });
        return;
      }

      // Verify payment
      await verifyPaystackPayment(visitId, intent.id, ref);

      // Remove from pending payments
      const pendingPayments = JSON.parse(
        sessionStorage.getItem('pending_paystack_payments') || '[]'
      );
      const updated = pendingPayments.filter((p: any) => p.reference !== ref);
      sessionStorage.setItem('pending_paystack_payments', JSON.stringify(updated));

      // Success
      showSuccess('Payment verified successfully!');
      onPaymentSuccess();

      // Redirect (remove query params)
      navigate(`/visits/${visitId}`, { replace: true });
    } catch (error: any) {
      console.error('Verification failed:', error);
      showError(error.message || 'Failed to verify payment');
      navigate(`/visits/${visitId}`, { replace: true });
    } finally {
      setVerifying(false);
    }
  };

  if (!isReturning) return null;

  return (
    <div className="fixed inset-0 z-50 bg-white bg-opacity-95 flex items-center justify-center">
      <div className="text-center">
        {verifying ? (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-lg font-medium text-gray-900">Verifying payment...</p>
            <p className="text-sm text-gray-600 mt-2">Please wait while we confirm your payment</p>
          </>
        ) : (
          <>
            <div className="text-5xl mb-4">✅</div>
            <p className="text-lg font-medium text-gray-900">Payment verification complete</p>
            <p className="text-sm text-gray-600 mt-2">Redirecting...</p>
          </>
        )}
      </div>
    </div>
  );
}

