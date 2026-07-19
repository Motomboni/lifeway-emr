/**
 * Payment Processing Page
 *
 * Billing is visit-scoped — redirect to the visits list so staff open billing
 * from each visit's details page (matches production Lifeway workflow).
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/PaymentProcessing.module.css';

export default function PaymentProcessingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showSuccess } = useToast();

  useEffect(() => {
    showSuccess('Billing is visit-scoped. Opening visits list…');
    navigate('/visits', { replace: true });
  }, [navigate, showSuccess]);

  if (user?.role !== 'RECEPTIONIST') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Receptionists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.paymentProcessingPage}>
      <BackToDashboard />
      <div className={styles.content}>
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>Redirecting to Visits List…</h2>
          <p>Billing is visit-scoped. Open a visit and use the Billing section to collect payment.</p>
          <LoadingSkeleton count={3} />
        </div>
      </div>
    </div>
  );
}
