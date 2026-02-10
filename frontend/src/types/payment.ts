/**
 * TypeScript types for Payments
 */

export interface Payment {
  id: number;
  visit: number;
  visit_id: number;
  amount: string;
  payment_method: 'CASH' | 'CARD' | 'BANK_TRANSFER' | 'MOBILE_MONEY' | 'INSURANCE' | 'WALLET' | 'PAYSTACK';
  status: 'PENDING' | 'CLEARED' | 'FAILED' | 'REFUNDED';
  transaction_reference?: string;
  notes?: string;
  processed_by: number;
  processed_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface PaymentCreateData {
  visit: number;
  amount: number;
  payment_method: 'CASH' | 'CARD' | 'BANK_TRANSFER' | 'MOBILE_MONEY' | 'INSURANCE' | 'WALLET' | 'PAYSTACK';
  transaction_reference?: string;
  notes?: string;
  status?: 'PENDING' | 'CLEARED';
}

export interface PaymentClearData {
  transaction_reference?: string;
  notes?: string;
}
