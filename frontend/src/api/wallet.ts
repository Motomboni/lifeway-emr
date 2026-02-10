/**
 * Wallet API Client
 * 
 * Endpoints:
 * - GET /api/v1/wallet/wallets/ - List wallets
 * - GET /api/v1/wallet/wallets/{id}/ - Get wallet
 * - GET /api/v1/wallet/wallets/{id}/transactions/ - Get transactions
 * - POST /api/v1/wallet/wallets/{id}/top-up/ - Top up wallet
 * - POST /api/v1/wallet/wallets/{id}/verify-payment/ - Verify payment
 * - POST /api/v1/wallet/wallets/{id}/pay-visit/ - Pay for visit
 * - GET /api/v1/wallet/payment-channels/ - List payment channels
 */
import { apiRequest } from '../utils/apiClient';
import {
  Wallet,
  PaymentChannel,
  WalletTransaction,
  WalletTopUpRequest,
  WalletTopUpResponse,
  WalletPaymentRequest,
  WalletPaymentResponse,
} from '../types/wallet';

/**
 * Get wallet by ID
 */
export async function getWallet(walletId: number): Promise<Wallet> {
  return apiRequest<Wallet>(`/wallet/wallets/${walletId}/`);
}

/**
 * Get current user's wallet (for patients)
 * Auto-creates wallet if it doesn't exist (handled by backend)
 */
export async function getMyWallet(): Promise<Wallet> {
  const response = await apiRequest<any>('/wallet/wallets/');
  
  // Handle both paginated and non-paginated responses
  let wallets: Wallet[];
  if (Array.isArray(response)) {
    wallets = response;
  } else if (response && response.results && Array.isArray(response.results)) {
    // Paginated response
    wallets = response.results;
  } else {
    // Unexpected format
    wallets = [];
  }
  
  if (wallets.length === 0) {
    // Wallet should be auto-created by backend, but if it's still not there,
    // it might be a patient record issue
    throw new Error('Wallet not found. Please contact support.');
  }
  return wallets[0];
}

/**
 * Get wallet transactions
 */
export async function getWalletTransactions(walletId: number): Promise<WalletTransaction[]> {
  return apiRequest<WalletTransaction[]>(`/wallet/wallets/${walletId}/transactions/`);
}

/**
 * Top up wallet
 */
export async function topUpWallet(
  walletId: number,
  data: WalletTopUpRequest
): Promise<WalletTopUpResponse> {
  return apiRequest<WalletTopUpResponse>(`/wallet/wallets/${walletId}/top-up/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Verify payment after gateway callback
 */
export async function verifyPayment(
  walletId: number,
  reference: string
): Promise<WalletPaymentResponse> {
  return apiRequest<WalletPaymentResponse>(`/wallet/wallets/${walletId}/verify-payment/`, {
    method: 'POST',
    body: JSON.stringify({ reference }),
  });
}

/**
 * Pay for visit using wallet
 */
export async function payVisitWithWallet(
  walletId: number,
  data: WalletPaymentRequest
): Promise<WalletPaymentResponse> {
  return apiRequest<WalletPaymentResponse>(`/wallet/wallets/${walletId}/pay-visit/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get payment channels
 */
export async function getPaymentChannels(): Promise<PaymentChannel[]> {
  const response = await apiRequest<any>('/wallet/payment-channels/');
  
  // Handle both paginated and non-paginated responses
  if (Array.isArray(response)) {
    return response;
  } else if (response && response.results && Array.isArray(response.results)) {
    // Paginated response
    return response.results;
  } else {
    // Unexpected format, return empty array
    return [];
  }
}
