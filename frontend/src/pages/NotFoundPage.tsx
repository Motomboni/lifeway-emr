/**
 * 404 Not Found Page
 * 
 * Displayed when a user navigates to a non-existent route.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from '../styles/NotFound.module.css';

export default function NotFoundPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Determine the correct dashboard route based on user role
  const dashboardRoute = user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard';

  return (
    <div className={styles.notFound}>
      <div className={styles.container}>
        <div className={styles.icon}>🔍</div>
        <h1 className={styles.title}>404</h1>
        <h2 className={styles.subtitle}>Page Not Found</h2>
        <p className={styles.message}>
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className={styles.actions}>
          <button
            className={styles.homeButton}
            onClick={() => navigate(dashboardRoute)}
          >
            Go to Dashboard
          </button>
          <button
            className={styles.backButton}
            onClick={() => navigate(-1)}
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  );
}
