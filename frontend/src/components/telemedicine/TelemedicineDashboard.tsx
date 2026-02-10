/**
 * Telemedicine Dashboard
 *
 * Doctor & patient: "Start Video Consult" and "Join Video Consult".
 * Opens meeting link in same tab or new window.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  fetchTelemedicineSessions,
  createSessionFromAppointment,
  getTelemedicineJoinLink,
} from '../../api/telemedicine';
import { TelemedicineSession } from '../../types/telemedicine';
import { useToast } from '../../hooks/useToast';
import LoadingSkeleton from '../common/LoadingSkeleton';

interface TelemedicineDashboardProps {
  userRole: string;
  appointmentId?: number | null;
  onStartConsult?: () => void;
  onJoinConsult?: (sessionId: number) => void;
}

export default function TelemedicineDashboard({
  userRole,
  appointmentId,
  onStartConsult,
  onJoinConsult,
}: TelemedicineDashboardProps) {
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();
  const [sessions, setSessions] = useState<TelemedicineSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [joiningId, setJoiningId] = useState<number | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await fetchTelemedicineSessions();
      const list = Array.isArray(data) ? data : (data as any)?.results ?? [];
      setSessions(list);
    } catch (e: any) {
      showError(e.message || 'Failed to load sessions');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleStartVideoConsult = async () => {
    if (userRole !== 'DOCTOR') {
      showError('Only doctors can start a video consult.');
      return;
    }
    if (appointmentId) {
      setCreating(true);
      try {
        const result = await createSessionFromAppointment(appointmentId, {
          recording_enabled: false,
        });
        const link = (result as any).meeting_link;
        if (link) {
          window.open(link, '_blank', 'noopener,noreferrer');
          showSuccess('Video consult started. Join via the opened link.');
        }
        if (onStartConsult) onStartConsult();
        await loadSessions();
      } catch (e: any) {
        showError(e.message || 'Failed to create session');
      } finally {
        setCreating(false);
      }
    } else {
      navigate('/telemedicine');
    }
  };

  const handleJoinVideoConsult = async (session: TelemedicineSession) => {
    setJoiningId(session.id);
    try {
      const join = await getTelemedicineJoinLink(session.id);
      if (onJoinConsult) {
        onJoinConsult(session.id);
      } else if (join.meeting_link) {
        window.location.href = join.meeting_link;
      } else {
        navigate(`/telemedicine/room/${session.id}`);
      }
      showSuccess('Joining video consult...');
    } catch (e: any) {
      showError(e.message || 'Failed to join');
    } finally {
      setJoiningId(null);
    }
  };

  if (loading) {
    return <LoadingSkeleton />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-4">
        {userRole === 'DOCTOR' && (
          <button
            type="button"
            onClick={handleStartVideoConsult}
            disabled={creating || (!!appointmentId && !appointmentId)}
            className="min-h-[48px] min-w-[180px] px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Start Video Consult'}
          </button>
        )}
      </div>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Your sessions</h3>
        {sessions.length === 0 ? (
          <p className="text-gray-500">No telemedicine sessions yet.</p>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 overflow-hidden">
            {sessions.map((session) => (
              <li
                key={session.id}
                className="flex items-center justify-between gap-4 p-4 bg-white hover:bg-gray-50"
              >
                <div>
                  <p className="font-medium text-gray-900">
                    {session.patient_name ?? `Session #${session.id}`}
                  </p>
                  <p className="text-sm text-gray-500">
                    {session.status} · {session.scheduled_start ? new Date(session.scheduled_start).toLocaleString() : ''}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleJoinVideoConsult(session)}
                  disabled={joiningId === session.id}
                  className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-400 disabled:opacity-50"
                >
                  {joiningId === session.id ? 'Joining...' : 'Join Video Consult'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
