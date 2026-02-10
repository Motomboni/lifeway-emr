/**
 * Medication Administration Section Component
 * 
 * Allows Nurse to record medication administration from existing prescriptions.
 * Visit-scoped and permission-aware.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { fetchMedicationAdministrations, createMedicationAdministration, updateMedicationAdministration } from '../../api/nursing';
import { fetchPrescriptions } from '../../api/prescription';
import { MedicationAdministration, MedicationAdministrationCreate } from '../../types/nursing';
import { Prescription } from '../../types/prescription';
import styles from '../../styles/NurseVisit.module.css';

interface MedicationAdministrationSectionProps {
  visitId: string;
  canCreate: boolean;
}

export default function MedicationAdministrationSection({ visitId, canCreate }: MedicationAdministrationSectionProps) {
  const { showSuccess, showError } = useToast();
  const [administrations, setAdministrations] = useState<MedicationAdministration[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPrescriptions, setLoadingPrescriptions] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [editingAdmin, setEditingAdmin] = useState<MedicationAdministration | null>(null);
  const [formData, setFormData] = useState<MedicationAdministrationCreate>({
    prescription: 0,
    administration_time: new Date().toISOString().slice(0, 16),
    dose_administered: '',
    route: 'ORAL',
    site: '',
    status: 'GIVEN',
    administration_notes: '',
    reason_if_held: '',
    merge_with_patient_record: false,
  });

  useEffect(() => {
    loadData();
  }, [visitId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [adminData, prescData] = await Promise.all([
        fetchMedicationAdministrations(parseInt(visitId)).catch(() => []),
        fetchPrescriptions(visitId).catch(() => [])
      ]);
      setAdministrations(Array.isArray(adminData) ? adminData : []);
      setPrescriptions(Array.isArray(prescData) ? prescData : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load medication administrations');
    } finally {
      setLoading(false);
    }
  };

  const loadPrescriptions = async () => {
    try {
      setLoadingPrescriptions(true);
      const data = await fetchPrescriptions(visitId);
      setPrescriptions(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load prescriptions');
    } finally {
      setLoadingPrescriptions(false);
    }
  };

  const handleShowForm = () => {
    if (!showForm) {
      loadPrescriptions();
    } else {
      handleCancel();
    }
    setShowForm(!showForm);
  };

  const handleEdit = (admin: MedicationAdministration) => {
    setEditingAdmin(admin);
    setFormData({
      prescription: admin.prescription,
      administration_time: new Date(admin.administration_time).toISOString().slice(0, 16),
      dose_administered: admin.dose_administered,
      route: admin.route,
      site: admin.site || '',
      status: admin.status,
      administration_notes: admin.administration_notes || '',
      reason_if_held: admin.reason_if_held || '',
      merge_with_patient_record: false,
    });
    loadPrescriptions();
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingAdmin(null);
    setFormData({
      prescription: 0,
      administration_time: new Date().toISOString().slice(0, 16),
      dose_administered: '',
      route: 'ORAL',
      site: '',
      status: 'GIVEN',
      administration_notes: '',
      reason_if_held: '',
      merge_with_patient_record: false,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!canCreate) {
      showError('Cannot record medication administration. Visit must be OPEN and payment cleared.');
      return;
    }
    
    if (!formData.prescription) {
      showError('Please select a prescription');
      return;
    }
    
    if (!formData.dose_administered.trim()) {
      showError('Dose administered is required');
      return;
    }
    
    if (formData.status === 'HELD' && !formData.reason_if_held?.trim()) {
      showError('Reason is required when medication is held');
      return;
    }
    
    try {
      setSaving(true);
      await createMedicationAdministration(parseInt(visitId), formData);
      showSuccess('Medication administration recorded successfully');
      setShowForm(false);
      setFormData({
        prescription: 0,
        administration_time: new Date().toISOString().slice(0, 16),
        dose_administered: '',
        route: 'ORAL',
        site: '',
        status: 'GIVEN',
        administration_notes: '',
        reason_if_held: '',
        merge_with_patient_record: false,
      });
      loadData();
    } catch (error: any) {
      showError(error.message || 'Failed to record medication administration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3>💊 Medication Administration</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={handleShowForm}
            disabled={saving}
          >
            {showForm ? 'Cancel' : editingAdmin ? 'Edit Administration' : '+ Record Administration'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.medicationForm}>
          <div className={styles.formField}>
            <label>Prescription *</label>
            {loadingPrescriptions ? (
              <div className={styles.loading}>Loading prescriptions...</div>
            ) : prescriptions.length === 0 ? (
              <div className={styles.warningMessage}>
                No prescriptions available for this visit. Medication can only be administered from existing prescriptions.
              </div>
            ) : (
              <select
                value={formData.prescription}
                onChange={(e) => setFormData({ ...formData, prescription: parseInt(e.target.value) })}
                required
              >
                <option value={0}>Select a prescription...</option>
                {prescriptions.map((presc) => (
                  <option key={presc.id} value={presc.id}>
                    {presc.drug} - {presc.dosage} {presc.frequency || ''}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className={styles.formGrid}>
            <div className={styles.formField}>
              <label>Administration Time *</label>
              <input
                type="datetime-local"
                value={formData.administration_time}
                onChange={(e) => setFormData({ ...formData, administration_time: e.target.value })}
                required
              />
            </div>
            <div className={styles.formField}>
              <label>Dose Administered *</label>
              <input
                type="text"
                value={formData.dose_administered}
                onChange={(e) => setFormData({ ...formData, dose_administered: e.target.value })}
                required
                placeholder="e.g., 10mg"
              />
            </div>
            <div className={styles.formField}>
              <label>Route *</label>
              <select
                value={formData.route}
                onChange={(e) => setFormData({ ...formData, route: e.target.value as MedicationAdministrationCreate['route'] })}
                required
              >
                <option value="ORAL">Oral</option>
                <option value="IV">IV</option>
                <option value="IM">IM</option>
                <option value="SC">Subcutaneous</option>
                <option value="TOPICAL">Topical</option>
                <option value="INHALATION">Inhalation</option>
                <option value="RECTAL">Rectal</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div className={styles.formField}>
              <label>Site</label>
              <input
                type="text"
                value={formData.site}
                onChange={(e) => setFormData({ ...formData, site: e.target.value })}
                placeholder="e.g., Left arm"
              />
            </div>
            <div className={styles.formField}>
              <label>Status *</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as MedicationAdministrationCreate['status'] })}
                required
              >
                <option value="GIVEN">Given</option>
                <option value="REFUSED">Refused</option>
                <option value="HELD">Held</option>
                <option value="NOT_AVAILABLE">Not Available</option>
                <option value="ERROR">Error</option>
              </select>
            </div>
          </div>
          {formData.status === 'HELD' && (
            <div className={styles.formField}>
              <label>Reason if Held *</label>
              <textarea
                value={formData.reason_if_held}
                onChange={(e) => setFormData({ ...formData, reason_if_held: e.target.value })}
                rows={3}
                required
                placeholder="Explain why medication was held..."
              />
            </div>
          )}
          <div className={styles.formField}>
            <label>Administration Notes</label>
            <textarea
              value={formData.administration_notes}
              onChange={(e) => setFormData({ ...formData, administration_notes: e.target.value })}
              rows={3}
              placeholder="Additional notes about administration..."
            />
          </div>
          <div className={styles.formField}>
            <label>
              <input
                type="checkbox"
                checked={formData.merge_with_patient_record || false}
                onChange={(e) => setFormData({ ...formData, merge_with_patient_record: e.target.checked })}
              />
              Merge with patient's medical record
            </label>
            <p className={styles.helpText}>
              If checked, this medication administration will be added to the patient's cumulative medical history.
            </p>
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={saving || prescriptions.length === 0} className={styles.saveButton}>
              {saving ? 'Saving...' : editingAdmin ? 'Update Administration' : 'Record Administration'}
            </button>
            <button type="button" onClick={handleCancel} className={styles.cancelButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className={styles.loading}>Loading medication administrations...</div>
      ) : administrations.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No medication administrations recorded yet.</p>
          {canCreate && <p>Click "Record Administration" to add the first entry.</p>}
        </div>
      ) : (
        <div className={styles.administrationsList}>
          {administrations.map((admin) => (
            <div key={admin.id} className={styles.administrationCard}>
              <div className={styles.administrationHeader}>
                <div>
                  <strong>{admin.prescription_details?.drug || admin.prescription_details?.drug_name || 'Medication'}</strong>
                  <span className={styles.administrationDose}>
                    {admin.dose_administered} via {admin.route === 'ORAL' ? 'Oral' :
                     admin.route === 'IV' ? 'IV' :
                     admin.route === 'IM' ? 'IM' :
                     admin.route === 'SC' ? 'Subcutaneous' :
                     admin.route === 'TOPICAL' ? 'Topical' :
                     admin.route === 'INHALATION' ? 'Inhalation' :
                     admin.route === 'RECTAL' ? 'Rectal' :
                     admin.route === 'OTHER' ? 'Other' :
                     admin.route}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className={`${styles.statusBadge} ${admin.status === 'GIVEN' ? styles.statusGiven : styles.statusOther}`}>
                    {admin.status}
                  </span>
                  {canCreate && (
                    <button
                      type="button"
                      className={styles.editButton}
                      onClick={() => handleEdit(admin)}
                      title="Edit medication administration"
                    >
                      ✏️ Edit
                    </button>
                  )}
                </div>
              </div>
              <div className={styles.administrationDetails}>
                <div className={styles.administrationDetailItem}>
                  <label>Time:</label>
                  <span>{new Date(admin.administration_time).toLocaleString()}</span>
                </div>
                {admin.site && (
                  <div className={styles.administrationDetailItem}>
                    <label>Site:</label>
                    <span>{admin.site}</span>
                  </div>
                )}
                <div className={styles.administrationDetailItem}>
                  <label>Recorded by:</label>
                  <span>{admin.administered_by_name || 'Nurse'} on {new Date(admin.recorded_at).toLocaleString()}</span>
                </div>
              </div>
              {admin.administration_notes && (
                <div className={styles.administrationNotes}>
                  <label>Notes:</label>
                  <p>{admin.administration_notes}</p>
                </div>
              )}
              {admin.reason_if_held && (
                <div className={styles.administrationNotes}>
                  <label>Reason if Held:</label>
                  <p>{admin.reason_if_held}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
