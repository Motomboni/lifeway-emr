/**
 * Billing API Client
 * 
 * All endpoints are visit-scoped:
 * - GET /api/v1/visits/{visit_id}/billing/summary/
 * - POST /api/v1/visits/{visit_id}/billing/charges/
 * - POST /api/v1/visits/{visit_id}/billing/payments/
 * - POST /api/v1/visits/{visit_id}/billing/wallet-debit/
 * - POST /api/v1/visits/{visit_id}/billing/insurance/
 * - GET /api/v1/visits/{visit_id}/billing/receipt/
 * - GET /api/v1/visits/{visit_id}/billing/invoice/
 * - POST /api/v1/visits/{visit_id}/billing/receipt/send-email/
 * - POST /api/v1/visits/{visit_id}/billing/invoice/send-email/
 */
import { apiRequest } from '../utils/apiClient';

/** Payment gates: pre-service payment rules (registration & consultation must be paid before access) */
export interface PaymentGates {
  registration_paid: boolean;
  consultation_paid: boolean;
  can_access_consultation: boolean;
  can_doctor_start_encounter: boolean;
}

export interface BillingSummary {
  total_charges: string;
  total_payments: string;
  total_wallet_debits: string;
  has_retainership: boolean;
  retainership_discount: string;
  retainership_discount_percentage: string;
  charges_after_retainership: string;
  has_insurance: boolean;
  insurance_status: string | null;
  insurance_amount: string;
  insurance_coverage_type: string | null;
  patient_payable: string;
  outstanding_balance: string;
  payment_status: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED' | 'PENDING' | 'CLEARED';
  is_fully_covered_by_insurance: boolean;
  can_be_cleared: boolean;
  computation_timestamp: string;
  visit_id: number;
  /** Strict payment rules: registration & consultation gates */
  payment_gates?: PaymentGates;
}

export interface VisitCharge {
  id: number;
  visit_id: number;
  category: 'CONSULTATION' | 'LAB' | 'RADIOLOGY' | 'DRUG' | 'PROCEDURE' | 'MISC';
  description: string;
  amount: string;
  created_by_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChargeCreateData {
  amount: string;
  description: string;
}

export interface PaymentCreateData {
  amount: string;
  payment_method: 'CASH' | 'POS' | 'TRANSFER' | 'PAYSTACK' | 'WALLET' | 'INSURANCE';
  transaction_reference?: string;
  notes?: string;
  status?: 'PENDING' | 'CLEARED';
}

export interface WalletDebitData {
  wallet_id: number;
  amount: string;
  description?: string;
}

export interface InsuranceCreateData {
  provider: number;
  policy_number: string;
  coverage_type: 'FULL' | 'PARTIAL';
  coverage_percentage: number;
  notes?: string;
}

/**
 * Get billing summary for a visit
 */
export async function getBillingSummary(visitId: number): Promise<BillingSummary> {
  return apiRequest<BillingSummary>(`/visits/${visitId}/billing/summary/`);
}

/** Pending queue item (one BillingLineItem) */
export interface PendingQueueItem {
  id: number;
  department: string;
  description: string;
  amount: string;
  amount_paid: string;
  outstanding: string;
  status: 'PENDING' | 'PARTIALLY_PAID' | 'PAID';
}

/** Pending queue visit entry (Receptionist central billing queue) */
export interface PendingQueueVisit {
  visit_id: number;
  patient: { id: number; name: string };
  items: PendingQueueItem[];
  total_pending: string;
  consultation_id: number | null;
  visit_status: string;
}

export interface BillingPendingQueueResponse {
  visits: PendingQueueVisit[];
}

/**
 * Get central billing pending queue (Receptionist only)
 */
export async function getBillingPendingQueue(): Promise<BillingPendingQueueResponse> {
  return apiRequest<BillingPendingQueueResponse>('/billing/pending-queue/');
}

/**
 * Create a MISC charge for a visit
 */
export async function createCharge(visitId: number, data: ChargeCreateData): Promise<VisitCharge> {
  return apiRequest<VisitCharge>(`/visits/${visitId}/billing/charges/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Create a payment for a visit
 */
export async function createPayment(visitId: number, data: PaymentCreateData): Promise<any> {
  return apiRequest(`/visits/${visitId}/billing/payments/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Create a wallet debit payment for a visit
 */
export async function createWalletDebit(visitId: number, data: WalletDebitData): Promise<any> {
  return apiRequest(`/visits/${visitId}/billing/wallet-debit/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Create insurance record for a visit
 */
export async function createInsurance(visitId: number, data: InsuranceCreateData): Promise<any> {
  return apiRequest(`/visits/${visitId}/billing/insurance/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get list of HMO Providers
 */
export async function getHMOProviders(): Promise<any[]> {
  return apiRequest<any[]>(`/billing/hmo-providers/`);
}

/**
 * Get charges for a visit
 */
export async function getVisitCharges(visitId: number): Promise<VisitCharge[]> {
  return apiRequest<VisitCharge[]>(`/visits/${visitId}/billing/charges/`);
}

/**
 * Get insurance record for a visit
 */
export async function getVisitInsurance(visitId: number): Promise<any> {
  return apiRequest(`/visits/${visitId}/insurance/`);
}

/**
 * Update insurance record (for approval)
 */
export async function updateInsurance(visitId: number, insuranceId: number, data: {
  approval_status?: 'PENDING' | 'APPROVED' | 'REJECTED';
  approved_amount?: string;
  approval_reference?: string;
  rejection_reason?: string;
}): Promise<any> {
  return apiRequest(`/visits/${visitId}/insurance/${insuranceId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Initialize Paystack payment
 */
export async function initializePaystackPayment(visitId: number, data: {
  visit_id: number;
  amount: string;
  callback_url?: string;
  customer_email?: string;
}): Promise<any> {
  return apiRequest(`/visits/${visitId}/payment-intents/initialize/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Verify Paystack payment
 */
export async function verifyPaystackPayment(visitId: number, paymentIntentId: number, reference: string): Promise<any> {
  return apiRequest(`/visits/${visitId}/payment-intents/${paymentIntentId}/verify/`, {
    method: 'POST',
    body: JSON.stringify({ reference }),
  });
}

/**
 * Get payment intents for a visit
 */
export async function getPaymentIntents(visitId: number): Promise<any[]> {
  return apiRequest<any[]>(`/visits/${visitId}/payment-intents/`);
}

// ============================================================================
// Service Catalog API
// ============================================================================

export interface Service {
  id?: number;
  department: 'CONSULTATION' | 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  service_code: string;
  service_name?: string;  // Old field (kept for backward compatibility)
  name?: string;  // New field from ServiceCatalog
  amount: string;
  description?: string;
  is_active?: boolean;
  display?: string;
  category?: string;
  workflow_type?: string;
  requires_visit?: boolean;
  requires_consultation?: boolean;
  allowed_roles?: string[];  // Roles that can order this service
  /** Drug availability (PHARMACY/DRUG only): current stock quantity */
  drug_availability?: number | null;
  /** Drug expiry date ISO string (PHARMACY/DRUG only) */
  drug_expiry_date?: string | null;
  /** Drug unit e.g. tablets, units (PHARMACY/DRUG only) */
  drug_unit?: string | null;
  /** True if out of stock or expired (PHARMACY/DRUG only) */
  is_out_of_stock?: boolean | null;
  /** True if low stock (PHARMACY/DRUG only) */
  is_low_stock?: boolean | null;
}

export interface ServiceCatalogResponse {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: Service[];
}

export interface ServiceSearchResponse {
  results: Service[];
}

/**
 * Quick search for services (autocomplete/dropdown)
 * GET /api/v1/billing/service-catalog/search/?q=consultation&department=PROCEDURE&limit=20
 */
export async function searchServices(params: {
  q: string;
  department?: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  limit?: number;
}): Promise<ServiceSearchResponse> {
  const searchParams = new URLSearchParams();
  searchParams.append('q', params.q);
  if (params.department) searchParams.append('department', params.department);
  if (params.limit) searchParams.append('limit', params.limit.toString());
  
  return apiRequest<ServiceSearchResponse>(`/billing/service-catalog/search/?${searchParams}`);
}

/**
 * Get service catalog with pagination and filters
 * GET /api/v1/billing/service-catalog/?search=dental&department=PROCEDURE&page=1&page_size=50
 */
export async function getServiceCatalog(params?: {
  search?: string;
  department?: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE' | 'ALL';
  active_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ServiceCatalogResponse> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.append('search', params.search);
  if (params?.department) searchParams.append('department', params.department);
  if (params?.active_only !== undefined) searchParams.append('active_only', params.active_only.toString());
  if (params?.page) searchParams.append('page', params.page.toString());
  if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
  
  const queryString = searchParams.toString();
  return apiRequest<ServiceCatalogResponse>(`/billing/service-catalog/${queryString ? `?${queryString}` : ''}`);
}

/**
 * Get service price by code
 * GET /api/v1/billing/service-price/?department=PROCEDURE&service_code=CONS-001
 */
export async function getServicePrice(params: {
  department: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  service_code: string;
}): Promise<Service> {
  const searchParams = new URLSearchParams();
  searchParams.append('department', params.department);
  searchParams.append('service_code', params.service_code);
  
  return apiRequest<Service>(`/billing/service-price/?${searchParams}`);
}

/**
 * Add service to bill
 * POST /api/v1/billing/add-item/
 */
export interface AddBillItemData {
  visit_id: number;
  department: 'CONSULTATION' | 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  service_code: string;
  additional_data?: any;  // Optional prescription details or other service-specific data
}

export interface AddBillItemResponse {
  id: number;
  bill_id: number;
  visit_id: number;
  department: string;
  service_code: string;
  service_name: string;
  amount: string;
  status: string;
  bill_total_amount: string;
  bill_outstanding_balance: string;
  created_at: string;
}

export async function addServiceToBill(data: AddBillItemData): Promise<AddBillItemResponse> {
  return apiRequest<AddBillItemResponse>('/billing/add-item/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// Invoice/Receipt API
// ============================================================================

export interface ReceiptData {
  receipt_number: string;
  receipt_type: 'RECEIPT';
  visit_id: number;
  patient_name: string;
  patient_id: string;
  date: string;
  charges: Array<{
    category: string;
    description: string;
    amount: string;
    created_at: string;
  }>;
  payments: Array<{
    id: number;
    amount: string;
    payment_method: string;
    transaction_reference: string;
    notes?: string;
    processed_by: string;
    created_at: string;
  }>;
  total_charges: string;
  total_paid: string;
  outstanding_balance: string;
  payment_status: string;
  clinic_name: string;
  clinic_address: string;
  clinic_phone: string;
}

export interface InvoiceData {
  invoice_number: string;
  invoice_type: 'INVOICE';
  visit_id: number;
  patient_name: string;
  patient_id: string;
  insurance_provider: string;
  insurance_number: string;
  approval_status: string;
  approved_amount?: string;
  coverage_type: string;
  coverage_percentage: number;
  date: string;
  charges: Array<{
    category: string;
    description: string;
    amount: string;
    created_at: string;
  }>;
  total_charges: string;
  insurance_amount: string;
  patient_payable: string;
  outstanding_balance: string;
  payment_status: string;
  clinic_name: string;
  clinic_address: string;
  clinic_phone: string;
}

/**
 * Get receipt data for a visit
 */
export async function getReceipt(visitId: number, paymentId?: number): Promise<ReceiptData> {
  const url = paymentId
    ? `/visits/${visitId}/billing/receipt/`
    : `/visits/${visitId}/billing/receipt/`;
  
  const options = paymentId
    ? {
        method: 'POST',
        body: JSON.stringify({ payment_id: paymentId }),
      }
    : undefined;
  
  return apiRequest<ReceiptData>(url, options);
}

/**
 * Get invoice data for a visit
 */
export async function getInvoice(visitId: number): Promise<InvoiceData> {
  return apiRequest<InvoiceData>(`/visits/${visitId}/billing/invoice/`);
}

/**
 * Send receipt via email
 */
export async function sendReceiptEmail(visitId: number, email: string): Promise<any> {
  return apiRequest(`/visits/${visitId}/billing/receipt/send-email/`, {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

/**
 * Send invoice via email
 */
export async function sendInvoiceEmail(visitId: number, email: string): Promise<any> {
  return apiRequest(`/visits/${visitId}/billing/invoice/send-email/`, {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

