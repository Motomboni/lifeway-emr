/**
 * Drug/Medication types
 */

export interface Drug {
  id: number;
  name: string;
  generic_name?: string;
  drug_code?: string;
  drug_class?: string;
  dosage_forms?: string;
  common_dosages?: string;
  cost_price?: number;
  sales_price?: number;
  profit?: number;
  profit_margin?: number;
  description?: string;
  is_active: boolean;
  created_by: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface DrugCreateData {
  name: string;
  generic_name?: string;
  drug_code?: string;
  drug_class?: string;
  dosage_forms?: string;
  common_dosages?: string;
  cost_price?: number;
  sales_price?: number;
  description?: string;
  is_active?: boolean;
}

export interface DrugUpdateData extends Partial<DrugCreateData> {
  name?: string;
  is_active?: boolean;
}
