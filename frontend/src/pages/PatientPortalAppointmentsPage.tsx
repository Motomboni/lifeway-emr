/**
 * Patient Portal - Appointments Page
 * 
 * Shows all patient's appointments.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientAppointments } from '../api/patientPortal';
import { Appointment } from '../types/appointment';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalAppointmentsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadAppointments();
  }, [user, navigate]);

  const loadAppointments = async () => {
    try {
      setLoading(true);
      const data = await getPatientAppointments();
      setAppointments(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load appointments';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
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
      case 'SCHEDULED':
      case 'CONFIRMED':
        return styles.scheduled;
      case 'COMPLETED':
        return styles.open;
      case 'CANCELLED':
      case 'NO_SHOW':
        return styles.closed;
      default:
        return styles.open;
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
            <h1>My Appointments</h1>
            <p>View all your scheduled appointments</p>
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
          {appointments.length === 0 ? (
            <p className={styles.emptyText}>No appointments found.</p>
          ) : (
            <div className={styles.list}>
              {appointments.map((appointment) => (
                <div key={appointment.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>{formatDate(appointment.appointment_date)}</h3>
                    <span className={`${styles.badge} ${getStatusBadgeClass(appointment.status)}`}>
                      {appointment.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    {appointment.doctor_name && (
                      <p><strong>Doctor:</strong> {appointment.doctor_name}</p>
                    )}
                    {appointment.reason && (
                      <p><strong>Reason:</strong> {appointment.reason}</p>
                    )}
                    {appointment.notes && (
                      <p><strong>Notes:</strong> {appointment.notes}</p>
                    )}
                    <p><strong>Duration:</strong> {appointment.duration_minutes} minutes</p>
                    <p><strong>Created:</strong> {formatDateTime(appointment.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
