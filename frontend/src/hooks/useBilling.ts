/**
 * React Query hooks for billing data
 * 
 * NOTE: React Query (@tanstack/react-query) is not currently installed.
 * These hooks are placeholders for when React Query is added.
 * For now, components should use direct API calls with useState/useEffect.
 */
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from './useToast';
import {
  getBillingSummary,
  getVisitCharges,
  createCharge,
  createPayment,
  createWalletDebit,
  createInsurance,
  getVisitInsurance,
  updateInsurance,
  getPaymentIntents,
  initializePaystackPayment,
  verifyPaystackPayment,
  BillingSummary,
  VisitCharge,
  ChargeCreateData,
  PaymentCreateData,
  WalletDebitData,
  InsuranceCreateData,
} from '../api/billing';

/**
 * Get billing summary for a visit
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 * For now, use getBillingSummary() directly with useState/useEffect.
 */
export function useBillingSummary(visitId: number, enabled: boolean = true) {
  // Placeholder - React Query not installed
  // return useQuery({
  //   queryKey: ['billing', 'summary', visitId],
  //   queryFn: () => getBillingSummary(visitId),
  //   enabled: enabled && !!visitId,
  //   refetchInterval: 30000,
  //   staleTime: 10000,
  // });
  return { data: null, isLoading: false, error: null };
}

/**
 * Get charges for a visit
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useVisitCharges(visitId: number, enabled: boolean = true) {
  // Placeholder - React Query not installed
  return { data: [], isLoading: false, error: null };
}

/**
 * Get insurance record for a visit
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useVisitInsurance(visitId: number, enabled: boolean = true) {
  // Placeholder - React Query not installed
  return { data: null, isLoading: false, error: null };
}

/**
 * Get payment intents for a visit
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function usePaymentIntents(visitId: number, enabled: boolean = true) {
  // Placeholder - React Query not installed
  return { data: [], isLoading: false, error: null };
}

/**
 * Create a MISC charge
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useCreateCharge(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async (data: ChargeCreateData) => {
      try {
        await createCharge(visitId, data);
        showSuccess('Charge added successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to add charge');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Create a payment
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useCreatePayment(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async (data: PaymentCreateData) => {
      try {
        await createPayment(visitId, data);
        showSuccess('Payment recorded successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to record payment');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Create wallet debit payment
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useCreateWalletDebit(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async (data: WalletDebitData) => {
      try {
        await createWalletDebit(visitId, data);
        showSuccess('Wallet payment processed successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to process wallet payment');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Create insurance record
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useCreateInsurance(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async (data: InsuranceCreateData) => {
      try {
        await createInsurance(visitId, data);
        showSuccess('Insurance record created successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to create insurance record');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Update insurance record (approval/rejection)
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useUpdateInsurance(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async ({ insuranceId, data }: { insuranceId: number; data: Partial<InsuranceCreateData & { approval_status?: 'PENDING' | 'APPROVED' | 'REJECTED'; approved_amount?: string; rejection_reason?: string }> }) => {
      try {
        await updateInsurance(visitId, insuranceId, data);
        showSuccess('Insurance record updated successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to update insurance record');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Initialize Paystack payment
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useInitializePaystack(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async (data: { amount: string; callback_url?: string; customer_email?: string }) => {
      try {
        return await initializePaystackPayment(visitId, { visit_id: visitId, ...data });
      } catch (error: any) {
        showError(error.message || 'Failed to initialize Paystack payment');
        throw error;
      }
    },
    isPending: false,
  };
}

/**
 * Verify Paystack payment
 * 
 * NOTE: This is a placeholder. Install @tanstack/react-query to use.
 */
export function useVerifyPaystack(visitId: number) {
  const { showSuccess, showError } = useToast();
  
  // Placeholder - React Query not installed
  return {
    mutate: async ({ paymentIntentId, reference }: { paymentIntentId: number; reference: string }) => {
      try {
        await verifyPaystackPayment(visitId, paymentIntentId, reference);
        showSuccess('Payment verified successfully');
      } catch (error: any) {
        showError(error.message || 'Failed to verify payment');
        throw error;
      }
    },
    isPending: false,
  };
}
