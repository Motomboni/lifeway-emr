/**
 * Charges Breakdown Component
 * 
 * Displays all charges grouped by department with ability to add MISC charges.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { formatCurrency } from '../../utils/currency';
import { BillingPermissions } from '../../hooks/useBillingPermissions';
import { Visit } from '../../types/visit';
import { ChargeCreateData, VisitCharge, Service, addServiceToBill } from '../../api/billing';
import { ChargesTableSkeleton } from './BillingSkeleton';
import { useToast } from '../../hooks/useToast';
import { getVisitCharges, createCharge } from '../../api/billing';
import ServiceSearchInput from './ServiceSearchInput';
import { logger } from '../../utils/logger';
import styles from './ChargesBreakdown.module.css';

interface ChargesBreakdownProps {
  visitId: number;
  visit: Visit;
  permissions: BillingPermissions;
  onUpdate: () => void;
}

const DEPARTMENT_LABELS: Record<string, string> = {
  CONSULTATION: 'Consultation',
  LAB: 'Laboratory',
  RADIOLOGY: 'Radiology',
  DRUG: 'Pharmacy',
  PROCEDURE: 'Procedures',
  MISC: 'Miscellaneous',
};

const DEPARTMENT_ICONS: Record<string, string> = {
  CONSULTATION: '🩺',
  LAB: '🧪',
  RADIOLOGY: '📷',
  DRUG: '💊',
  PROCEDURE: '⚕️',
  MISC: '📋',
};

export default function ChargesBreakdown({
  visitId,
  visit,
  permissions,
  onUpdate,
}: ChargesBreakdownProps) {
  const { showSuccess, showError } = useToast();
  const [charges, setCharges] = useState<VisitCharge[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showServiceSearch, setShowServiceSearch] = useState(false);
  const [formData, setFormData] = useState<ChargeCreateData>({
    amount: '',
    description: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [addingService, setAddingService] = useState(false);

  const loadCharges = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getVisitCharges(visitId);
      setCharges(data);
    } catch (error: any) {
      showError('Failed to load charges');
      console.error('Failed to load charges:', error);
    } finally {
      setLoading(false);
    }
  }, [visitId, showError]);

  useEffect(() => {
    loadCharges();
  }, [loadCharges]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.amount || !formData.description) {
      showError('Please fill in all fields');
      return;
    }

    const amount = parseFloat(formData.amount);
    if (isNaN(amount) || amount <= 0) {
      showError('Please enter a valid amount');
      return;
    }

    try {
      setSubmitting(true);
      await createCharge(visitId, {
        amount: formData.amount,
        description: formData.description,
      });
      showSuccess('Charge added successfully');
      setFormData({ amount: '', description: '' });
      setShowAddForm(false);
      await loadCharges();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to add charge');
    } finally {
      setSubmitting(false);
    }
  };

  const handleServiceSelect = async (service: Service) => {
    if (visit.status === 'CLOSED') {
      showError('Cannot add services to a closed visit');
      return;
    }

    try {
      setAddingService(true);
      logger.debug('Adding service to bill:', { visitId, department: service.department, service_code: service.service_code });
      
      await addServiceToBill({
        visit_id: visitId,
        department: service.department,
        service_code: service.service_code,
      });
      
      logger.debug('Service added successfully, reloading charges');
      showSuccess(`${service.service_name} added to bill`);
      
      // Reload charges and update billing summary
      await loadCharges();
      onUpdate();
      
      // Close the service search after successful addition
      setShowServiceSearch(false);
    } catch (error: any) {
      console.error('Error adding service to bill:', error);
      showError(error.message || `Failed to add ${service.service_name}`);
    } finally {
      setAddingService(false);
    }
  };

  // Group charges by department
  const groupedCharges = charges.reduce((acc: Record<string, VisitCharge[]>, charge: VisitCharge) => {
    const dept = charge.category;
    if (!acc[dept]) {
      acc[dept] = [];
    }
    acc[dept].push(charge);
    return acc;
  }, {} as Record<string, VisitCharge[]>);

  const totalCharges = charges.reduce((sum: number, charge: VisitCharge) => sum + parseFloat(charge.amount), 0);

  if (loading) {
    return <ChargesTableSkeleton />;
  }

  const isVisitClosed = visit.status === 'CLOSED';

  return (
    <div className={styles.container}>
      {/* Header with Add Buttons */}
      <div className={styles.header}>
        <div>
          <h3 className={styles.headerTitle}>Charges Breakdown</h3>
          <p className={styles.headerSubtitle}>
            Total: <span className={styles.headerSubtitleAmount}>{formatCurrency(totalCharges.toString())}</span>
          </p>
        </div>
        {permissions.canEditBilling && !isVisitClosed && (
          <div className={styles.actions}>
            <button
              onClick={() => {
                setShowServiceSearch(!showServiceSearch);
                setShowAddForm(false);
              }}
              className={styles.addCatalogButton}
            >
              {showServiceSearch ? 'Cancel' : '🔍 Add from Catalog'}
            </button>
            <button
              onClick={() => {
                setShowAddForm(!showAddForm);
                setShowServiceSearch(false);
              }}
              className={styles.addManualButton}
            >
              {showAddForm ? 'Cancel' : '+ Add Manual Charge'}
            </button>
          </div>
        )}
      </div>

      {/* Add Service from Catalog */}
      {showServiceSearch && permissions.canEditBilling && !isVisitClosed && (
        <div className={styles.serviceSearchContainer}>
          <div className={styles.serviceSearchHeader}>
            <h4 className={styles.serviceSearchTitle}>
              🔍 Search Service Catalog
            </h4>
            <p className={styles.serviceSearchDescription}>
              Search from 437 available services. Price will be added automatically.
            </p>
          </div>
          <ServiceSearchInput
            onServiceSelect={handleServiceSelect}
            disabled={addingService}
            placeholder="Type to search (e.g., consultation, dental, vaccine)..."
          />
          {addingService && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280', display: 'flex', alignItems: 'center' }}>
              <div style={{ animation: 'spin 1s linear infinite', borderRadius: '9999px', height: '1rem', width: '1rem', border: '2px solid transparent', borderBottomColor: '#16a34a', marginRight: '0.5rem' }}></div>
              Adding service...
            </div>
          )}
        </div>
      )}

      {/* Add Manual Charge Form */}
      {showAddForm && permissions.canEditBilling && !isVisitClosed && (
        <form onSubmit={handleSubmit} className={styles.addFormContainer}>
          <div className={styles.formHeader}>
            <h4 className={styles.formTitle}>
              + Add Manual Charge
            </h4>
            <p className={styles.formDescription}>
              Add a custom charge not in the service catalog.
            </p>
          </div>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Description *
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className={styles.formInput}
                placeholder="Enter charge description"
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                className={styles.formInput}
                placeholder="0.00"
                required
              />
            </div>
          </div>
          <div className={styles.formActions}>
            <button
              type="submit"
              disabled={submitting}
              className={styles.submitButton}
            >
              {submitting ? 'Adding...' : 'Add Charge'}
            </button>
          </div>
        </form>
      )}

      {/* Charges by Department */}
      {Object.keys(groupedCharges).length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyStateText}>No charges recorded for this visit</p>
        </div>
      ) : (
        <div className={styles.chargesList}>
          {Object.entries(groupedCharges).map(([department, deptCharges]) => {
            const chargesArray = deptCharges as VisitCharge[];
            const deptTotal = chargesArray.reduce((sum: number, c: VisitCharge) => sum + parseFloat(c.amount), 0);
            return (
              <div key={department} className={styles.departmentGroup}>
                <div className={styles.departmentHeader}>
                  <div className={styles.departmentHeaderLeft}>
                    <span className={styles.departmentIcon}>{DEPARTMENT_ICONS[department] || '📋'}</span>
                    <h4 className={styles.departmentName}>
                      {DEPARTMENT_LABELS[department] || department}
                    </h4>
                    <span className={styles.departmentCount}>
                      ({chargesArray.length} {chargesArray.length === 1 ? 'item' : 'items'})
                    </span>
                  </div>
                  <span className={styles.departmentTotal}>
                    {formatCurrency(deptTotal.toString())}
                  </span>
                </div>
                <div className={styles.chargesItems}>
                  {chargesArray.map((charge) => (
                    <div key={charge.id} className={styles.chargeItem}>
                      <div className={styles.chargeContent}>
                        <div className={styles.chargeLeft}>
                          <p className={styles.chargeDescription}>{charge.description}</p>
                          <div className={styles.chargeMeta}>
                            <span className={styles.chargeDate}>
                              {new Date(charge.created_at).toLocaleDateString('en-NG', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            {charge.created_by_system && (
                              <span className={styles.systemBadge}>
                                System Generated
                              </span>
                            )}
                          </div>
                        </div>
                        <div className={styles.chargeAmount}>
                          {formatCurrency(charge.amount)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Total Summary */}
      {charges.length > 0 && (
        <div className={styles.totalSummary}>
          <div className={styles.totalSummaryContent}>
            <span className={styles.totalSummaryLabel}>Total Charges</span>
            <span className={styles.totalSummaryAmount}>
              {formatCurrency(totalCharges.toString())}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

