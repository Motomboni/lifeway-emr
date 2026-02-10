/**
 * Visits List Page
 * 
 * Displays a list of visits with filtering options.
 * Per EMR Rules: Visit-scoped, role-based access.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchVisits } from '../api/visits';
import { Visit } from '../types/visit';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/VisitsList.module.css';

export default function VisitsListPage() {
  const { user, isLoading: authLoading } = useAuth();
  const { showError } = useToast();
  const navigate = useNavigate();

  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState<{
    count: number;
    currentPage: number;
    pageSize: number;
    totalPages: number;
  }>({
    count: 0,
    currentPage: 1,
    pageSize: 20,
    totalPages: 0,
  });
  const [filters, setFilters] = useState<{
    status?: 'OPEN' | 'CLOSED';
    payment_status?: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED';
    date_from?: string;
    date_to?: string;
    search?: string;
  }>({});
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Only fetch when auth is ready and user is present (avoids 401 from firing before session is set)
  useEffect(() => {
    if (authLoading || !user) return;
    loadVisits();
  }, [filters, authLoading, user]);

  const loadVisits = async () => {
    try {
      setLoading(true);
      const response = await fetchVisits({
        ...filters,
        page: pagination.currentPage,
        page_size: pagination.pageSize,
      });
      
      // Handle paginated response
      if (response && typeof response === 'object' && 'results' in response) {
        setVisits(response.results);
        setPagination(prev => ({
          ...prev,
          count: response.count,
          totalPages: Math.ceil(response.count / pagination.pageSize),
        }));
      } else {
        // Fallback for non-paginated response
        setVisits(response as Visit[]);
        setPagination(prev => ({
          ...prev,
          count: (response as Visit[]).length,
          totalPages: 1,
        }));
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visits';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleVisitClick = (visitId: number) => {
    if (user?.role === 'DOCTOR') {
      navigate(`/visits/${visitId}/consultation`);
    } else if (user?.role === 'NURSE') {
      navigate(`/visits/${visitId}/nursing`);
    } else if (user?.role === 'RECEPTIONIST') {
      // Receptionists navigate to visit details page for billing access
      navigate(`/visits/${visitId}`);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'OPEN':
        return styles.statusOpen;
      case 'CLOSED':
        return styles.statusClosed;
      default:
        return styles.statusDefault;
    }
  };

  const getPaymentBadgeClass = (paymentStatus: string) => {
    switch (paymentStatus) {
      case 'PAID':
      case 'SETTLED':
        return styles.paymentCleared;
      case 'UNPAID':
      case 'PARTIALLY_PAID':
      case 'INSURANCE_PENDING':
        return styles.paymentPending;
      default:
        return styles.paymentDefault;
    }
  };

  return (
    <div className={styles.visitsListPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Visits</h1>
        <div className={styles.actions}>
          {user?.role === 'RECEPTIONIST' && (
            <button
              className={styles.newVisitButton}
              onClick={() => navigate('/visits/new')}
            >
              New Visit
            </button>
          )}
        </div>
      </header>

      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label>Status:</label>
          <select
            value={filters.status || ''}
            onChange={(e) => setFilters({
              ...filters,
              status: e.target.value as 'OPEN' | 'CLOSED' | undefined || undefined
            })}
          >
            <option value="">All</option>
            <option value="OPEN">Open</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label>Payment:</label>
          <select
            value={filters.payment_status || ''}
            onChange={(e) => setFilters({
              ...filters,
              payment_status: e.target.value as 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED' | undefined || undefined
            })}
          >
            <option value="">All</option>
            <option value="PENDING">Pending</option>
            <option value="CLEARED">Cleared</option>
          </select>
        </div>

        <button
          className={styles.clearFiltersButton}
          onClick={() => setFilters({})}
        >
          Clear Filters
        </button>
      </div>

      {(loading || authLoading) ? (
        <LoadingSkeleton count={5} />
      ) : visits.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No visits found</p>
          {user?.role === 'RECEPTIONIST' && (
            <button onClick={() => navigate('/visits/new')}>
              Create First Visit
            </button>
          )}
        </div>
      ) : (
        <div className={styles.visitsGrid}>
          {visits.map((visit) => {
            // All roles can click on visits, but navigation differs by role
            const isClickable = 
              user?.role === 'RECEPTIONIST' || // Receptionists can access all visits for billing
              (user?.role === 'DOCTOR' && visit.status === 'OPEN') ||
              (user?.role === 'NURSE' && visit.status === 'OPEN');
            
            return (
              <div
                key={visit.id}
                className={`${styles.visitCard} ${isClickable ? styles.clickable : ''}`}
                onClick={() => isClickable && handleVisitClick(visit.id)}
              >
                <div className={styles.visitHeader}>
                  <h3>Visit #{visit.id}</h3>
                  <div className={styles.badges}>
                    <span className={getStatusBadgeClass(visit.status)}>
                      {visit.status}
                    </span>
                    <span className={getPaymentBadgeClass(visit.payment_status)}>
                      {visit.payment_status}
                    </span>
                  </div>
                </div>
                
                <div className={styles.visitDetails}>
                  <p><strong>Patient:</strong> {visit.patient_name || 'N/A'}</p>
                  <p><strong>Patient ID:</strong> {visit.patient_id || 'N/A'}</p>
                  <p><strong>Created:</strong> {new Date(visit.created_at).toLocaleDateString()}</p>
                </div>

                {user?.role === 'DOCTOR' && visit.status === 'OPEN' && (
                  <div className={styles.visitActions}>
                    <button
                      className={styles.consultButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/visits/${visit.id}/consultation`);
                      }}
                    >
                      Open Consultation
                    </button>
                  </div>
                )}

                {user?.role === 'NURSE' && visit.status === 'OPEN' && (
                  <div className={styles.visitActions}>
                    <button
                      className={styles.consultButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/visits/${visit.id}/nursing`);
                      }}
                    >
                      Open Nursing Care
                    </button>
                  </div>
                )}

                {user?.role === 'RECEPTIONIST' && (
                  <div className={styles.visitActions}>
                    <button
                      className={styles.consultButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/visits/${visit.id}`);
                      }}
                    >
                      View Details & Billing
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && visits.length > 0 && pagination.totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.paginationButton}
            onClick={() => setPagination(prev => ({ ...prev, currentPage: prev.currentPage - 1 }))}
            disabled={pagination.currentPage === 1}
          >
            Previous
          </button>
          <span className={styles.paginationInfo}>
            Page {pagination.currentPage} of {pagination.totalPages} ({pagination.count} total)
          </span>
          <button
            className={styles.paginationButton}
            onClick={() => setPagination(prev => ({ ...prev, currentPage: prev.currentPage + 1 }))}
            disabled={pagination.currentPage >= pagination.totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
