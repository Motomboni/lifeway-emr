/**
 * Service Catalog types for admin-managed billable services.
 */

export type DepartmentCode =
  | 'CONSULTATION'
  | 'LAB'
  | 'PHARMACY'
  | 'RADIOLOGY'
  | 'PROCEDURE';

export type WorkflowType =
  | 'GOPD_CONSULT'
  | 'LAB_ORDER'
  | 'DRUG_DISPENSE'
  | 'PROCEDURE'
  | 'RADIOLOGY_STUDY'
  | 'IVF'
  | 'INJECTION'
  | 'DRESSING'
  | 'VACCINATION'
  | 'PHYSIOTHERAPY'
  | 'OTHER';

export interface ServiceCatalogItem {
  id: number;
  department: DepartmentCode;
  service_code: string;
  name: string;
  amount: string;
  description: string;
  category: string;
  workflow_type: WorkflowType;
  requires_visit: boolean;
  requires_consultation: boolean;
  auto_bill: boolean;
  bill_timing: string;
  restricted_service_flag: boolean;
  allowed_roles: string[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
  display: string;
}

export interface ServiceCatalogCreate {
  service_code: string;
  name: string;
  department: DepartmentCode;
  workflow_type: WorkflowType;
  amount: string;
  description?: string;
  category?: string;
  is_active?: boolean;
  requires_visit?: boolean;
  requires_consultation?: boolean;
  auto_bill?: boolean;
  bill_timing?: string;
  restricted_service_flag?: boolean;
  allowed_roles?: string[];
}

export interface ServiceCatalogUpdate extends Partial<ServiceCatalogCreate> {}

export interface ServiceCatalogListResponse {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: ServiceCatalogItem[];
}

export interface ServiceCatalogChoices {
  departments: { value: string; label: string }[];
  categories: { value: string; label: string }[];
  workflow_types: { value: string; label: string }[];
  bill_timing: { value: string; label: string }[];
}
