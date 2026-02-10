/**
 * Lab Orders Page
 * 
 * For Lab Techs to view and process lab orders.
 * Per EMR Rules: Visit-scoped, shows visits with pending lab orders.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { fetchLabOrders, createLabResult } from '../api/lab';
import { Visit } from '../types/visit';
import { LabOrder } from '../types/lab';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';
import styles from '../styles/LabOrders.module.css';

// Component for lab result post button with lock check
function LabResultPostButton({
  labOrderId,
  visitId,
  onShowForm,
  isCreating,
}: {
  labOrderId: number;
  visitId: string;
  onShowForm: () => void;
  isCreating: boolean;
}) {
  const labResultLock = useActionLock({
    actionType: 'lab_result_post',
    params: { lab_order_id: labOrderId },
    enabled: !!labOrderId,
  });

  if (labResultLock.isLocked && labResultLock.lockResult) {
    return (
      <div>
        <LockIndicator
          lockResult={labResultLock.lockResult}
          loading={labResultLock.loading}
          variant="inline"
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onShowForm}
      disabled={labResultLock.loading || isCreating || labResultLock.isLocked}
      style={{
        padding: '10px 20px',
        backgroundColor: labResultLock.loading ? '#95a5a6' : labResultLock.isLocked ? '#ccc' : '#3498db',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: labResultLock.loading || labResultLock.isLocked ? 'not-allowed' : 'pointer',
        fontSize: '14px',
        fontWeight: 500,
        transition: 'background-color 0.2s',
      }}
    >
      {labResultLock.loading ? 'Checking...' : isCreating ? 'Opening...' : 'Add Result'}
    </button>
  );
}

export default function LabOrdersPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  
  const [visits, setVisits] = useState<Visit[]>([]);
  const [selectedVisit, setSelectedVisit] = useState<number | null>(null);
  const [labOrders, setLabOrders] = useState<LabOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [creatingResult, setCreatingResult] = useState<number | null>(null);
  const [resultData, setResultData] = useState<Record<number, string>>({});
  const [resultFlag, setResultFlag] = useState<Record<number, 'NORMAL' | 'ABNORMAL' | 'CRITICAL'>>({});
  const [savingResult, setSavingResult] = useState(false);

  useEffect(() => {
    loadVisitsWithPendingOrders();
  }, []);

  useEffect(() => {
    if (selectedVisit) {
      loadLabOrders(selectedVisit.toString());
    }
  }, [selectedVisit]);

  const loadVisitsWithPendingOrders = async () => {
    try {
      setLoading(true);
      // Fetch all open visits with cleared payment (including PARTIALLY_PAID)
      const visitsResponse = await fetchVisits({ status: 'OPEN' });
      const allVisitsRaw = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results;
      // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
      const allVisits = allVisitsRaw.filter((v: Visit) => 
        v.payment_status === 'PAID' || 
        v.payment_status === 'SETTLED' || 
        v.payment_status === 'PARTIALLY_PAID'
      );
      
      // For each visit, check if it has pending lab orders
      // Note: In a real implementation, you'd want a backend endpoint for this
      // For now, we'll show all open visits and let the user select
      setVisits(allVisits);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visits';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadLabOrders = async (visitId: string) => {
    try {
      setLoadingOrders(true);
      const response = await fetchLabOrders(visitId);
      
      // Handle paginated response (DRF returns {count, results, next, previous})
      // or plain array response
      const ordersArray = Array.isArray(response) 
        ? response 
        : (response && typeof response === 'object' && 'results' in response && Array.isArray((response as any).results))
          ? (response as any).results
          : [];
      
      // Filter to show only pending orders (ORDERED or SAMPLE_COLLECTED status)
      const pendingOrders = ordersArray.filter(
        (order: LabOrder) => order.status === 'ORDERED' || order.status === 'SAMPLE_COLLECTED'
      );
      setLabOrders(pendingOrders);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load lab orders';
      showError(errorMessage);
    } finally {
      setLoadingOrders(false);
    }
  };

  const handleCreateResult = async (orderId: number) => {
    const data = resultData[orderId];
    if (!data || !data.trim()) {
      showError('Result data is required');
      return;
    }

    if (!selectedVisit) {
      showError('No visit selected');
      return;
    }

    try {
      setSavingResult(true);
      await createLabResult(selectedVisit.toString(), {
        lab_order: orderId,
        result_data: data,
        abnormal_flag: resultFlag[orderId] || 'NORMAL'
      });
      showSuccess('Lab result recorded successfully');
      setCreatingResult(null);
      setResultData(prev => {
        const next = { ...prev };
        delete next[orderId];
        return next;
      });
      setResultFlag(prev => {
        const next = { ...prev };
        delete next[orderId];
        return next;
      });
      // Reload lab orders to show updated status
      await loadLabOrders(selectedVisit.toString());
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to record lab result';
      showError(errorMessage);
    } finally {
      setSavingResult(false);
    }
  };

  if (user?.role !== 'LAB_TECH') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Lab Technicians only.</p>
      </div>
    );
  }

  return (
    <div className={styles.labOrdersPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Lab Orders</h1>
        <p>Select a visit to view and process pending lab orders</p>
      </header>

      <div className={styles.content}>
        <div className={styles.visitsPanel}>
          <h2>Visits with Pending Orders</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : visits.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No visits with pending lab orders</p>
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
              <h2>Lab Orders for Visit #{selectedVisit}</h2>
              {loadingOrders ? (
                <LoadingSkeleton count={3} />
              ) : labOrders.length === 0 ? (
                <div className={styles.emptyState}>
                  <p>No pending lab orders for this visit</p>
                </div>
              ) : (
                <div className={styles.ordersList}>
                  {labOrders.map((order) => (
                    <div key={order.id} className={styles.orderCard}>
                      <div className={styles.orderHeader}>
                        <h3>Lab Order #{order.id}</h3>
                        <span className={styles.orderStatus}>{order.status}</span>
                      </div>
                      <div className={styles.orderDetails}>
                        <p><strong>Tests Requested:</strong> {
                          Array.isArray(order.tests_requested) 
                            ? order.tests_requested.join(', ') 
                            : JSON.stringify(order.tests_requested)
                        }</p>
                        {order.clinical_indication && (
                          <p><strong>Clinical Indication:</strong> {order.clinical_indication}</p>
                        )}
                        <p><strong>Ordered By:</strong> Doctor ID {order.ordered_by}</p>
                        <p><strong>Created:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className={styles.orderActions}>
                        {order.status === 'RESULT_READY' ? (
                          <button
                            className={styles.viewButton}
                            onClick={() => {
                              // Navigate to consultation page to view result
                              window.location.href = `/visits/${selectedVisit}/consultation`;
                            }}
                          >
                            View Result
                          </button>
                        ) : (
                          <LabResultPostButton
                            labOrderId={order.id}
                            visitId={selectedVisit.toString()}
                            onShowForm={() => setCreatingResult(order.id)}
                            isCreating={creatingResult === order.id}
                          />
                        )}
                      </div>
                      
                      {/* Create result form */}
                      {creatingResult === order.id && (
                        <div className={styles.resultForm}>
                          <h4>Record Lab Result</h4>
                          <div className={styles.formGroup}>
                            <label>Result Data *</label>
                            <textarea
                              value={resultData[order.id] || ''}
                              onChange={(e) => setResultData(prev => ({ ...prev, [order.id]: e.target.value }))}
                              placeholder="Enter lab findings and results"
                              rows={5}
                              required
                            />
                          </div>
                          <div className={styles.formGroup}>
                            <label>Abnormality Flag</label>
                            <select
                              value={resultFlag[order.id] || 'NORMAL'}
                              onChange={(e) => setResultFlag(prev => ({ ...prev, [order.id]: e.target.value as 'NORMAL' | 'ABNORMAL' | 'CRITICAL' }))}
                            >
                              <option value="NORMAL">Normal</option>
                              <option value="ABNORMAL">Abnormal</option>
                              <option value="CRITICAL">Critical</option>
                            </select>
                          </div>
                          <div className={styles.formActions}>
                            <button
                              className={styles.saveButton}
                              onClick={() => handleCreateResult(order.id)}
                              disabled={savingResult}
                            >
                              {savingResult ? 'Recording...' : 'Record Result'}
                            </button>
                            <button
                              className={styles.cancelButton}
                              onClick={() => {
                                setCreatingResult(null);
                                setResultData(prev => {
                                  const next = { ...prev };
                                  delete next[order.id];
                                  return next;
                                });
                                setResultFlag(prev => {
                                  const next = { ...prev };
                                  delete next[order.id];
                                  return next;
                                });
                              }}
                              disabled={savingResult}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className={styles.emptyState}>
              <p>Select a visit to view lab orders</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
