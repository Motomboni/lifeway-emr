/**
 * Patient Portal Dashboard
 * 
 * Main landing page for patients after login.
 * Shows patient's own records, appointments, and results.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getPatientProfile,
  getPatientVisits,
  getPatientAppointments,
  getPatientLabResults,
  getPatientRadiologyResults,
  getPatientPrescriptions,
} from '../api/patientPortal';
import { Patient } from '../types/patient';
import { Visit } from '../types/visit';
import { Appointment } from '../types/appointment';
import { LabResult } from '../types/lab';
import { Prescription } from '../types/prescription';
import { RadiologyResult } from '../types/patientPortal';
import { useToast } from '../hooks/useToast';
import { logger } from '../utils/logger';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useToast();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [visits, setVisits] = useState<Visit[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [radiologyResults, setRadiologyResults] = useState<RadiologyResult[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const lastLoadTimeRef = React.useRef<number>(0);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/dashboard', { replace: true });
      return;
    }
    // Only load if we're actually on the patient portal dashboard route
    if (location.pathname === '/patient-portal/dashboard') {
      const now = Date.now();
      const lastLoadTime = lastLoadTimeRef.current;
      const timeSinceLastLoad = lastLoadTime === 0 ? Infinity : now - lastLoadTime;
      
      // Reload if it's been more than 500ms since last load (prevents rapid duplicate calls)
      if (timeSinceLastLoad > 500) {
        loadDashboardData();
        lastLoadTimeRef.current = now;
      }
    }
  }, [user, navigate, location.pathname]);

  const loadDashboardData = async () => {
    try {
      logger.debug('Patient Portal Dashboard: Starting data load...');
      setLoading(true);
      // Use Promise.allSettled to handle partial failures gracefully
      const results = await Promise.allSettled([
        getPatientProfile(),
        getPatientVisits(),
        getPatientAppointments(),
        getPatientLabResults(),
        getPatientRadiologyResults(),
        getPatientPrescriptions(),
      ]);
      logger.debug('Patient Portal Dashboard: Data load complete');

      // Handle each result
      if (results[0].status === 'fulfilled') {
        setPatient(results[0].value);
      } else {
        logger.warn('Failed to load profile:', results[0].reason);
      }

      if (results[1].status === 'fulfilled') {
        setVisits(results[1].value);
      } else {
        console.warn('Failed to load visits:', results[1].reason);
      }

      if (results[2].status === 'fulfilled') {
        setAppointments(results[2].value);
      } else {
        console.warn('Failed to load appointments:', results[2].reason);
        setAppointments([]); // Set empty array on error
      }

      if (results[3].status === 'fulfilled') {
        setLabResults(results[3].value);
      } else {
        console.warn('Failed to load lab results:', results[3].reason);
        setLabResults([]); // Set empty array on error
      }

      if (results[4].status === 'fulfilled') {
        setRadiologyResults(results[4].value);
      } else {
        console.warn('Failed to load radiology results:', results[4].reason);
        setRadiologyResults([]); // Set empty array on error
      }

      if (results[5].status === 'fulfilled') {
        setPrescriptions(results[5].value);
      } else {
        console.warn('Failed to load prescriptions:', results[5].reason);
        setPrescriptions([]); // Set empty array on error
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load dashboard data';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
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
            <h1>Patient Portal</h1>
            <p>Welcome, {patient?.first_name} {patient?.last_name}</p>
          </div>
          <button className={styles.logoutButton} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className={styles.content}>
        {/* Patient Information */}
        <section className={styles.section}>
          <h2>My Information</h2>
          <div className={styles.infoCard}>
            <div className={styles.infoRow}>
              <strong>Patient ID:</strong> {patient?.patient_id}
            </div>
            {patient?.date_of_birth && (
              <div className={styles.infoRow}>
                <strong>Date of Birth:</strong> {formatDate(patient.date_of_birth)}
              </div>
            )}
            {patient?.phone && (
              <div className={styles.infoRow}>
                <strong>Phone:</strong> {patient.phone}
              </div>
            )}
            {patient?.email && (
              <div className={styles.infoRow}>
                <strong>Email:</strong> {patient.email}
              </div>
            )}
            {patient?.blood_group && (
              <div className={styles.infoRow}>
                <strong>Blood Group:</strong> {patient.blood_group}
              </div>
            )}
            {patient?.allergies && (
              <div className={styles.infoRow}>
                <strong>Allergies:</strong> {patient.allergies}
              </div>
            )}
          </div>
        </section>

        {/* Quick Stats */}
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>📋</div>
            <div className={styles.statInfo}>
              <h3>{visits.length}</h3>
              <p>Total Visits</p>
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>📅</div>
            <div className={styles.statInfo}>
              <h3>{appointments.filter(a => a.status === 'SCHEDULED' || a.status === 'CONFIRMED').length}</h3>
              <p>Upcoming Appointments</p>
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>🧪</div>
            <div className={styles.statInfo}>
              <h3>{labResults.length}</h3>
              <p>Lab Results</p>
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>📷</div>
            <div className={styles.statInfo}>
              <h3>{radiologyResults.length}</h3>
              <p>Radiology Results</p>
            </div>
          </div>
          <div 
            className={styles.statCard}
            onClick={() => navigate('/wallet')}
            style={{ cursor: 'pointer' }}
          >
            <div className={styles.statIcon}>💳</div>
            <div className={styles.statInfo}>
              <h3>Wallet</h3>
              <p>View & Top Up</p>
            </div>
          </div>
        </div>

        {/* Recent Visits */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Recent Visits</h2>
            <button
              className={styles.viewAllButton}
              onClick={() => navigate('/patient-portal/visits')}
            >
              View All
            </button>
          </div>
          {visits.length === 0 ? (
            <p className={styles.emptyText}>No visits found.</p>
          ) : (
            <div className={styles.list}>
              {visits.slice(0, 5).map((visit) => (
                <div key={visit.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Visit #{visit.id}</h3>
                    <span className={`${styles.badge} ${visit.status === 'CLOSED' ? styles.closed : styles.open}`}>
                      {visit.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Date:</strong> {formatDate(visit.created_at)}</p>
                    <p><strong>Payment Status:</strong> {visit.payment_status}</p>
                  </div>
                  <button
                    className={styles.viewButton}
                    onClick={() => navigate(`/patient-portal/visits/${visit.id}`)}
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Upcoming Appointments */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Upcoming Appointments</h2>
            <button
              className={styles.viewAllButton}
              onClick={() => navigate('/patient-portal/appointments')}
            >
              View All
            </button>
          </div>
          {appointments.filter(a => a.status === 'SCHEDULED' || a.status === 'CONFIRMED').length === 0 ? (
            <p className={styles.emptyText}>No upcoming appointments.</p>
          ) : (
            <div className={styles.list}>
              {appointments
                .filter(a => a.status === 'SCHEDULED' || a.status === 'CONFIRMED')
                .slice(0, 5)
                .map((appointment) => (
                  <div key={appointment.id} className={styles.card}>
                    <div className={styles.cardHeader}>
                      <h3>{formatDate(appointment.appointment_date)}</h3>
                      <span className={`${styles.badge} ${styles.scheduled}`}>
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
                    </div>
                  </div>
                ))}
            </div>
          )}
        </section>

        {/* Recent Lab Results */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Recent Lab Results</h2>
            <button
              className={styles.viewAllButton}
              onClick={() => navigate('/patient-portal/lab-results')}
            >
              View All
            </button>
          </div>
          {labResults.length === 0 ? (
            <p className={styles.emptyText}>No lab results found.</p>
          ) : (
            <div className={styles.list}>
              {labResults.slice(0, 5).map((result) => (
                <div key={result.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Lab Result #{result.id}</h3>
                    <span className={`${styles.badge} ${
                      result.abnormal_flag === 'CRITICAL' ? styles.critical :
                      result.abnormal_flag === 'ABNORMAL' ? styles.abnormal :
                      styles.normal
                    }`}>
                      {result.abnormal_flag}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Date:</strong> {formatDateTime(result.recorded_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Quick Links */}
        <section className={styles.section}>
          <h2>Quick Links</h2>
          <div className={styles.quickLinks}>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/visits')}
            >
              📋 All Visits
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/appointments')}
            >
              📅 Appointments
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/lab-results')}
            >
              🧪 Lab Results
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/radiology-results')}
            >
              📷 Radiology Results
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/prescriptions')}
            >
              💊 Prescriptions
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/medical-history')}
            >
              📜 Medical History
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/patient-portal/telemedicine')}
            >
              📹 Telemedicine
            </button>
            <button
              className={styles.quickLinkButton}
              onClick={() => navigate('/wallet')}
            >
              💳 My Wallet
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
