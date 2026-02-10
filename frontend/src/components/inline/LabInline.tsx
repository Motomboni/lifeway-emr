/**
 * LabInline Component
 * 
 * Inline component for lab orders within consultation workspace.
 * 
 * Per EMR Rules:
 * - Visit-scoped: Requires visitId
 * - Consultation-dependent: Requires consultationId
 * - Doctor: Can create orders, view all
 * - Lab Tech: Can create results, view limited fields
 * - No sidebar navigation - inline only
 */
import React, { useState, useEffect } from 'react';
import { useLabOrders } from '../../hooks/useLabOrders';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import { LabOrder, LabResult } from '../../types/lab';
import { fetchLabTestTemplates, applyLabTestTemplate, type LabTestTemplate } from '../../api/lab';
import LabOrderDetailsForm, { LabOrderDetails } from '../laboratory/LabOrderDetailsForm';
import LockedButton from '../locks/LockedButton';
import LockIndicator from '../locks/LockIndicator';
import { useActionLock } from '../../hooks/useActionLock';
import { logger } from '../../utils/logger';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface LabInlineProps {
  visitId: string;
  consultationId?: number;
}

// Component for lab order create button with lock check
function LabOrderCreateButton({
  visitId,
  consultationId,
  onShowForm,
}: {
  visitId: string;
  consultationId: number;
  onShowForm: () => void;
}) {
  const labOrderLock = useActionLock({
    actionType: 'lab_order',
    params: { visit_id: parseInt(visitId), consultation_id: consultationId },
    enabled: !!visitId && !!consultationId,
  });

  if (labOrderLock.isLocked && labOrderLock.lockResult) {
    return (
      <div>
        <LockIndicator
          lockResult={labOrderLock.lockResult}
          loading={labOrderLock.loading}
          variant="inline"
        />
      </div>
    );
  }

  return (
    <LockedButton
      lockResult={labOrderLock.lockResult}
      loading={labOrderLock.loading}
      onClick={onShowForm}
      variant="primary"
      showLockMessage={false}
      className={styles.addButton}
    >
      + New Order
    </LockedButton>
  );
}

// Component for lab result post button with lock check
function LabResultPostButton({
  labOrderId,
  visitId,
  onShowForm,
}: {
  labOrderId: number;
  visitId: string;
  onShowForm: () => void;
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
    <LockedButton
      lockResult={labResultLock.lockResult}
      loading={labResultLock.loading}
      onClick={onShowForm}
      variant="primary"
      showLockMessage={false}
      className={styles.addButton}
    >
      Add Result
    </LockedButton>
  );
}

export default function LabInline({ visitId, consultationId }: LabInlineProps) {
  const { user } = useAuth();
  const {
    labOrders,
    labResults,
    loading,
    error,
    isSaving,
    createLabOrder,
    createLabResult,
    refresh
  } = useLabOrders(visitId);
  
  const { showSuccess, showError } = useToast();
  
  const [showCreateOrderModal, setShowCreateOrderModal] = useState(false);
  const [formInitialValues, setFormInitialValues] = useState<{ tests: string[]; indication: string } | null>(null);
  const [showCreateResult, setShowCreateResult] = useState<number | null>(null);
  const [newResultData, setNewResultData] = useState<Record<number, string>>({});
  const [newResultFlag, setNewResultFlag] = useState<Record<number, 'NORMAL' | 'ABNORMAL' | 'CRITICAL'>>({});
  
  // Template state (for "Use Template" before opening modal)
  const [templates, setTemplates] = useState<LabTestTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  const handleLabOrderFormSubmit = async (labOrderDetails: LabOrderDetails) => {
    if (!consultationId) {
      showError('Consultation is required to create lab orders');
      return;
    }

    try {
      await createLabOrder(visitId, {
        consultation: consultationId,
        tests_requested: labOrderDetails.tests_requested,
        clinical_indication: labOrderDetails.clinical_indication
      });
      showSuccess('Lab order created successfully');
      setShowCreateOrderModal(false);
      setFormInitialValues(null);
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create lab order');
    }
  };

  const handleCreateResult = async (labOrderId: number) => {
    // Restrict to Lab Technicians only
    if (user?.role !== 'LAB_TECH') {
      showError('Only Lab Technicians can record lab results');
      return;
    }
    
    const resultData = newResultData[labOrderId];
    if (!resultData || !resultData.trim()) {
      showError('Result data is required');
      return;
    }

    try {
      await createLabResult(
        visitId,
        labOrderId,
        resultData,
        newResultFlag[labOrderId] || 'NORMAL'
      );
      showSuccess('Lab result recorded successfully');
      setShowCreateResult(null);
      setNewResultData(prev => {
        const next = { ...prev };
        delete next[labOrderId];
        return next;
      });
      setNewResultFlag(prev => {
        const next = { ...prev };
        delete next[labOrderId];
        return next;
      });
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create lab result');
    }
  };

  // Load templates when template picker is shown
  useEffect(() => {
    if (showTemplates && templates.length === 0 && !loadingTemplates) {
      loadTemplates();
    }
  }, [showTemplates]);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      logger.debug('Loading lab test templates...');
      const data = await fetchLabTestTemplates();
      const templatesArray = Array.isArray(data) ? data : [];
      logger.debug('Loaded lab test templates:', templatesArray.length);
      setTemplates(templatesArray);
    } catch (err) {
      console.error('Failed to load lab test templates:', err);
      showError('Failed to load lab test templates. Please try again.');
      setTemplates([]);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleUseTemplate = async (template: LabTestTemplate) => {
    try {
      const templateData = await applyLabTestTemplate(template.id);
      setFormInitialValues({
        tests: templateData.tests,
        indication: templateData.clinical_indication || ''
      });
      setShowTemplates(false);
      setShowCreateOrderModal(true);
      showSuccess(`Template "${template.name}" applied`);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to use template');
    }
  };

  const getResultForOrder = (orderId: number): LabResult | undefined => {
    return labResults.find(r => r.lab_order_id === orderId);
  };

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Lab Orders</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Lab Orders</h3>
        {consultationId && !showCreateOrderModal && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <LabOrderCreateButton
              visitId={visitId}
              consultationId={consultationId}
              onShowForm={() => {
                setFormInitialValues(null);
                setShowCreateOrderModal(true);
              }}
            />
            <button
              type="button"
              onClick={() => {
                if (templates.length === 0 && !loadingTemplates) loadTemplates();
                setShowTemplates(!showTemplates);
              }}
              className={styles.secondaryButton}
              style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
              disabled={loadingTemplates}
            >
              {loadingTemplates ? 'Loading...' : showTemplates ? 'Hide Templates' : '📋 Use Template'}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className={styles.errorMessage}>{error}</div>
      )}

      {/* Template selection (when "Use Template" clicked, before opening modal) */}
      {showTemplates && !showCreateOrderModal && (
        <div className={styles.templateSelector} style={{ marginBottom: '1rem', padding: '1rem', background: '#f5f5f5', borderRadius: '4px' }}>
          <h5 style={{ marginTop: 0, marginBottom: '0.75rem' }}>Select a Template:</h5>
          {loadingTemplates ? (
            <p>Loading templates...</p>
          ) : templates.length === 0 ? (
            <p style={{ color: '#666', fontStyle: 'italic' }}>No templates available</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
              {templates.map(template => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => handleUseTemplate(template)}
                  className={styles.secondaryButton}
                  style={{ textAlign: 'left', padding: '0.75rem', fontSize: '0.875rem' }}
                >
                  <div style={{ fontWeight: 600 }}>{template.name}</div>
                  {template.category && (
                    <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>{template.category}</div>
                  )}
                  {template.description && (
                    <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.25rem' }}>
                      {template.description.substring(0, 50)}...
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Improved Lab Order modal (same form as Service Catalog) */}
      {showCreateOrderModal && consultationId && (
        <LabOrderDetailsForm
          serviceName="Lab tests"
          initialTests={formInitialValues?.tests}
          initialClinicalIndication={formInitialValues?.indication}
          onSubmit={handleLabOrderFormSubmit}
          onCancel={() => {
            setShowCreateOrderModal(false);
            setFormInitialValues(null);
          }}
          isSubmitting={isSaving}
        />
      )}

      {/* Lab orders list */}
      {labOrders.length === 0 && !showCreateOrderModal && (
        <p className={styles.emptyState}>No lab orders for this visit.</p>
      )}

      {labOrders.map(order => {
        const result = getResultForOrder(order.id);
        const isCreatingResult = showCreateResult === order.id;

        return (
          <div key={order.id} className={styles.labOrderCard}>
            <div className={styles.orderHeader}>
              <div>
                <strong>Order #{order.id}</strong>
                <span className={styles.statusBadge}>{order.status}</span>
              </div>
              {order.status === 'ORDERED' && !result && user?.role === 'LAB_TECH' && (
                <LabResultPostButton
                  labOrderId={order.id}
                  visitId={visitId}
                  onShowForm={() => setShowCreateResult(order.id)}
                />
              )}
            </div>

            <div className={styles.orderDetails}>
              <div><strong>Tests:</strong> {Array.isArray(order.tests_requested) ? order.tests_requested.join(', ') : JSON.stringify(order.tests_requested)}</div>
              {order.clinical_indication && (
                <div><strong>Indication:</strong> {order.clinical_indication}</div>
              )}
            </div>

            {/* Create result form */}
            {isCreatingResult && (
              <div className={styles.createForm}>
                <h4>Record Lab Result</h4>
                <div className={styles.formGroup}>
                  <label>Result Data</label>
                  <textarea
                    value={newResultData[order.id] || ''}
                    onChange={(e) => setNewResultData(prev => ({ ...prev, [order.id]: e.target.value }))}
                    placeholder="Enter lab findings and results"
                    rows={5}
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Abnormality Flag</label>
                  <select
                    value={newResultFlag[order.id] || 'NORMAL'}
                    onChange={(e) => setNewResultFlag(prev => ({ ...prev, [order.id]: e.target.value as 'NORMAL' | 'ABNORMAL' | 'CRITICAL' }))}
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
                    disabled={isSaving || !newResultData[order.id]?.trim()}
                  >
                    {isSaving ? 'Recording...' : 'Record Result'}
                  </button>
                  <button
                    className={styles.cancelButton}
                    onClick={() => {
                      setShowCreateResult(null);
                      setNewResultData(prev => {
                        const next = { ...prev };
                        delete next[order.id];
                        return next;
                      });
                    }}
                    disabled={isSaving}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Display result if exists */}
            {result && (
              <div className={styles.resultCard}>
                <div className={styles.resultHeader}>
                  <strong>Result</strong>
                  <span className={`${styles.flagBadge} ${styles[`flag${result.abnormal_flag}`]}`}>
                    {result.abnormal_flag}
                  </span>
                </div>
                <div className={styles.resultData}>{result.result_data}</div>
                <div className={styles.resultMeta}>
                  Recorded: {new Date(result.recorded_at).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
