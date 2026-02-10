/**
 * Drugs Management Page
 * 
 * For Pharmacists to create and manage drugs/medications in the catalog.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { 
  fetchDrugs, 
  createDrug, 
  updateDrug, 
  deleteDrug,
  DrugCreateData,
  DrugUpdateData,
  PaginatedDrugResponse
} from '../api/drug';
import { Drug } from '../types/drug';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Drugs.module.css';

export default function DrugsPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingDrug, setEditingDrug] = useState<Drug | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<DrugCreateData>({
    name: '',
    generic_name: '',
    drug_code: '',
    drug_class: '',
    dosage_forms: '',
    common_dosages: '',
    cost_price: undefined,
    sales_price: undefined,
    description: '',
    is_active: true,
  });

  useEffect(() => {
    loadDrugs();
  }, []);

  const loadDrugs = async () => {
    try {
      setLoading(true);
      const response = await fetchDrugs();
      // Handle both array and paginated response
      const drugsArray = Array.isArray(response) 
        ? response 
        : (response as PaginatedDrugResponse)?.results || [];
      setDrugs(drugsArray);
    } catch (error) {
      console.error('Error loading drugs:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load drugs';
      showError(errorMessage);
      setDrugs([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      showError('Drug name is required');
      return;
    }

    try {
      setIsSaving(true);
      await createDrug(formData);
      showSuccess('Drug created successfully');
      resetForm();
      setShowCreateForm(false);
      await loadDrugs();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create drug';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingDrug) return;
    if (!formData.name.trim()) {
      showError('Drug name is required');
      return;
    }

    try {
      setIsSaving(true);
      await updateDrug(editingDrug.id, formData as DrugUpdateData);
      showSuccess('Drug updated successfully');
      resetForm();
      setEditingDrug(null);
      await loadDrugs();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update drug';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (drugId: number) => {
    if (!window.confirm('Are you sure you want to deactivate this drug?')) {
      return;
    }

    try {
      await deleteDrug(drugId);
      showSuccess('Drug deactivated successfully');
      await loadDrugs();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to deactivate drug';
      showError(errorMessage);
    }
  };

  const handleEdit = (drug: Drug) => {
    setEditingDrug(drug);
    setFormData({
      name: drug.name,
      generic_name: drug.generic_name || '',
      drug_code: drug.drug_code || '',
      drug_class: drug.drug_class || '',
      dosage_forms: drug.dosage_forms || '',
      common_dosages: drug.common_dosages || '',
      cost_price: drug.cost_price,
      sales_price: drug.sales_price,
      description: drug.description || '',
      is_active: drug.is_active,
    });
    setShowCreateForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      generic_name: '',
      drug_code: '',
      drug_class: '',
      dosage_forms: '',
      common_dosages: '',
      cost_price: undefined,
      sales_price: undefined,
      description: '',
      is_active: true,
    });
    setEditingDrug(null);
  };

  const handleCancel = () => {
    resetForm();
    setShowCreateForm(false);
  };

  if (user?.role !== 'PHARMACIST') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Pharmacists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.drugsPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Drug Catalog Management</h1>
        <p>Create and manage drugs/medications in the catalog</p>
      </header>

      <div className={styles.content}>
        <div className={styles.actions}>
          {!showCreateForm && (
            <button
              className={styles.addButton}
              onClick={() => {
                resetForm();
                setShowCreateForm(true);
              }}
            >
              + Add New Drug
            </button>
          )}
        </div>

        {/* Create/Edit Form */}
        {showCreateForm && (
          <div className={styles.formContainer}>
            <h2>{editingDrug ? 'Edit Drug' : 'Create New Drug'}</h2>
            <div className={styles.form}>
              <div className={styles.formGroup}>
                <label>Drug Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Paracetamol, Amoxicillin"
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label>Generic Name</label>
                <input
                  type="text"
                  value={formData.generic_name}
                  onChange={(e) => setFormData({ ...formData, generic_name: e.target.value })}
                  placeholder="e.g., Acetaminophen"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Drug Code</label>
                <input
                  type="text"
                  value={formData.drug_code}
                  onChange={(e) => setFormData({ ...formData, drug_code: e.target.value })}
                  placeholder="e.g., NDC code, internal code"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Drug Class</label>
                <input
                  type="text"
                  value={formData.drug_class}
                  onChange={(e) => setFormData({ ...formData, drug_class: e.target.value })}
                  placeholder="e.g., Antibiotic, Analgesic, Antihypertensive"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Dosage Forms</label>
                <input
                  type="text"
                  value={formData.dosage_forms}
                  onChange={(e) => setFormData({ ...formData, dosage_forms: e.target.value })}
                  placeholder="e.g., Tablet, Capsule, Syrup"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Common Dosages</label>
                <input
                  type="text"
                  value={formData.common_dosages}
                  onChange={(e) => setFormData({ ...formData, common_dosages: e.target.value })}
                  placeholder="e.g., 250mg, 500mg, 1000mg"
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Cost Price (₦)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.cost_price ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      cost_price: e.target.value ? parseFloat(e.target.value) : undefined 
                    })}
                    placeholder="0.00"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label>Sales Price (₦)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.sales_price ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      sales_price: e.target.value ? parseFloat(e.target.value) : undefined 
                    })}
                    placeholder="0.00"
                  />
                </div>
              </div>

              {formData.cost_price !== undefined && formData.sales_price !== undefined && 
               formData.cost_price > 0 && formData.sales_price > 0 && (
                <div className={styles.profitInfo}>
                  <p>
                    <strong>Profit:</strong> ₦{((formData.sales_price - formData.cost_price) || 0).toFixed(2)}
                    {' '}
                    <strong>Margin:</strong> {formData.cost_price > 0 
                      ? (((formData.sales_price - formData.cost_price) / formData.cost_price) * 100).toFixed(2)
                      : '0.00'}%
                  </p>
                </div>
              )}

              <div className={styles.formGroup}>
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description, indications, etc."
                  rows={4}
                />
              </div>

              <div className={styles.formGroup}>
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                  Active (available for use)
                </label>
              </div>

              <div className={styles.formActions}>
                <button
                  className={styles.saveButton}
                  onClick={editingDrug ? handleUpdate : handleCreate}
                  disabled={isSaving || !formData.name.trim()}
                >
                  {isSaving ? 'Saving...' : editingDrug ? 'Update Drug' : 'Create Drug'}
                </button>
                <button
                  className={styles.cancelButton}
                  onClick={handleCancel}
                  disabled={isSaving}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Drugs List */}
        <div className={styles.drugsList}>
          <h2>Drug Catalog ({drugs.length})</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : drugs.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No drugs in catalog. Create your first drug to get started.</p>
            </div>
          ) : (
            <div className={styles.drugsGrid}>
              {drugs.map((drug) => (
                <div key={drug.id} className={styles.drugCard}>
                  <div className={styles.drugHeader}>
                    <h3>{drug.name}</h3>
                    <span className={`${styles.statusBadge} ${drug.is_active ? styles.active : styles.inactive}`}>
                      {drug.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className={styles.drugDetails}>
                    {drug.generic_name && (
                      <p><strong>Generic:</strong> {drug.generic_name}</p>
                    )}
                    {drug.drug_code && (
                      <p><strong>Code:</strong> {drug.drug_code}</p>
                    )}
                    {drug.drug_class && (
                      <p><strong>Class:</strong> {drug.drug_class}</p>
                    )}
                    {drug.dosage_forms && (
                      <p><strong>Forms:</strong> {drug.dosage_forms}</p>
                    )}
                    {drug.common_dosages && (
                      <p><strong>Dosages:</strong> {drug.common_dosages}</p>
                    )}
                    {(drug.cost_price !== undefined && drug.cost_price !== null || 
                      drug.sales_price !== undefined && drug.sales_price !== null) && (
                      <div className={styles.pricingInfo}>
                        {drug.cost_price !== undefined && drug.cost_price !== null && (
                          <p><strong>Cost Price:</strong> ₦{Number(drug.cost_price).toFixed(2)}</p>
                        )}
                        {drug.sales_price !== undefined && drug.sales_price !== null && (
                          <p><strong>Sales Price:</strong> ₦{Number(drug.sales_price).toFixed(2)}</p>
                        )}
                        {drug.profit !== undefined && drug.profit !== null && (
                          <p className={styles.profit}>
                            <strong>Profit:</strong> ₦{Number(drug.profit).toFixed(2)}
                            {drug.profit_margin !== undefined && drug.profit_margin !== null && (
                              <span> ({Number(drug.profit_margin).toFixed(2)}%)</span>
                            )}
                          </p>
                        )}
                      </div>
                    )}
                    {drug.description && (
                      <p className={styles.description}>{drug.description}</p>
                    )}
                  </div>
                  <div className={styles.drugActions}>
                    <button
                      className={styles.editButton}
                      onClick={() => handleEdit(drug)}
                    >
                      Edit
                    </button>
                    {drug.is_active && (
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(drug.id)}
                      >
                        Deactivate
                      </button>
                    )}
                  </div>
                  <div className={styles.drugMeta}>
                    <p>Created by: {drug.created_by_name || 'Unknown'}</p>
                    <p>Created: {new Date(drug.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
