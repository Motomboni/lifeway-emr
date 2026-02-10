/**
 * API client functions for Timeline Events.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface TimelineEvent {
  id: number;
  visit: number;
  event_type: string;
  event_type_display: string;
  timestamp: string;
  actor: number | null;
  actor_full_name: string | null;
  actor_role: string;
  description: string;
  content_type: number | null;
  object_id: number | null;
  source_object_url: string | null;
  metadata: Record<string, any>;
}

/**
 * Fetch timeline events for a visit.
 */
export const fetchTimelineEvents = async (visitId: number): Promise<TimelineEvent[]> => {
  return apiRequest<TimelineEvent[]>(`/visits/${visitId}/timeline/`);
};

