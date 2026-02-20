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
  /** Current stock (from inventory) - for doctors to make informed prescribing decisions */
  current_stock?: number | null;
  /** Unit e.g. tablets, units */
  drug_unit?: string | null;
  /** Expiry date ISO string */
  drug_expiry_date?: string | null;
  is_out_of_stock?: boolean | null;
  is_low_stock?: boolean | null;
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
