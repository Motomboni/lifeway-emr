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
  /** Creates a consultation record when the doctor places an order before saving notes. */
  ensureConsultation?: () => Promise<number>;
}

// Component for lab order create button with lock check
function LabOrderCreateButton({
  visitId,
  consultationId,
  ensureConsultation,
  onConsultationResolved,
  onShowForm,
}: {
  visitId: string;
  consultationId?: number;
  ensureConsultation?: () => Promise<number>;
  onConsultationResolved: (id: number) => void;
  onShowForm: () => void;
}) {
  const { showError } = useToast();
  const [resolvedId, setResolvedId] = useState<number | undefined>(consultationId);
  const [ensuring, setEnsuring] = useState(false);

  useEffect(() => {
    if (consultationId) {
      setResolvedId(consultationId);
    }
  }, [consultationId]);

  const labOrderLock = useActionLock({
    actionType: 'lab_order',
    params: { visit_id: parseInt(visitId), consultation_id: resolvedId ?? 0 },
    enabled: !!visitId && !!resolvedId,
  });

  const handleClick = async () => {
    setEnsuring(true);
    try {
      let id = resolvedId;
      if (!id && ensureConsultation) {
        id = await ensureConsultation();
        setResolvedId(id);
        onConsultationResolved(id);
      }
      if (!id) {
        showError('Consultation is required to create lab orders');
        return;
      }
      onShowForm();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to start consultation');
    } finally {
      setEnsuring(false);
    }
  };

  if (resolvedId && labOrderLock.isLocked && labOrderLock.lockResult) {
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
      lockResult={resolvedId ? labOrderLock.lockResult : null}
      loading={labOrderLock.loading || ensuring}
      onClick={handleClick}
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

export default function LabInline({ visitId, consultationId, ensureConsultation }: LabInlineProps) {
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
  const [effectiveConsultationId, setEffectiveConsultationId] = useState<number | undefined>(consultationId);
  const isDoctor = user?.role === 'DOCTOR';

  useEffect(() => {
    if (consultationId) {
      setEffectiveConsultationId(consultationId);
    }
  }, [consultationId]);

  const handleLabOrderFormSubmit = async (labOrderDetails: LabOrderDetails) => {
    let orderConsultationId = effectiveConsultationId;
    if (!orderConsultationId && ensureConsultation) {
      try {
        orderConsultationId = await ensureConsultation();
        setEffectiveConsultationId(orderConsultationId);
      } catch {
        showError('Consultation is required to create lab orders');
        return;
      }
    }
    if (!orderConsultationId) {
      showError('Consultation is required to create lab orders');
      return;
    }

    try {
      await createLabOrder(visitId, {
        consultation: orderConsultationId,
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
      <div className={styles.inlineComponent} data-guide-id="lab-inline">
        <h3>Lab Orders</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent} data-guide-id="lab-inline">
      <div className={styles.inlineHeader}>
        <h3>Lab Orders</h3>
        {isDoctor && !showCreateOrderModal && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <LabOrderCreateButton
              visitId={visitId}
              consultationId={effectiveConsultationId}
              ensureConsultation={ensureConsultation}
              onConsultationResolved={setEffectiveConsultationId}
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
        <div className={styles.templateSelector}>
          <h4>Select a Template</h4>
          {loadingTemplates ? (
            <p className={styles.templateStatus}>Loading templates...</p>
          ) : templates.length === 0 ? (
            <p className={styles.helpText}>
              No lab templates are configured yet. An administrator can load the starter set with{' '}
              <code>python manage.py seed_lab_templates</code>.
            </p>
          ) : (
            <div className={styles.templateList}>
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  className={styles.templateItem}
                  onClick={() => handleUseTemplate(template)}
                >
                  <strong>{template.name}</strong>
                  {template.category && (
                    <span className={styles.templateCategory}>{template.category}</span>
                  )}
                  {template.description && (
                    <p className={styles.templateDescription}>
                      {template.description.length > 80
                        ? `${template.description.substring(0, 80)}…`
                        : template.description}
                    </p>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Improved Lab Order modal (same form as Service Catalog) */}
      {showCreateOrderModal && (
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
