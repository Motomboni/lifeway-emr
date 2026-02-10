/**
 * TypeScript types for Inventory Management
 */

export interface DrugInventory {
  id: number;
  drug: number;
  drug_name?: string;
  drug_code?: string;
  current_stock: number;
  unit: string;
  reorder_level: number;
  batch_number?: string;
  expiry_date?: string | null;
  location?: string;
  last_restocked_at?: string | null;
  last_restocked_by?: number | null;
  last_restocked_by_name?: string | null;
  is_low_stock?: boolean;
  is_out_of_stock?: boolean;
  created_at: string;
  updated_at: string;
}

export interface DrugInventoryCreateData {
  drug: number;
  current_stock: number;
  unit: string;
  reorder_level: number;
  batch_number?: string;
  expiry_date?: string;
  location?: string;
}

export interface DrugInventoryUpdateData {
  current_stock?: number;
  unit?: string;
  reorder_level?: number;
  batch_number?: string;
  expiry_date?: string;
  location?: string;
}

export interface StockMovement {
  id: number;
  inventory: number;
  inventory_drug_name?: string;
  movement_type: 'IN' | 'OUT' | 'ADJUSTMENT' | 'DISPENSED' | 'RETURNED' | 'EXPIRED' | 'DAMAGED';
  quantity: number;
  prescription?: number | null;
  prescription_id?: number | null;
  reference_number?: string;
  notes?: string;
  created_by: number;
  created_by_name?: string;
  created_at: string;
}

export interface StockMovementCreateData {
  inventory: number;
  movement_type: 'IN' | 'OUT' | 'ADJUSTMENT' | 'DISPENSED' | 'RETURNED' | 'EXPIRED' | 'DAMAGED';
  quantity: number;
  prescription?: number | null;
  reference_number?: string;
  notes?: string;
}

export interface InventoryFilters {
  drug?: number;
  low_stock?: boolean;
  out_of_stock?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface RestockData {
  quantity: number;
  reference_number?: string;
  notes?: string;
}

export interface AdjustData {
  quantity: number;
  reason?: string;
  notes?: string;
}
