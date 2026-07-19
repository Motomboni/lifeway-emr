/**
 * Visits List Page
 * 
 * Displays a list of visits with filtering options.
 * Per EMR Rules: Visit-scoped, role-based access.
 * Honors URL query params (e.g. /visits?status=OPEN from voice commands).
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useRolePermissions } from '../hooks/useRolePermissions';
import { fetchVisits, deleteVisit } from '../api/visits';
import { Visit } from '../types/visit';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/VisitsList.module.css';

type VisitFilters = {
  status?: 'OPEN' | 'CLOSED';
  payment_status?: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED';
  date_from?: string;
  date_to?: string;
  search?: string;
};

function filtersFromSearchParams(searchParams: URLSearchParams): VisitFilters {
  const status = searchParams.get('status');
  const payment = searchParams.get('payment_status');
  const filters: VisitFilters = {};
  if (status === 'OPEN' || status === 'CLOSED') {
    filters.status = status;
  }
  if (
    payment === 'UNPAID' ||
    payment === 'PARTIALLY_PAID' ||
    payment === 'PAID' ||
    payment === 'INSURANCE_PENDING' ||
    payment === 'INSURANCE_CLAIMED' ||
    payment === 'SETTLED'
  ) {
    filters.payment_status = payment;
  }
  const dateFrom = searchParams.get('date_from');
  const dateTo = searchParams.get('date_to');
  const search = searchParams.get('search');
  if (dateFrom) filters.date_from = dateFrom;
  if (dateTo) filters.date_to = dateTo;
  if (search) filters.search = search;
  return filters;
}

function searchParamsFromFilters(filters: VisitFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.payment_status) params.set('payment_status', filters.payment_status);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.search) params.set('search', filters.search);
  return params;
}

export default function VisitsListPage() {
  const { user, isLoading: authLoading } = useAuth();
  const { isAdmin, isReceptionist, isDoctor, isNurse, canCreateVisit, canHardDeleteRecords } = useRolePermissions();
  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

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
  const [filters, setFilters] = useState<VisitFilters>(() =>
    filtersFromSearchParams(searchParams),
  );
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Keep filters in sync when URL changes (voice command / deep link)
  useEffect(() => {
    setFilters(filtersFromSearchParams(searchParams));
  }, [searchParams]);

  const updateFilters = useCallback(
    (next: VisitFilters | ((prev: VisitFilters) => VisitFilters)) => {
      setFilters((prev) => {
        const resolved = typeof next === 'function' ? next(prev) : next;
        setSearchParams(searchParamsFromFilters(resolved), { replace: true });
        return resolved;
      });
    },
    [setSearchParams],
  );

  // Only fetch when auth is ready
  useEffect(() => {
    if (authLoading || !user) return;
    loadVisits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleDeleteVisit = async (visitId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Permanently delete visit #${visitId}? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteVisit(visitId);
      showSuccess(`Visit #${visitId} deleted.`);
      loadVisits();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to delete visit');
    }
  };

  const handleVisitClick = (visitId: number) => {
    if (isDoctor) {
      navigate(`/visits/${visitId}/consultation`);
    } else if (isNurse) {
      navigate(`/visits/${visitId}/nursing`);
    } else {
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
          {canCreateVisit && (
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
            onChange={(e) =>
              updateFilters({
                ...filters,
                status: (e.target.value as 'OPEN' | 'CLOSED' | '') || undefined,
              })
            }
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
            onChange={(e) =>
              updateFilters({
                ...filters,
                payment_status:
                  (e.target.value as VisitFilters['payment_status'] | '') || undefined,
              })
            }
          >
            <option value="">All</option>
            <option value="UNPAID">Unpaid</option>
            <option value="PARTIALLY_PAID">Partially Paid</option>
            <option value="PAID">Paid</option>
            <option value="INSURANCE_PENDING">Insurance Pending</option>
            <option value="SETTLED">Settled</option>
          </select>
        </div>

        <button
          className={styles.clearFiltersButton}
          onClick={() => updateFilters({})}
        >
          Clear Filters
        </button>
      </div>

      {(loading || authLoading) ? (
        <LoadingSkeleton count={5} />
      ) : visits.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No visits found</p>
          {canCreateVisit && (
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
              isAdmin ||
              isReceptionist ||
              (isDoctor && visit.status === 'OPEN') ||
              (isNurse && visit.status === 'OPEN');
            
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

                {isDoctor && visit.status === 'OPEN' && (
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

                {isNurse && visit.status === 'OPEN' && (
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

                {canHardDeleteRecords && (
                  <div className={styles.visitActions}>
                    <button
                      type="button"
                      className={styles.deleteButton}
                      onClick={(e) => handleDeleteVisit(visit.id, e)}
                    >
                      Delete permanently
                    </button>
                  </div>
                )}

                {canCreateVisit && (
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
