import { apiRequest } from '../utils/apiClient';

export interface OfflineQueueEntry {
  id: number;
  device_id: string;
  action: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
}

export async function fetchOfflineQueue(deviceId?: string): Promise<OfflineQueueEntry[]> {
  const qs = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : '';
  return apiRequest<OfflineQueueEntry[]>(`/offline/queue/${qs}`);
}

export async function enqueueOfflineAction(data: {
  device_id: string;
  action: string;
  payload?: Record<string, unknown>;
}): Promise<{ id: number; status: string }> {
  return apiRequest('/offline/queue/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function syncOfflineEntry(entryId: number): Promise<{ id: number; status: string }> {
  return apiRequest(`/offline/queue/${entryId}/sync/`, { method: 'POST' });
}
