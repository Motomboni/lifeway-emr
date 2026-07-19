/**
 * Patient Portal - Telemedicine Page
 *
 * Allows patients to view and join their telemedicine sessions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchTelemedicineSessions } from '../api/telemedicine';
import { TelemedicineSession } from '../types/telemedicine';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalTelemedicinePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [sessions, setSessions] = useState<TelemedicineSession[]>([]);
  const [loading, setLoading] = useState(true);

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
        : ((data as { results?: TelemedicineSession[] })?.results || []);
      setSessions(sessionsArray);
    } catch (error: unknown) {
      showError(error instanceof Error ? error.message : 'Failed to load telemedicine sessions');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinSession = (session: TelemedicineSession) => {
    navigate(`/telemedicine/room/${session.id}`);
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
            type="button"
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
                    {(session.doctor_display_name || session.doctor_name) && (
                      <p>
                        <strong>Doctor:</strong>{' '}
                        {session.doctor_display_name || session.doctor_name}
                      </p>
                    )}
                    {session.scheduled_start && (
                      <p>
                        <strong>Scheduled:</strong> {formatDateTime(session.scheduled_start)}
                      </p>
                    )}
                    {session.actual_start && (
                      <p>
                        <strong>Started:</strong> {formatDateTime(session.actual_start)}
                      </p>
                    )}
                    {session.notes && (
                      <p>
                        <strong>Notes:</strong> {session.notes}
                      </p>
                    )}
                  </div>
                  {(session.status === 'SCHEDULED' || session.status === 'IN_PROGRESS') && (
                    <button
                      type="button"
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
