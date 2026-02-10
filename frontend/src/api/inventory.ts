/**
 * Inventory API Client
 * 
 * Endpoints:
 * - GET    /api/v1/inventory/          - List inventory items
 * - POST   /api/v1/inventory/          - Create inventory (Pharmacist)
 * - GET    /api/v1/inventory/{id}/     - Get inventory
 * - PUT    /api/v1/inventory/{id}/     - Update inventory
 * - PATCH  /api/v1/inventory/{id}/     - Partial update inventory
 * - DELETE /api/v1/inventory/{id}/     - Delete inventory
 * - GET    /api/v1/inventory/low_stock/ - Get low stock items
 * - GET    /api/v1/inventory/out_of_stock/ - Get out of stock items
 * - POST   /api/v1/inventory/{id}/restock/ - Restock inventory
 * - POST   /api/v1/inventory/{id}/adjust/ - Adjust inventory
 * - GET    /api/v1/inventory/movements/ - List stock movements
 */
import { apiRequest } from '../utils/apiClient';
import {
  DrugInventory,
  DrugInventoryCreateData,
  DrugInventoryUpdateData,
  StockMovement,
  InventoryFilters,
  RestockData,
  AdjustData,
} from '../types/inventory';

// Re-export types for convenience
export type {
  DrugInventory,
  DrugInventoryCreateData,
  DrugInventoryUpdateData,
  StockMovement,
  InventoryFilters,
  RestockData,
  AdjustData,
} from '../types/inventory';

export interface PaginatedInventoryResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: DrugInventory[];
}

export interface PaginatedMovementResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: StockMovement[];
}

/**
 * Fetch inventory items (with optional filters and pagination)
 */
export async function fetchInventory(
  filters?: InventoryFilters
): Promise<DrugInventory[] | PaginatedInventoryResponse> {
  const params = new URLSearchParams();
  if (filters?.drug) params.append('drug', filters.drug.toString());
  if (filters?.low_stock) params.append('low_stock', 'true');
  if (filters?.out_of_stock) params.append('out_of_stock', 'true');
  if (filters?.search) params.append('search', filters.search);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/inventory/?${queryString}` : '/inventory/';
  return apiRequest<DrugInventory[] | PaginatedInventoryResponse>(endpoint);
}

/**
 * Get inventory item by ID
 */
export async function getInventory(inventoryId: number): Promise<DrugInventory> {
  return apiRequest<DrugInventory>(`/inventory/${inventoryId}/`);
}

/**
 * Create a new inventory item (Pharmacist only)
 */
export async function createInventory(
  inventoryData: DrugInventoryCreateData
): Promise<DrugInventory> {
  return apiRequest<DrugInventory>('/inventory/', {
    method: 'POST',
    body: JSON.stringify(inventoryData),
  });
}

/**
 * Update an inventory item
 */
export async function updateInventory(
  inventoryId: number,
  inventoryData: DrugInventoryUpdateData
): Promise<DrugInventory> {
  return apiRequest<DrugInventory>(`/inventory/${inventoryId}/`, {
    method: 'PUT',
    body: JSON.stringify(inventoryData),
  });
}

/**
 * Partially update an inventory item
 */
export async function partialUpdateInventory(
  inventoryId: number,
  inventoryData: Partial<DrugInventoryUpdateData>
): Promise<DrugInventory> {
  return apiRequest<DrugInventory>(`/inventory/${inventoryId}/`, {
    method: 'PATCH',
    body: JSON.stringify(inventoryData),
  });
}

/**
 * Delete an inventory item
 */
export async function deleteInventory(inventoryId: number): Promise<void> {
  return apiRequest<void>(`/inventory/${inventoryId}/`, {
    method: 'DELETE',
  });
}

/**
 * Get low stock items
 */
export async function fetchLowStockInventory(): Promise<
  DrugInventory[] | PaginatedInventoryResponse
> {
  return apiRequest<DrugInventory[] | PaginatedInventoryResponse>('/inventory/low_stock/');
}

/**
 * Get out of stock items
 */
export async function fetchOutOfStockInventory(): Promise<
  DrugInventory[] | PaginatedInventoryResponse
> {
  return apiRequest<DrugInventory[] | PaginatedInventoryResponse>('/inventory/out_of_stock/');
}

/**
 * Restock inventory
 */
export async function restockInventory(
  inventoryId: number,
  restockData: RestockData
): Promise<DrugInventory> {
  return apiRequest<DrugInventory>(`/inventory/${inventoryId}/restock/`, {
    method: 'POST',
    body: JSON.stringify(restockData),
  });
}

/**
 * Adjust inventory
 */
export async function adjustInventory(
  inventoryId: number,
  adjustData: AdjustData
): Promise<DrugInventory> {
  return apiRequest<DrugInventory>(`/inventory/${inventoryId}/adjust/`, {
    method: 'POST',
    body: JSON.stringify(adjustData),
  });
}

/**
 * Fetch stock movements
 */
export async function fetchStockMovements(filters?: {
  inventory?: number;
  movement_type?: string;
  prescription?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}): Promise<StockMovement[] | PaginatedMovementResponse> {
  const params = new URLSearchParams();
  if (filters?.inventory) params.append('inventory', filters.inventory.toString());
  if (filters?.movement_type) params.append('movement_type', filters.movement_type);
  if (filters?.prescription) params.append('prescription', filters.prescription.toString());
  if (filters?.date_from) params.append('date_from', filters.date_from);
  if (filters?.date_to) params.append('date_to', filters.date_to);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/inventory/movements/?${queryString}` : '/inventory/movements/';
  return apiRequest<StockMovement[] | PaginatedMovementResponse>(endpoint);
}
