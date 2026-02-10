/**
 * Payment API Client
 * 
 * All endpoints are visit-scoped:
 * - GET    /api/v1/visits/{visitId}/payments/          - List payments
 * - POST   /api/v1/visits/{visitId}/payments/          - Create payment (Receptionist)
 * - POST   /api/v1/visits/{visitId}/payments/{id}/clear/ - Clear payment (Receptionist)
 */
import { apiRequest } from '../utils/apiClient';
import { Payment, PaymentCreateData, PaymentClearData } from '../types/payment';

// Re-export types for convenience
export type { Payment, PaymentCreateData, PaymentClearData } from '../types/payment';

/**
 * Fetch payments for a visit
 */
export async function fetchPayments(visitId: string): Promise<Payment[]> {
  return apiRequest<Payment[]>(`/visits/${visitId}/payments/`);
}

/**
 * Create a new payment (Receptionist only)
 */
export async function createPayment(
  visitId: string,
  paymentData: PaymentCreateData
): Promise<Payment> {
  return apiRequest<Payment>(`/visits/${visitId}/payments/`, {
    method: 'POST',
    body: JSON.stringify(paymentData),
  });
}

/**
 * Clear a payment (Receptionist only)
 */
export async function clearPayment(
  visitId: string,
  paymentId: number,
  clearData?: PaymentClearData
): Promise<Payment> {
  return apiRequest<Payment>(`/visits/${visitId}/payments/${paymentId}/clear/`, {
    method: 'POST',
    body: JSON.stringify(clearData || {}),
  });
}
