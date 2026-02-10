/**
 * Payment Processing Page
 * 
 * DEPRECATED: This standalone page conflicts with visit-scoped billing workflow.
 * Per billing_context.md: Billing is VISIT-SCOPED and must be accessed from Visit Details Page.
 * 
 * This page now redirects to the visits list for visit-scoped billing access.
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
  const { showError, showSuccess } = useToast();

  useEffect(() => {
    // Redirect to visits list for visit-scoped billing access
    // Per billing_context.md: Billing is VISIT-SCOPED and must be accessed from Visit Details Page
    showSuccess('Billing is visit-scoped. Redirecting to visits list...');
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
          <h2>Redirecting to Visits List...</h2>
          <p>Billing is visit-scoped. Please access billing from the Visit Details page.</p>
          <LoadingSkeleton count={3} />
        </div>
      </div>
    </div>
  );
}
