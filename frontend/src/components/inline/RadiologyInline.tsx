/**
 * RadiologyInline Component
 *
 * Service Catalog flow only: GET /visits/{visitId}/radiology/ (RadiologyRequest).
 * Doctor: create orders. Radiology Tech: post report via PATCH. No legacy RadiologyResult.
 */
import React, { useState, useEffect } from 'react';
import { useRadiologyOrders } from '../../hooks/useRadiologyOrders';
import { updateRadiologyReport, draftRadiologyReport } from '../../api/radiology';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface RadiologyInlineProps {
  visitId: string;
  consultationId?: number;
  ensureConsultation?: () => Promise<number>;
}

const IMAGING_TYPES: { value: 'XRAY' | 'CT' | 'MRI' | 'US'; label: string }[] = [
  { value: 'XRAY', label: 'X-Ray' },
  { value: 'CT', label: 'CT Scan' },
  { value: 'MRI', label: 'MRI' },
  { value: 'US', label: 'Ultrasound' },
];

export default function RadiologyInline({ visitId, consultationId, ensureConsultation }: RadiologyInlineProps) {
  const { user } = useAuth();
  const {
    radiologyOrders,
    loading,
    error,
    isSaving,
    createRadiologyOrder,
    refresh
  } = useRadiologyOrders(visitId);
  
  const { showSuccess, showError } = useToast();
  
  const [showCreateOrder, setShowCreateOrder] = useState(false);
  const [showCreateResult, setShowCreateResult] = useState<number | null>(null);
  const [newOrderImagingType, setNewOrderImagingType] = useState<'XRAY' | 'CT' | 'MRI' | 'US'>('XRAY');
  const [newOrderBodyPart, setNewOrderBodyPart] = useState('');
  const [newOrderIndication, setNewOrderIndication] = useState('');
  const [newOrderPriority, setNewOrderPriority] = useState<'ROUTINE' | 'URGENT'>('ROUTINE');
  const [newResultReport, setNewResultReport] = useState<Record<number, string>>({});
  const [newResultImageCount, setNewResultImageCount] = useState<Record<number, number>>({});
  const [draftingReportFor, setDraftingReportFor] = useState<number | null>(null);
  const [effectiveConsultationId, setEffectiveConsultationId] = useState<number | undefined>(consultationId);
  const [ensuringConsultation, setEnsuringConsultation] = useState(false);
  const isDoctor = user?.role === 'DOCTOR';

  useEffect(() => {
    if (consultationId) {
      setEffectiveConsultationId(consultationId);
    }
  }, [consultationId]);

  const resolveConsultationId = async (): Promise<number | null> => {
    if (effectiveConsultationId) {
      return effectiveConsultationId;
    }
    if (!ensureConsultation) {
      return null;
    }
    setEnsuringConsultation(true);
    try {
      const id = await ensureConsultation();
      setEffectiveConsultationId(id);
      return id;
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to start consultation');
      return null;
    } finally {
      setEnsuringConsultation(false);
    }
  };

  const handleCreateOrder = async () => {
    const orderConsultationId = await resolveConsultationId();
    if (!orderConsultationId) {
      showError('Consultation is required to create radiology orders');
      return;
    }

    if (!newOrderBodyPart.trim()) {
      showError('Body part is required');
      return;
    }

    if (!newOrderIndication.trim()) {
      showError('Clinical indication is required');
      return;
    }

    try {
      await createRadiologyOrder(visitId, {
        consultation: orderConsultationId,
        study_type: `${getImagingTypeLabel(newOrderImagingType)} - ${newOrderBodyPart}`,
        clinical_indication: newOrderIndication,
        instructions: `Priority: ${newOrderPriority}`
      });
      showSuccess('Radiology order created successfully');
      setShowCreateOrder(false);
      setNewOrderBodyPart('');
      setNewOrderIndication('');
      setNewOrderPriority('ROUTINE');
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create radiology order');
    }
  };

  const handleCreateResult = async (requestId: number) => {
    // Restrict to Radiology Technicians only
    if (user?.role !== 'RADIOLOGY_TECH') {
      showError('Only Radiology Technicians can record radiology results');
      return;
    }

    const report = newResultReport[requestId];
    if (!report || !report.trim()) {
      showError('Report is required');
      return;
    }

    try {
      // Service Catalog: PATCH RadiologyRequest only. Finding flag is not persisted (legacy RadiologyResult only).
      await updateRadiologyReport(parseInt(visitId), requestId, {
        report: report.trim(),
        image_count: newResultImageCount[requestId] ?? 0,
      });
      showSuccess('Radiology result recorded successfully');
      setShowCreateResult(null);
      setNewResultReport(prev => {
        const next = { ...prev };
        delete next[requestId];
        return next;
      });
      setNewResultImageCount(prev => {
        const next = { ...prev };
        delete next[requestId];
        return next;
      });
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create radiology result');
    }
  };

  const handleDraftReport = async (order: { id: number; study_type: string; clinical_indication?: string }) => {
    if (draftingReportFor !== null) return;
    setDraftingReportFor(order.id);
    try {
      const draft = await draftRadiologyReport(parseInt(visitId), order.id, {
        study_type: order.study_type,
        clinical_indication: order.clinical_indication ?? '',
      });
      setNewResultReport(prev => ({ ...prev, [order.id]: draft.draft }));
      showSuccess('Draft inserted. Edit as needed before saving.');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Could not generate draft');
    } finally {
      setDraftingReportFor(null);
    }
  };

  const getImagingTypeLabel = (type: string): string => {
    return IMAGING_TYPES.find(t => t.value === type)?.label || type;
  };

  if (loading) {
    return (
      <div className={styles.inlineComponent} data-guide-id="radiology-inline">
        <h3>Radiology Orders</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent} data-guide-id="radiology-inline">
      <div className={styles.inlineHeader}>
        <h3>Radiology Orders</h3>
        {isDoctor && !showCreateOrder && (
          <button
            className={styles.addButton}
            onClick={async () => {
              const id = await resolveConsultationId();
              if (!id) {
                showError('Consultation is required to create radiology orders');
                return;
              }
              setShowCreateOrder(true);
            }}
            type="button"
            disabled={ensuringConsultation}
          >
            {ensuringConsultation ? 'Preparing…' : '+ New Order'}
          </button>
        )}
      </div>

      {error && (
        <div className={styles.errorMessage}>{error}</div>
      )}

      {/* Create new radiology order form */}
      {showCreateOrder && (
        <div className={styles.createForm}>
          <h4 style={{ marginBottom: '1rem' }}>Create Radiology Order</h4>
          <div className={styles.formGroup}>
            <label>Imaging Type</label>
            <select
              value={newOrderImagingType}
              onChange={(e) => setNewOrderImagingType(e.target.value as 'XRAY' | 'CT' | 'MRI' | 'US')}
            >
              {IMAGING_TYPES.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>
          <div className={styles.formGroup}>
            <label>Body Part *</label>
            <input
              type="text"
              value={newOrderBodyPart}
              onChange={(e) => setNewOrderBodyPart(e.target.value)}
              placeholder="e.g., Chest, Head, Abdomen"
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Clinical Indication *</label>
            <textarea
              value={newOrderIndication}
              onChange={(e) => setNewOrderIndication(e.target.value)}
              placeholder="Reason for imaging request"
              rows={3}
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Priority</label>
            <select
              value={newOrderPriority}
              onChange={(e) => setNewOrderPriority(e.target.value as 'ROUTINE' | 'URGENT')}
            >
              <option value="ROUTINE">Routine</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>
          <div className={styles.formActions}>
            <button
              className={styles.saveButton}
              onClick={handleCreateOrder}
              disabled={isSaving || !newOrderBodyPart.trim() || !newOrderIndication.trim()}
            >
              {isSaving ? 'Creating...' : 'Create Order'}
            </button>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowCreateOrder(false);
                setNewOrderBodyPart('');
                setNewOrderIndication('');
                setNewOrderPriority('ROUTINE');
              }}
              disabled={isSaving}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Radiology orders list */}
      {radiologyOrders.length === 0 && !showCreateOrder && (
        <p className={styles.emptyState}>No radiology orders for this visit.</p>
      )}

      {radiologyOrders.map(order => {
        const isCreatingResult = showCreateResult === order.id;
        const hasReport = order.report != null && order.report.trim() !== '';

        return (
          <div key={order.id} className={styles.labOrderCard}>
            <div className={styles.orderHeader}>
              <div>
                <strong>Order #{order.id}</strong>
                <span className={styles.statusBadge}>{order.status}</span>
              </div>
              {order.status === 'PENDING' && !hasReport && user?.role === 'RADIOLOGY_TECH' && (
                <button
                  className={styles.addButton}
                  onClick={() => setShowCreateResult(order.id)}
                  type="button"
                >
                  Add Report
                </button>
              )}
            </div>

            <div className={styles.orderDetails}>
              <div><strong>Study Type:</strong> {order.study_type}</div>
              {order.study_code && <div><strong>Code:</strong> {order.study_code}</div>}
              {order.clinical_indication && <div><strong>Indication:</strong> {order.clinical_indication}</div>}
              {order.instructions && <div><strong>Instructions:</strong> {order.instructions}</div>}
            </div>

            {/* Create result form */}
            {isCreatingResult && (
              <div className={styles.createForm}>
                <h4>Record report (Service Catalog)</h4>
                <div className={styles.formGroup}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <label style={{ margin: 0 }}>Report *</label>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      style={{ fontSize: '0.875rem', padding: '0.35rem 0.75rem' }}
                      disabled={draftingReportFor === order.id}
                      onClick={() => handleDraftReport(order)}
                    >
                      {draftingReportFor === order.id ? 'Generating...' : '✨ Draft with AI'}
                    </button>
                  </div>
                  <textarea
                    value={newResultReport[order.id] || ''}
                    onChange={(e) => setNewResultReport(prev => ({ ...prev, [order.id]: e.target.value }))}
                    placeholder="Enter radiology report and interpretation"
                    rows={6}
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Image Count</label>
                  <input
                    type="number"
                    min="0"
                    value={newResultImageCount[order.id] || 0}
                    onChange={(e) => setNewResultImageCount(prev => ({ ...prev, [order.id]: parseInt(e.target.value) || 0 }))}
                  />
                </div>
                <div className={styles.formActions}>
                  <button
                    className={styles.saveButton}
                    onClick={() => handleCreateResult(order.id)}
                    disabled={isSaving || !newResultReport[order.id]?.trim()}
                  >
                    {isSaving ? 'Recording...' : 'Record Result'}
                  </button>
                  <button
                    className={styles.cancelButton}
                    onClick={() => {
                      setShowCreateResult(null);
                      setNewResultReport(prev => {
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

            {/* Display result from RadiologyRequest only. Finding flag not persisted for Service Catalog. */}
            {hasReport && (
              <div className={styles.resultCard}>
                <div className={styles.resultHeader}>
                  <strong>Result</strong>
                </div>
                <div className={styles.resultData}>
                  {order.report}
                </div>
                {order.image_count != null && order.image_count > 0 && (
                  <div className={styles.resultMeta}>
                    Image count: {order.image_count}
                  </div>
                )}
                <div className={styles.resultMeta}>
                  Reported by: {order.reported_by != null ? `ID ${order.reported_by}` : '—'}
                </div>
                <div className={styles.resultMeta}>
                  Report date: {order.report_date ? new Date(order.report_date).toLocaleString() : '—'}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
