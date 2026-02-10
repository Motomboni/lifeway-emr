/**
 * Back to Dashboard Component
 * 
 * Provides a consistent link to navigate back to the dashboard from any page.
 * For PATIENT users, redirects to /patient-portal/dashboard
 * For other users, redirects to /dashboard
 */
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import styles from '../../styles/BackToDashboard.module.css';

interface BackToDashboardProps {
  /** Optional custom label */
  label?: string;
  /** Optional custom className */
  className?: string;
  /** Show as button instead of link */
  asButton?: boolean;
}

export default function BackToDashboard({ 
  label = '← Back to Dashboard', 
  className = '',
  asButton = false 
}: BackToDashboardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  
  // Determine the correct dashboard route based on user role
  const dashboardRoute = user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard';
  
  // Don't show on dashboard page itself
  if (location.pathname === '/dashboard' || location.pathname === '/patient-portal/dashboard') {
    return null;
  }
  
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate(dashboardRoute);
  };
  
  if (asButton) {
    return (
      <button 
        onClick={handleClick}
        className={`${styles.backButton} ${className}`}
        aria-label="Go back to dashboard"
      >
        {label}
      </button>
    );
  }
  
  return (
    <a 
      href={dashboardRoute}
      onClick={handleClick}
      className={`${styles.backLink} ${className}`}
      aria-label="Go back to dashboard"
    >
      {label}
    </a>
  );
}
