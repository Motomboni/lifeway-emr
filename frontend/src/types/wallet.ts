/**
 * Wallet TypeScript types
 */

export interface Wallet {
  id: number;
  patient: number;
  patient_name: string;
  patient_id: number;
  balance: string;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaymentChannel {
  id: number;
  name: string;
  channel_type: 'PAYSTACK' | 'MOBILE_MONEY' | 'BANK_TRANSFER' | 'CASH' | 'CARD' | 'INSURANCE';
  is_active: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface WalletTransaction {
  id: number;
  wallet: number;
  wallet_patient_name: string;
  transaction_type: 'CREDIT' | 'DEBIT';
  amount: string;
  balance_after: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  payment_channel: number | null;
  payment_channel_name: string | null;
  visit: number | null;
  gateway_transaction_id: string;
  description: string;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
}

export interface WalletTopUpRequest {
  amount: number;
  payment_channel_id: number;
  description?: string;
  callback_url?: string;
}

export interface WalletTopUpResponse {
  transaction_id: number;
  reference: string;
  authorization_url: string;
  access_code: string;
}

export interface WalletPaymentRequest {
  visit_id: number;
  amount: number;
  description?: string;
}

export interface WalletPaymentResponse {
  status: string;
  transaction: WalletTransaction;
  wallet_balance: string;
}
