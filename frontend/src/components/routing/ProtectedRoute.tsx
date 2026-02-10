/**
 * Protected Route Component
 * 
 * Per EMR Rules:
 * - All clinical routes require authentication
 * - Role-based access can be enforced per route
 * - Redirects to login if not authenticated
 */
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { logger } from '../../utils/logger';

// All valid user roles
type UserRole = 'DOCTOR' | 'NURSE' | 'LAB_TECH' | 'RADIOLOGY_TECH' | 'PHARMACIST' | 'RECEPTIONIST' | 'PATIENT' | 'ADMIN' | 'IVF_SPECIALIST' | 'EMBRYOLOGIST';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: UserRole | UserRole[];
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requiredRole, requireAdmin }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check admin access if required (superuser OR role ADMIN)
  const isAdmin = user?.is_superuser === true || user?.role === 'ADMIN';
  if (requireAdmin && !isAdmin) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <h2>Access Denied</h2>
        <p>You do not have permission to access this page.</p>
        <p>This page is restricted to administrators only.</p>
      </div>
    );
  }

  // Check role if required
  if (requiredRole) {
    const allowedRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    const userRole = user?.role;
    
    logger.debug('[ProtectedRoute] Checking access:', { userRole, allowedRoles });
    
    // Admin can access any route
    if (userRole === 'ADMIN') {
      // Allow access
    } else if (!userRole || !allowedRoles.includes(userRole as UserRole)) {
      logger.warn('[ProtectedRoute] Access denied:', userRole, 'not in', allowedRoles);
      return (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <h2>Access Denied</h2>
          <p>You do not have permission to access this page.</p>
          <p>Required role: {Array.isArray(requiredRole) ? requiredRole.join(' or ') : requiredRole}</p>
          <p style={{ color: '#666', fontSize: '0.9em' }}>Your current role: {userRole || 'None'}</p>
        </div>
      );
    }
  }

  return <>{children}</>;
}
