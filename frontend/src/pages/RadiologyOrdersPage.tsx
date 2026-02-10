/**
 * Radiology Orders Page
 *
 * Route: /radiology-orders
 * For Radiology staff. Data: GET /visits/{visitId}/radiology/ → RadiologyRequest objects.
 *
 * Display: Table with Patient Name, Hospital Number, Study Type, Ordering Doctor,
 * Status (PENDING / COMPLETED), Order Date, Report Date (if completed).
 * Actions: "Add Report" for PENDING, "View Report" for COMPLETED.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { fetchRadiologyOrders, updateRadiologyReport } from '../api/radiology';
import { Visit } from '../types/visit';
import { RadiologyOrder } from '../types/radiology';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';
import styles from '../styles/RadiologyOrders.module.css';

// Component for radiology report post button with lock check
function RadiologyReportPostButton({
  radiologyOrderId,
  visitId,
  onShowForm,
  isCreating,
}: {
  radiologyOrderId: number;
  visitId: string;
  onShowForm: () => void;
  isCreating: boolean;
}) {
  // Hooks must be called unconditionally - always call useActionLock
  const radiologyReportLock = useActionLock({
    actionType: 'radiology_report',
    params: { radiology_order_id: radiologyOrderId },
    enabled: !!radiologyOrderId && radiologyOrderId > 0,
  });

  // Handle invalid order ID after hook call
  if (!radiologyOrderId || radiologyOrderId <= 0) {
    return null;
  }

  // Show lock indicator only if explicitly locked (not on error/null)
  // Only show lock indicator if we have a valid lock result AND it's actually locked
  // AND it's not an error state
  if (
    radiologyReportLock.lockResult && 
    radiologyReportLock.lockResult.is_locked && 
    radiologyReportLock.lockResult.reason_code !== 'ERROR'
  ) {
    return (
      <div>
        <LockIndicator
          lockResult={radiologyReportLock.lockResult}
          loading={radiologyReportLock.loading}
          variant="inline"
        />
      </div>
    );
  }

  // Always show the button, even if lock check is loading, failed, or null
  // The button will be disabled if locked, but visible
  // If there's an error, we still show the button (it will be enabled since is_locked is false)
  // Always render something - never return null or undefined after this point
  const isDisabled = radiologyReportLock.loading || isCreating || 
                     (radiologyReportLock.lockResult?.is_locked && radiologyReportLock.lockResult.reason_code !== 'ERROR');
  
  return (
    <button
      className={styles.updateButton}
      onClick={isDisabled ? undefined : onShowForm}
      disabled={isDisabled}
      type="button"
    >
      {isCreating || radiologyReportLock.loading ? 'Loading...' : 'Add Report'}
    </button>
  );
}

export default function RadiologyOrdersPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();

  const [visits, setVisits] = useState<Visit[]>([]);
  const [selectedVisit, setSelectedVisit] = useState<number | null>(null);
  const [radiologyOrders, setRadiologyOrders] = useState<RadiologyOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [creatingResult, setCreatingResult] = useState<number | null>(null);
  const [resultData, setResultData] = useState<Record<number, string>>({});
  const [resultImageCount, setResultImageCount] = useState<Record<number, number>>({});
  const [savingResult, setSavingResult] = useState(false);

  useEffect(() => {
    loadVisits();
  }, []);

  useEffect(() => {
    if (selectedVisit) {
      loadRadiologyOrders(selectedVisit.toString());
    } else {
      setRadiologyOrders([]);
    }
  }, [selectedVisit]);

  const loadVisits = async () => {
    try {
      setLoading(true);
      const visitsResponse = await fetchVisits({ status: 'OPEN' });
      const allVisitsRaw = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results;
      const allVisits = (allVisitsRaw || []).filter((v: Visit) =>
        v.payment_status === 'PAID' ||
        v.payment_status === 'SETTLED' ||
        v.payment_status === 'PARTIALLY_PAID'
      );
      setVisits(allVisits);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visits';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadRadiologyOrders = async (visitId: string) => {
    try {
      setLoadingOrders(true);
      const response = await fetchRadiologyOrders(visitId);
      const ordersArray = Array.isArray(response)
        ? response
        : (response && typeof response === 'object' && 'results' in response && Array.isArray((response as any).results))
          ? (response as any).results
          : [];
      setRadiologyOrders(ordersArray);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load radiology orders';
      showError(errorMessage);
      setRadiologyOrders([]);
    } finally {
      setLoadingOrders(false);
    }
  };

  const selectedVisitData = selectedVisit ? (visits.find((v) => v.id === selectedVisit) ?? null) : null;
  const isCompleted = (order: RadiologyOrder) =>
    order.status === 'COMPLETED' || !!(order as any).report;

  const handleCreateResult = async (orderId: number) => {
    const report = resultData[orderId];
    if (!report || !report.trim()) {
      showError('Report is required');
      return;
    }

    if (!selectedVisit) {
      showError('No visit selected');
      return;
    }

    try {
      setSavingResult(true);
      const payload: { report: string; image_count?: number } = { report };
      const imgCount = resultImageCount[orderId];
      if (imgCount !== undefined && imgCount !== null)
        payload.image_count = Number(imgCount) || 0;
      await updateRadiologyReport(selectedVisit, orderId, payload);
      showSuccess('Radiology report posted successfully');
      setCreatingResult(null);
      setResultData(prev => {
        const next = { ...prev };
        delete next[orderId];
        return next;
      });
      setResultImageCount(prev => {
        const next = { ...prev };
        delete next[orderId];
        return next;
      });
      await loadRadiologyOrders(selectedVisit.toString());
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to record radiology result';
      showError(errorMessage);
    } finally {
      setSavingResult(false);
    }
  };

  const formatDateTime = (dateStr: string | undefined) =>
    dateStr ? new Date(dateStr).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—';

  if (user?.role !== 'RADIOLOGY_TECH') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Radiology Technicians only.</p>
      </div>
    );
  }

  return (
    <div className={styles.radiologyOrdersPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Radiology Orders</h1>
        <p>Select a visit to view and process radiology orders</p>
      </header>

      <div className={styles.content}>
        <div className={styles.visitsPanel}>
          <h2>Visits with Pending Orders</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : visits.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No visits available</p>
            </div>
          ) : (
            <div className={styles.visitsList}>
              {visits.map((visit) => (
                <div
                  key={visit.id}
                  className={`${styles.visitItem} ${selectedVisit === visit.id ? styles.selected : ''}`}
                  onClick={() => setSelectedVisit(visit.id)}
                >
                  <div className={styles.visitInfo}>
                    <h3>Visit #{visit.id}</h3>
                    <p>{visit.patient_name || 'Unknown Patient'}</p>
                    <p className={styles.visitDate}>
                      {new Date(visit.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={styles.ordersPanel}>
          {selectedVisit ? (
            <>
              <h2>Radiology Orders for Visit #{selectedVisit}</h2>
              {loadingOrders ? (
                <LoadingSkeleton count={3} />
              ) : radiologyOrders.length === 0 ? (
                <div className={styles.emptyState}>
                  <p>No radiology orders for this visit</p>
                </div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.ordersTable}>
                    <thead>
                      <tr>
                        <th>Patient Name</th>
                        <th>Hospital Number</th>
                        <th>Study Type</th>
                        <th>Ordering Doctor</th>
                        <th>Status</th>
                        <th>Order Date</th>
                        <th>Report Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {radiologyOrders.map((order) => {
                        const completed = isCompleted(order);
                        return (
                          <React.Fragment key={order.id}>
                            <tr>
                              <td>{selectedVisitData?.patient_name ?? '—'}</td>
                              <td>{selectedVisitData?.patient_id ?? '—'}</td>
                              <td>{order.study_type}</td>
                              <td>Doctor ID {order.ordered_by}</td>
                              <td>
                                <span className={completed ? styles.statusCompleted : styles.statusPending}>
                                  {order.status}
                                </span>
                              </td>
                              <td>{formatDateTime(order.created_at)}</td>
                              <td>{completed && order.report_date ? formatDateTime(order.report_date) : '—'}</td>
                              <td className={styles.actionCell}>
                                {completed ? (
                                  <button
                                    className={styles.viewButton}
                                    onClick={() => navigate(`/visits/${selectedVisit}/consultation`)}
                                  >
                                    View Report
                                  </button>
                                ) : (
                                  <RadiologyReportPostButton
                                    radiologyOrderId={order.id}
                                    visitId={selectedVisit.toString()}
                                    onShowForm={() => setCreatingResult(order.id)}
                                    isCreating={creatingResult === order.id}
                                  />
                                )}
                              </td>
                            </tr>
                            {creatingResult === order.id && (
                              <tr>
                                <td colSpan={8} className={styles.formCell}>
                                  <div className={styles.resultForm}>
                                    <h4>Record Radiology Result</h4>
                                    <p className={styles.formIntro}>
                                      Submit stores report and image count on the radiology request. Finding flag is for reference only and is not stored.
                                    </p>
                                    <div className={styles.formGroup}>
                                      <label>Report (required)</label>
                                      <textarea
                                        value={resultData[order.id] || ''}
                                        onChange={(e) => setResultData(prev => ({ ...prev, [order.id]: e.target.value }))}
                                        placeholder="Enter radiology findings and report"
                                        rows={5}
                                        required
                                      />
                                    </div>
                                    <div className={styles.formGroup}>
                                      <label>Image Count (optional)</label>
                                      <input
                                        type="number"
                                        min="0"
                                        value={resultImageCount[order.id] ?? ''}
                                        onChange={(e) => {
                                          const v = e.target.value;
                                          setResultImageCount(prev => {
                                            const next = { ...prev };
                                            if (v === '') delete next[order.id];
                                            else next[order.id] = parseInt(v, 10) || 0;
                                            return next;
                                          });
                                        }}
                                        placeholder="0"
                                      />
                                    </div>
                                    <div className={styles.formActions}>
                                      <button
                                        className={styles.saveButton}
                                        onClick={() => handleCreateResult(order.id)}
                                        disabled={savingResult || !resultData[order.id]?.trim()}
                                      >
                                        {savingResult ? 'Recording...' : 'Record Result'}
                                      </button>
                                      <button
                                        className={styles.cancelButton}
                                        onClick={() => {
                                          setCreatingResult(null);
                                          setResultData(prev => { const next = { ...prev }; delete next[order.id]; return next; });
                                          setResultImageCount(prev => { const next = { ...prev }; delete next[order.id]; return next; });
                                        }}
                                        disabled={savingResult}
                                      >
                                        Cancel
                                      </button>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className={styles.emptyState}>
              <p>Select a visit to view radiology orders</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
