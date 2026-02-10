/**
 * Patient Portal - Telemedicine Page
 * 
 * Allows patients to view and join their telemedicine sessions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchTelemedicineSessions,
  getTelemedicineAccessToken,
  leaveTelemedicineSession,
} from '../api/telemedicine';
import { TelemedicineSession } from '../types/telemedicine';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import VideoCall from '../components/telemedicine/VideoCall';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalTelemedicinePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [sessions, setSessions] = useState<TelemedicineSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<TelemedicineSession | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadSessions();
  }, [user, navigate]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await fetchTelemedicineSessions();
      const sessionsArray = Array.isArray(data) 
        ? data 
        : ((data as any)?.results || []);
      setSessions(sessionsArray);
    } catch (error: any) {
      showError(error.message || 'Failed to load telemedicine sessions');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinSession = async (session: TelemedicineSession) => {
    try {
      // Get access token
      const tokenData = await getTelemedicineAccessToken(session.id);
      setAccessToken(tokenData.token);
      setActiveSession(session);
      showSuccess('Joining session...');
    } catch (error: any) {
      showError(error.message || 'Failed to join session');
    }
  };

  const handleLeaveSession = async () => {
    if (!activeSession) return;
    
    try {
      await leaveTelemedicineSession(activeSession.id);
      setActiveSession(null);
      setAccessToken(null);
      showSuccess('Left session successfully');
      loadSessions();
    } catch (error: any) {
      showError(error.message || 'Failed to leave session');
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'IN_PROGRESS':
        return styles.open;
      case 'COMPLETED':
        return styles.closed;
      case 'SCHEDULED':
      default:
        return styles.scheduled;
    }
  };

  if (loading) {
    return (
      <div className={styles.dashboard}>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  // Show video call if active session
  if (activeSession && accessToken) {
    return (
      <div className={styles.dashboard}>
        <header className={styles.header}>
          <div className={styles.headerContent}>
            <div>
              <h1>Video Consultation</h1>
              <p>Session #{activeSession.id}</p>
            </div>
            <button
              className={styles.logoutButton}
              onClick={handleLeaveSession}
            >
              Leave Session
            </button>
          </div>
        </header>
        <VideoCall
          token={accessToken}
          roomName={activeSession.twilio_room_name || ''}
          onLeave={handleLeaveSession}
        />
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>Telemedicine Sessions</h1>
            <p>View and join your video consultations</p>
          </div>
          <button
            className={styles.viewAllButton}
            onClick={() => navigate('/patient-portal/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      <div className={styles.content}>
        <section className={styles.section}>
          {sessions.length === 0 ? (
            <p className={styles.emptyText}>No telemedicine sessions found.</p>
          ) : (
            <div className={styles.list}>
              {sessions.map((session) => (
                <div key={session.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Session #{session.id}</h3>
                    <span className={`${styles.badge} ${getStatusBadgeClass(session.status)}`}>
                      {session.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    {session.doctor_name && (
                      <p><strong>Doctor:</strong> {session.doctor_name}</p>
                    )}
                    {session.scheduled_start && (
                      <p><strong>Scheduled:</strong> {formatDateTime(session.scheduled_start)}</p>
                    )}
                    {session.actual_start && (
                      <p><strong>Started:</strong> {formatDateTime(session.actual_start)}</p>
                    )}
                    {session.notes && (
                      <p><strong>Notes:</strong> {session.notes}</p>
                    )}
                  </div>
                  {(session.status === 'SCHEDULED' || session.status === 'IN_PROGRESS') && (
                    <button
                      className={styles.viewButton}
                      onClick={() => handleJoinSession(session)}
                    >
                      Join Session
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
