/**
 * Audit Log API Client
 * 
 * Read-only access to audit logs for compliance.
 */
import { apiRequest } from '../utils/apiClient';

export interface AuditLog {
  id: number;
  user: number;
  user_name?: string;
  user_email?: string;
  user_role: string;
  action: string;
  visit_id?: number;
  resource_type: string;
  resource_id?: number;
  ip_address?: string;
  user_agent?: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface AuditLogFilters {
  visit_id?: number;
  user?: number;
  action?: string;
  resource_type?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedAuditLogs {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLog[];
}

/**
 * Fetch audit logs with optional filters
 */
export async function fetchAuditLogs(filters?: AuditLogFilters): Promise<AuditLog[] | PaginatedAuditLogs> {
  const params = new URLSearchParams();
  if (filters?.visit_id) params.append('visit_id', filters.visit_id.toString());
  if (filters?.user) params.append('user', filters.user.toString());
  if (filters?.action) params.append('action', filters.action);
  if (filters?.resource_type) params.append('resource_type', filters.resource_type);
  if (filters?.date_from) params.append('date_from', filters.date_from);
  if (filters?.date_to) params.append('date_to', filters.date_to);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/audit-logs/?${queryString}` : '/audit-logs/';
  return apiRequest<AuditLog[] | PaginatedAuditLogs>(endpoint);
}
