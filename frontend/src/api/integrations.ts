import { apiRequest } from '../utils/apiClient';

export interface ExternalHealthHub {
  hub_type: string;
  base_url: string;
  api_key_env: string;
  is_enabled: boolean;
  last_sync_at: string | null;
  config: Record<string, unknown>;
}

export async function fetchIntegrationHubs(): Promise<ExternalHealthHub[]> {
  return apiRequest<ExternalHealthHub[]>('/integrations/hubs/');
}

export async function updateIntegrationHub(
  hubType: string,
  data: Partial<Pick<ExternalHealthHub, 'base_url' | 'api_key_env' | 'is_enabled' | 'config'>> & {
    mark_synced?: boolean;
  },
): Promise<ExternalHealthHub> {
  return apiRequest<ExternalHealthHub>(`/integrations/hubs/${hubType}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
