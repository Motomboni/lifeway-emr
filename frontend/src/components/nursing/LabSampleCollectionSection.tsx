/**
 * Lab Sample Collection Section Component
 * 
 * Allows Nurse to record lab sample collection from existing lab orders.
 * Visit-scoped and permission-aware.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { fetchLabSampleCollections, createLabSampleCollection, updateLabSampleCollection } from '../../api/nursing';
import { fetchLabOrders } from '../../api/lab';
import { LabSampleCollection, LabSampleCollectionCreate } from '../../types/nursing';
import { LabOrder } from '../../types/lab';
import styles from '../../styles/NurseVisit.module.css';

interface LabSampleCollectionSectionProps {
  visitId: string;
  canCreate: boolean;
}

export default function LabSampleCollectionSection({ visitId, canCreate }: LabSampleCollectionSectionProps) {
  const { showSuccess, showError } = useToast();
  const [collections, setCollections] = useState<LabSampleCollection[]>([]);
  const [labOrders, setLabOrders] = useState<LabOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingLabOrders, setLoadingLabOrders] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [editingCollection, setEditingCollection] = useState<LabSampleCollection | null>(null);
  const [formData, setFormData] = useState<LabSampleCollectionCreate>({
    lab_order: 0,
    collection_time: new Date().toISOString().slice(0, 16),
    sample_type: 'Blood',
    collection_site: '',
    status: 'COLLECTED',
    sample_volume: '',
    container_type: '',
    collection_notes: '',
    reason_if_failed: '',
    merge_with_patient_record: false,
  });

  useEffect(() => {
    loadData();
  }, [visitId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [collectionData, orderData] = await Promise.all([
        fetchLabSampleCollections(parseInt(visitId)).catch(() => []),
        fetchLabOrders(visitId).catch(() => [])
      ]);
      setCollections(Array.isArray(collectionData) ? collectionData : []);
      setLabOrders(Array.isArray(orderData) ? orderData : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load lab sample collections');
    } finally {
      setLoading(false);
    }
  };

  const loadLabOrders = async () => {
    try {
      setLoadingLabOrders(true);
      const data = await fetchLabOrders(visitId);
      setLabOrders(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load lab orders');
    } finally {
      setLoadingLabOrders(false);
    }
  };

  const handleShowForm = () => {
    if (!showForm) {
      loadLabOrders();
    } else {
      handleCancel();
    }
    setShowForm(!showForm);
  };

  const handleEdit = (collection: LabSampleCollection) => {
    setEditingCollection(collection);
    setFormData({
      lab_order: collection.lab_order,
      collection_time: new Date(collection.collection_time).toISOString().slice(0, 16),
      sample_type: collection.sample_type,
      collection_site: collection.collection_site || '',
      status: collection.status,
      sample_volume: collection.sample_volume || '',
      container_type: collection.container_type || '',
      collection_notes: collection.collection_notes || '',
      reason_if_failed: collection.reason_if_failed || '',
      merge_with_patient_record: false,
    });
    loadLabOrders();
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingCollection(null);
    setFormData({
      lab_order: 0,
      collection_time: new Date().toISOString().slice(0, 16),
      sample_type: 'Blood',
      collection_site: '',
      status: 'COLLECTED',
      sample_volume: '',
      container_type: '',
      collection_notes: '',
      reason_if_failed: '',
      merge_with_patient_record: false,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!canCreate) {
      showError('Cannot create or update lab sample collection. Visit must be OPEN and payment cleared.');
      return;
    }
    
    if (!formData.lab_order) {
      showError('Please select a lab order');
      return;
    }
    
    if (formData.status === 'FAILED' && !formData.reason_if_failed?.trim()) {
      showError('Reason is required when collection failed');
      return;
    }
    
    try {
      setSaving(true);
      if (editingCollection) {
        // Update existing collection
        await updateLabSampleCollection(parseInt(visitId), editingCollection.id, formData);
        showSuccess('Lab sample collection updated successfully');
      } else {
        // Create new collection
        await createLabSampleCollection(parseInt(visitId), formData);
        showSuccess('Lab sample collection recorded successfully');
      }
      handleCancel();
      loadData();
    } catch (error: any) {
      showError(error.message || `Failed to ${editingCollection ? 'update' : 'create'} lab sample collection`);
    } finally {
      setSaving(false);
    }
  };

  // Filter lab orders that can be collected (ORDERED or SAMPLE_COLLECTED status)
  const collectibleOrders = labOrders.filter(
    order => order.status === 'ORDERED' || order.status === 'SAMPLE_COLLECTED'
  );

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3>🧪 Lab Sample Collection</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={handleShowForm}
            disabled={saving}
          >
            {showForm ? 'Cancel' : editingCollection ? 'Edit Collection' : '+ Record Sample Collection'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.labSampleForm}>
          <div className={styles.formField}>
            <label>Lab Order *</label>
            {loadingLabOrders ? (
              <div className={styles.loading}>Loading lab orders...</div>
            ) : collectibleOrders.length === 0 ? (
              <div className={styles.warningMessage}>
                No collectible lab orders available. Samples can only be collected for ORDERED or SAMPLE_COLLECTED lab orders.
              </div>
            ) : (
              <select
                value={formData.lab_order}
                onChange={(e) => setFormData({ ...formData, lab_order: parseInt(e.target.value) })}
                required
              >
                <option value={0}>Select a lab order...</option>
                {collectibleOrders.map((order) => (
                  <option key={order.id} value={order.id}>
                    {order.tests_requested?.join(', ') || 'Lab Order'} - {order.status}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className={styles.formGrid}>
            <div className={styles.formField}>
              <label>Collection Time *</label>
              <input
                type="datetime-local"
                value={formData.collection_time}
                onChange={(e) => setFormData({ ...formData, collection_time: e.target.value })}
                required
              />
            </div>
            <div className={styles.formField}>
              <label>Sample Type *</label>
              <select
                value={formData.sample_type}
                onChange={(e) => setFormData({ ...formData, sample_type: e.target.value as LabSampleCollectionCreate['sample_type'] })}
                required
              >
                <option value="Blood">Blood</option>
                <option value="Urine">Urine</option>
                <option value="Stool">Stool</option>
                <option value="Sputum">Sputum</option>
                <option value="Swab">Swab</option>
                <option value="Tissue">Tissue</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div className={styles.formField}>
              <label>Status *</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as LabSampleCollectionCreate['status'] })}
                required
              >
                <option value="COLLECTED">Collected</option>
                <option value="PARTIAL">Partial</option>
                <option value="FAILED">Failed</option>
                <option value="REFUSED">Refused</option>
              </select>
            </div>
            <div className={styles.formField}>
              <label>Collection Site</label>
              <input
                type="text"
                value={formData.collection_site}
                onChange={(e) => setFormData({ ...formData, collection_site: e.target.value })}
                placeholder="e.g., Left arm"
              />
            </div>
            <div className={styles.formField}>
              <label>Sample Volume</label>
              <input
                type="text"
                value={formData.sample_volume}
                onChange={(e) => setFormData({ ...formData, sample_volume: e.target.value })}
                placeholder="e.g., 5ml"
              />
            </div>
            <div className={styles.formField}>
              <label>Container Type</label>
              <input
                type="text"
                value={formData.container_type}
                onChange={(e) => setFormData({ ...formData, container_type: e.target.value })}
                placeholder="e.g., Vacutainer"
              />
            </div>
          </div>
          {formData.status === 'FAILED' && (
            <div className={styles.formField}>
              <label>Reason if Failed *</label>
              <textarea
                value={formData.reason_if_failed}
                onChange={(e) => setFormData({ ...formData, reason_if_failed: e.target.value })}
                rows={3}
                required
                placeholder="Explain why collection failed..."
              />
            </div>
          )}
          <div className={styles.formField}>
            <label>Collection Notes</label>
            <textarea
              value={formData.collection_notes}
              onChange={(e) => setFormData({ ...formData, collection_notes: e.target.value })}
              rows={3}
              placeholder="Additional notes about collection..."
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
              If checked, this lab sample collection will be added to the patient's cumulative medical history.
            </p>
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={saving || collectibleOrders.length === 0} className={styles.saveButton}>
              {saving ? 'Saving...' : editingCollection ? 'Update Collection' : 'Record Collection'}
            </button>
            <button type="button" onClick={handleCancel} className={styles.cancelButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className={styles.loading}>Loading lab sample collections...</div>
      ) : collections.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No lab sample collections recorded yet.</p>
          {canCreate && <p>Click "Record Sample Collection" to add the first entry.</p>}
        </div>
      ) : (
        <div className={styles.collectionsList}>
          {collections.map((collection) => (
            <div key={collection.id} className={styles.collectionCard}>
              <div className={styles.collectionHeader}>
                <div>
                  <strong>{collection.sample_type} Sample</strong>
                  <span className={styles.collectionTests}>
                    {collection.lab_order_tests?.join(', ') || 'Lab Order'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className={`${styles.statusBadge} ${collection.status === 'COLLECTED' ? styles.statusCollected : styles.statusOther}`}>
                    {collection.status}
                  </span>
                  {canCreate && (
                    <button
                      type="button"
                      className={styles.editButton}
                      onClick={() => handleEdit(collection)}
                      title="Edit lab sample collection"
                    >
                      ✏️ Edit
                    </button>
                  )}
                </div>
              </div>
              <div className={styles.collectionDetails}>
                <div className={styles.collectionDetailItem}>
                  <label>Collection Time:</label>
                  <span>{new Date(collection.collection_time).toLocaleString()}</span>
                </div>
                {collection.collection_site && (
                  <div className={styles.collectionDetailItem}>
                    <label>Site:</label>
                    <span>{collection.collection_site}</span>
                  </div>
                )}
                {collection.sample_volume && (
                  <div className={styles.collectionDetailItem}>
                    <label>Volume:</label>
                    <span>{collection.sample_volume}</span>
                  </div>
                )}
                {collection.container_type && (
                  <div className={styles.collectionDetailItem}>
                    <label>Container:</label>
                    <span>{collection.container_type}</span>
                  </div>
                )}
                <div className={styles.collectionDetailItem}>
                  <label>Collected by:</label>
                  <span>{collection.collected_by_name || 'Nurse'} on {new Date(collection.recorded_at).toLocaleString()}</span>
                </div>
              </div>
              {collection.collection_notes && (
                <div className={styles.collectionNotes}>
                  <label>Notes:</label>
                  <p>{collection.collection_notes}</p>
                </div>
              )}
              {collection.reason_if_failed && (
                <div className={styles.collectionNotes}>
                  <label>Reason if Failed:</label>
                  <p>{collection.reason_if_failed}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
