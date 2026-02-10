/**
 * Notification Context
 * 
 * Provides notification system for pending orders and important updates.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { isAccessTokenExpired } from '../api/auth';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { Visit } from '../types/visit';
import { fetchLabOrders } from '../api/lab';
import { fetchRadiologyOrders } from '../api/radiology';
import { fetchPrescriptions } from '../api/prescription';
import { getPendingVerificationPatients } from '../api/patient';
import { fetchAdmission } from '../api/admissions';
import { extractPaginatedResults } from '../utils/pagination';
import { logger } from '../utils/logger';

export interface Notification {
  id: string;
  type: 'lab_order' | 'radiology_order' | 'prescription' | 'prescription_dispensed' | 'payment' | 'patient_verification' | 'patient_discharged';
  message: string;
  visitId: number;
  count: number;
  timestamp: Date;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  refreshNotifications: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [readIds, setReadIds] = useState<Set<string>>(new Set());

  const refreshNotifications = useCallback(async () => {
    if (!user || !isAuthenticated) {
      setNotifications([]);
      return;
    }

    // Check if access token is expired to avoid 401 errors
    const storedTokens = localStorage.getItem('auth_tokens');
    if (storedTokens) {
      try {
        const parsedTokens = JSON.parse(storedTokens);
        if (parsedTokens?.access && isAccessTokenExpired(parsedTokens.access)) {
          // Token is expired, skip API calls to avoid 401
          return;
        }
      } catch {
        // Invalid tokens, skip
        return;
      }
    } else {
      // No tokens stored, skip
      return;
    }

    try {
      const newNotifications: Notification[] = [];

      // Role-specific notifications
      if (user.role === 'LAB_TECH') {
        const visitsResponse = await fetchVisits({ status: 'OPEN' });
        const allVisits = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results || [];
        // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
        const openVisits = allVisits.filter((v: Visit) => 
          v.payment_status === 'PAID' || 
          v.payment_status === 'SETTLED' || 
          v.payment_status === 'PARTIALLY_PAID'
        );
        for (const visit of openVisits) {
          try {
            const orders = await fetchLabOrders(visit.id.toString());
            const pendingOrders = orders.filter(o => o.status === 'ORDERED' || o.status === 'SAMPLE_COLLECTED');
            if (pendingOrders.length > 0) {
              newNotifications.push({
                id: `lab-${visit.id}`,
                type: 'lab_order',
                message: `${pendingOrders.length} pending lab order(s) for Visit #${visit.id}`,
                visitId: visit.id,
                count: pendingOrders.length,
                timestamp: new Date(),
              });
            }
          } catch (error: any) {
            // Skip if error fetching orders (including 401 token expiration)
            // Don't log 401 errors as they're handled by apiClient
            if (error?.status !== 401) {
              logger.debug('Failed to fetch lab orders for notifications:', error);
            }
          }
        }
      }

      if (user.role === 'RADIOLOGY_TECH') {
        const visitsResponse = await fetchVisits({ status: 'OPEN' });
        const allVisits = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results || [];
        // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
        const openVisits = allVisits.filter((v: Visit) => 
          v.payment_status === 'PAID' || 
          v.payment_status === 'SETTLED' || 
          v.payment_status === 'PARTIALLY_PAID'
        );
        for (const visit of openVisits) {
          try {
            const orders = await fetchRadiologyOrders(visit.id.toString());
            const pendingOrders = orders.filter(o => o.status === 'PENDING');
            if (pendingOrders.length > 0) {
              newNotifications.push({
                id: `radiology-${visit.id}`,
                type: 'radiology_order',
                message: `${pendingOrders.length} pending radiology order(s) for Visit #${visit.id}`,
                visitId: visit.id,
                count: pendingOrders.length,
                timestamp: new Date(),
              });
            }
          } catch (error: any) {
            // Skip if error fetching orders (including 401 token expiration)
            // Don't log 401 errors as they're handled by apiClient
            if (error?.status !== 401) {
              logger.debug('Failed to fetch radiology orders for notifications:', error);
            }
          }
        }
      }

      if (user.role === 'PHARMACIST') {
        const visitsResponse = await fetchVisits({ status: 'OPEN' });
        const allVisits = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results || [];
        const openVisits = allVisits.filter((v: Visit) => v.payment_status === 'PAID' || v.payment_status === 'SETTLED');
        for (const visit of openVisits) {
          try {
            const prescriptions = await fetchPrescriptions(visit.id.toString());
            const pendingPrescriptions = prescriptions.filter(p => p.status === 'PENDING');
            if (pendingPrescriptions.length > 0) {
              newNotifications.push({
                id: `prescription-${visit.id}`,
                type: 'prescription',
                message: `${pendingPrescriptions.length} pending prescription(s) for Visit #${visit.id}`,
                visitId: visit.id,
                count: pendingPrescriptions.length,
                timestamp: new Date(),
              });
            }
          } catch (error) {
            // Skip if error fetching prescriptions
          }
        }
      }

      if (user.role === 'NURSE') {
        // Dispensed prescriptions notification - nurses need to administer drugs
        const visitsResponse = await fetchVisits({ status: 'OPEN' });
        const allVisits = extractPaginatedResults(visitsResponse);
        // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
        const openVisits = allVisits.filter((v: Visit) => 
          v.payment_status === 'PAID' || 
          v.payment_status === 'SETTLED' || 
          v.payment_status === 'PARTIALLY_PAID'
        );
        for (const visit of openVisits) {
          try {
            const prescriptions = await fetchPrescriptions(visit.id.toString());
            // Filter for dispensed prescriptions that need administration
            const dispensedPrescriptions = prescriptions.filter(p => p.status === 'DISPENSED');
            if (dispensedPrescriptions.length > 0) {
              newNotifications.push({
                id: `prescription-dispensed-${visit.id}`,
                type: 'prescription_dispensed',
                message: `${dispensedPrescriptions.length} dispensed prescription(s) ready for administration - Visit #${visit.id}`,
                visitId: visit.id,
                count: dispensedPrescriptions.length,
                timestamp: new Date(),
              });
            }
          } catch (error: any) {
            // Skip if error fetching prescriptions (including 401 token expiration)
            // Don't log 401 errors as they're handled by apiClient
            if (error?.status !== 401) {
              logger.debug('Failed to fetch prescriptions for notifications:', error);
            }
          }
        }

        // Patient discharge notification - nurses need to be aware of recent discharges
        // Check both OPEN and CLOSED visits for recently discharged patients
        const allVisitsForDischarge = extractPaginatedResults(await fetchVisits({}));
        const recentDischarges: { visitId: number; patientName: string; dischargeDate: Date }[] = [];
        
        for (const visit of allVisitsForDischarge) {
          try {
            const admission = await fetchAdmission(visit.id);
            if (admission && admission.admission_status === 'DISCHARGED' && admission.discharge_date) {
              const dischargeDate = new Date(admission.discharge_date);
              const hoursSinceDischarge = (Date.now() - dischargeDate.getTime()) / (1000 * 60 * 60);
              
              // Only notify about discharges within the last 24 hours
              if (hoursSinceDischarge <= 24 && hoursSinceDischarge >= 0) {
                recentDischarges.push({
                  visitId: visit.id,
                  patientName: admission.patient_name || `Patient #${visit.id}`,
                  dischargeDate: dischargeDate,
                });
              }
            }
          } catch (error: any) {
            // Skip if error fetching admission (404 is expected for visits without admissions)
            // Don't log 401 errors as they're handled by apiClient
            if (error?.status !== 401 && error?.status !== 404) {
              logger.debug('Failed to fetch admission for notifications:', error);
            }
          }
        }

        if (recentDischarges.length > 0) {
          // Group by visit or show individual notifications
          recentDischarges.forEach((discharge, index) => {
            const hoursAgo = Math.round((Date.now() - discharge.dischargeDate.getTime()) / (1000 * 60 * 60));
            newNotifications.push({
              id: `patient-discharged-${discharge.visitId}`,
              type: 'patient_discharged',
              message: `${discharge.patientName} was discharged ${hoursAgo === 0 ? 'recently' : `${hoursAgo} hour(s) ago`} - Visit #${discharge.visitId}`,
              visitId: discharge.visitId,
              count: 1,
              timestamp: discharge.dischargeDate,
            });
          });
        }
      }

      if (user.role === 'RECEPTIONIST') {
        // Pending payments notification
        try {
          const visitsResponse = await fetchVisits({ status: 'OPEN' });
          const allVisits = extractPaginatedResults(visitsResponse);
          const pendingVisits = allVisits.filter((v: any) => v.payment_status === 'UNPAID' || v.payment_status === 'PARTIALLY_PAID' || v.payment_status === 'INSURANCE_PENDING');
          if (pendingVisits.length > 0) {
            newNotifications.push({
              id: 'payments-pending',
              type: 'payment',
              message: `${pendingVisits.length} visit(s) with pending payments`,
              visitId: 0,
              count: pendingVisits.length,
              timestamp: new Date(),
            });
          }
        } catch (error: any) {
          // Skip if error fetching visits (including 401 token expiration, 504 timeouts)
          // Don't log 401/504 errors as they're expected during background polling
          if (error?.status !== 401 && error?.status !== 504) {
            console.warn('Error fetching visits for notifications:', error);
          }
        }
        
        // Pending patient verifications notification
        try {
          const pendingPatients = await getPendingVerificationPatients();
          if (pendingPatients.length > 0) {
            newNotifications.push({
              id: 'patient-verifications-pending',
              type: 'patient_verification',
              message: `${pendingPatients.length} patient account(s) pending verification`,
              visitId: 0,
              count: pendingPatients.length,
              timestamp: new Date(),
            });
          }
        } catch (error: any) {
          // Skip if error fetching pending verifications (including 401 token expiration, 504 timeouts)
          // Don't log 401/504 errors as they're expected during background polling
          if (error?.status !== 401 && error?.status !== 504) {
            logger.debug('Failed to fetch pending verifications for notifications:', error);
          }
        }
      }

      setNotifications(newNotifications);
    } catch (error: any) {
      // Don't log 401 as apiClient handles token refresh/redirect
      const isTokenExpired = error?.responseData?.code === 'token_not_valid' &&
                            error?.responseData?.messages?.some((m: any) => m.message === 'Token is expired');
      const isNetworkOr503 = error?.status === 503 || (error?.message && /network request failed|network error|service unavailable/i.test(error.message));
      if (error?.status !== 401 && !isTokenExpired) {
        if (isNetworkOr503) {
          logger.debug('Notification refresh skipped (backend unreachable):', error?.message || error?.status);
        } else {
          logger.error('Failed to refresh notifications:', error);
        }
      }
    }
  }, [user, isAuthenticated]);

  useEffect(() => {
    // Only start refreshing if user is authenticated
    if (!isAuthenticated || !user) {
      setNotifications([]);
      return;
    }
    
    refreshNotifications();
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      // Check authentication before each refresh
      if (isAuthenticated && user) {
        // Wrap in try-catch to prevent unhandled promise rejections
        refreshNotifications().catch((error) => {
          // Silently handle errors in background polling
          // Token refresh errors are handled by apiClient
          if (error?.status !== 401) {
            logger.debug('Notification refresh error:', error);
          }
        });
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshNotifications, isAuthenticated, user]);

  const markAsRead = useCallback((id: string) => {
    setReadIds(prev => {
      const newSet = new Set(prev);
      newSet.add(id);
      return newSet;
    });
  }, []);

  const markAllAsRead = useCallback(() => {
    setReadIds(new Set(notifications.map(n => n.id)));
  }, [notifications]);

  const unreadCount = notifications.filter(n => !readIds.has(n.id)).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        markAsRead,
        markAllAsRead,
        refreshNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
