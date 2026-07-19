import { apiRequest } from '../utils/apiClient';

export interface NafdacFormularyEntry {
  id: number;
  nafdac_reg_no: string;
  product_name: string;
  active_ingredient: string;
  dosage_form: string;
  strength: string;
  manufacturer: string;
  nhia_tariff_code: string;
  is_essential_medicine: boolean;
  is_active: boolean;
}

export async function fetchNafdacFormulary(params?: {
  search?: string;
  nhia_tariff_only?: boolean;
}): Promise<NafdacFormularyEntry[]> {
  const qs = new URLSearchParams();
  if (params?.search) qs.set('search', params.search);
  if (params?.nhia_tariff_only) qs.set('nhia_tariff_only', 'true');
  const query = qs.toString();
  return apiRequest<NafdacFormularyEntry[]>(
    `/pharmacy/nafdac-formulary/${query ? `?${query}` : ''}`,
  );
}
