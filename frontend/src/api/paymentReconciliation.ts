import { apiRequest } from '../utils/apiClient';

export interface PaymentReconciliation {
  id: number;
  visit_id: number | null;
  payment_id: number | null;
  method: string;
  reference: string;
  amount_ngn: string;
  payer_name: string;
  bank_name: string;
  status: 'PENDING' | 'MATCHED' | 'DISPUTED';
  notes: string;
  recorded_by: number | null;
  matched_at: string | null;
  created_at: string;
}

export async function fetchPaymentReconciliations(status?: string): Promise<PaymentReconciliation[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiRequest<PaymentReconciliation[]>(`/billing/payment-reconciliation/${qs}`);
}

export async function createPaymentReconciliation(data: {
  visit_id?: number;
  method: string;
  reference: string;
  amount_ngn: string;
  payer_name?: string;
  bank_name?: string;
  notes?: string;
}): Promise<PaymentReconciliation> {
  return apiRequest<PaymentReconciliation>('/billing/payment-reconciliation/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function matchPaymentReconciliation(
  recId: number,
  data?: { payment_id?: number; notes?: string },
): Promise<PaymentReconciliation> {
  return apiRequest<PaymentReconciliation>(`/billing/payment-reconciliation/${recId}/match/`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  });
}

export async function disputePaymentReconciliation(
  recId: number,
  notes?: string,
): Promise<PaymentReconciliation> {
  return apiRequest<PaymentReconciliation>(`/billing/payment-reconciliation/${recId}/dispute/`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}
