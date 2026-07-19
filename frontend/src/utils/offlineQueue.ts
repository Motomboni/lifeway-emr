/**
 * Queue actions when the browser is offline; sync via Offline Clinic Queue page.
 */
import { enqueueOfflineAction } from '../api/offline';

const DEVICE_ID_KEY = 'offline_device_id';

export function getOfflineDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = `web-${Date.now()}`;
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

export async function queueOfflineAction(
  action: string,
  payload: Record<string, unknown>,
): Promise<{ queued: true; id: number }> {
  const result = await enqueueOfflineAction({
    device_id: getOfflineDeviceId(),
    action,
    payload,
  });
  return { queued: true, id: result.id };
}
