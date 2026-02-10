/**
 * Radiology Study Types Catalog Management Page
 * 
 * For Doctors and Radiology Techs to create and manage radiology study types in the catalog.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchRadiologyStudyTypes,
  fetchActiveRadiologyStudyTypes,
  getRadiologyStudyCategories,
  createRadiologyStudyType,
  updateRadiologyStudyType,
  deleteRadiologyStudyType,
  RadiologyStudyTypeFilters,
} from '../api/radiologyStudyTypes';
import {
  RadiologyStudyType,
  RadiologyStudyTypeCreate,
  RadiologyStudyTypeUpdate,
  RadiologyStudyCategory,
} from '../types/radiologyStudyTypes';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/RadiologyStudyTypes.module.css';

export default function RadiologyStudyTypesPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  
  const [studyTypes, setStudyTypes] = useState<RadiologyStudyType[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingStudyType, setEditingStudyType] = useState<RadiologyStudyType | null>(null);
  
  // Filters
  const [filters, setFilters] = useState<RadiologyStudyTypeFilters>({
    is_active: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form state
  const [formData, setFormData] = useState<RadiologyStudyTypeCreate>({
    study_code: '',
    study_name: '',
    category: 'OTHER',
    description: '',
    protocol: '',
    preparation_instructions: '',
    contrast_required: false,
    contrast_type: '',
    estimated_duration_minutes: null,
    body_part: '',
    is_active: true,
    requires_sedation: false,
    radiation_dose: '',
  });

  useEffect(() => {
    loadStudyTypes();
    loadCategories();
  }, [filters]);

  useEffect(() => {
    if (searchQuery) {
      const timeoutId = setTimeout(() => {
        setFilters(prev => ({ ...prev, search: searchQuery }));
      }, 300);
      return () => clearTimeout(timeoutId);
    } else {
      setFilters(prev => {
        const { search, ...rest } = prev;
        return rest;
      });
    }
  }, [searchQuery]);

  const loadStudyTypes = async () => {
    try {
      setLoading(true);
      const data = await fetchRadiologyStudyTypes(filters);
      setStudyTypes(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading radiology study types:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load radiology study types';
      showError(errorMessage);
      setStudyTypes([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const cats = await getRadiologyStudyCategories();
      setCategories(cats);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const handleCreate = async () => {
    if (!formData.study_code.trim() || !formData.study_name.trim()) {
      showError('Study code and name are required');
      return;
    }

    if (formData.contrast_required && (!formData.contrast_type || !formData.contrast_type.trim())) {
      showError('Contrast type is required when contrast is required');
      return;
    }

    try {
      setIsSaving(true);
      await createRadiologyStudyType(formData);
      showSuccess('Radiology study type created successfully');
      resetForm();
      setShowCreateForm(false);
      await loadStudyTypes();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create radiology study type';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingStudyType) return;
    if (!formData.study_code.trim() || !formData.study_name.trim()) {
      showError('Study code and name are required');
      return;
    }

    if (formData.contrast_required && (!formData.contrast_type || !formData.contrast_type.trim())) {
      showError('Contrast type is required when contrast is required');
      return;
    }

    try {
      setIsSaving(true);
      await updateRadiologyStudyType(editingStudyType.id, formData as RadiologyStudyTypeUpdate);
      showSuccess('Radiology study type updated successfully');
      resetForm();
      setEditingStudyType(null);
      setShowCreateForm(false);
      await loadStudyTypes();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update radiology study type';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (studyTypeId: number) => {
    if (!window.confirm('Are you sure you want to delete this radiology study type?')) {
      return;
    }

    try {
      await deleteRadiologyStudyType(studyTypeId);
      showSuccess('Radiology study type deleted successfully');
      await loadStudyTypes();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete radiology study type';
      showError(errorMessage);
    }
  };

  const handleEdit = (studyType: RadiologyStudyType) => {
    setEditingStudyType(studyType);
    setFormData({
      study_code: studyType.study_code,
      study_name: studyType.study_name,
      category: studyType.category,
      description: studyType.description || '',
      protocol: studyType.protocol || '',
      preparation_instructions: studyType.preparation_instructions || '',
      contrast_required: studyType.contrast_required,
      contrast_type: studyType.contrast_type || '',
      estimated_duration_minutes: studyType.estimated_duration_minutes,
      body_part: studyType.body_part || '',
      is_active: studyType.is_active,
      requires_sedation: studyType.requires_sedation,
      radiation_dose: studyType.radiation_dose || '',
    });
    setShowCreateForm(true);
  };

  const resetForm = () => {
    setFormData({
      study_code: '',
      study_name: '',
      category: 'OTHER',
      description: '',
      protocol: '',
      preparation_instructions: '',
      contrast_required: false,
      contrast_type: '',
      estimated_duration_minutes: null,
      body_part: '',
      is_active: true,
      requires_sedation: false,
      radiation_dose: '',
    });
    setEditingStudyType(null);
  };

  const handleCancel = () => {
    resetForm();
    setShowCreateForm(false);
  };

  const canManage = user?.role === 'DOCTOR' || user?.role === 'RADIOLOGY_TECH';

  if (!canManage) {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Doctors and Radiology Technicians only.</p>
      </div>
    );
  }

  return (
    <div className={styles.catalogPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Radiology Study Types Catalog</h1>
        <p>Create and manage available radiology study types and protocols</p>
      </header>

      <div className={styles.content}>
        <div className={styles.filters}>
          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by code, name, description, or body part..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className={styles.filterGroup}>
            <label>
              Category:
              <select
                value={filters.category || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    category: e.target.value ? (e.target.value as RadiologyStudyCategory) : undefined,
                  })
                }
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Status:
              <select
                value={filters.is_active === undefined ? '' : filters.is_active.toString()}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    is_active: e.target.value === '' ? undefined : e.target.value === 'true',
                  })
                }
              >
                <option value="">All</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>
            <label>
              Contrast Required:
              <select
                value={filters.contrast_required === undefined ? '' : filters.contrast_required.toString()}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    contrast_required: e.target.value === '' ? undefined : e.target.value === 'true',
                  })
                }
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
          </div>
        </div>

        <div className={styles.actions}>
          {!showCreateForm && (
            <button
              className={styles.addButton}
              onClick={() => {
                resetForm();
                setShowCreateForm(true);
              }}
            >
              + Add New Study Type
            </button>
          )}
        </div>

        {/* Create/Edit Form */}
        {showCreateForm && (
          <div className={styles.formContainer}>
            <h2>{editingStudyType ? 'Edit Radiology Study Type' : 'Create New Radiology Study Type'}</h2>
            <div className={styles.form}>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Study Code *</label>
                  <input
                    type="text"
                    value={formData.study_code}
                    onChange={(e) => setFormData({ ...formData, study_code: e.target.value.toUpperCase() })}
                    placeholder="e.g., CXR, CT-HEAD, MRI-BRAIN"
                    required
                    disabled={!!editingStudyType}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Study Name *</label>
                  <input
                    type="text"
                    value={formData.study_name}
                    onChange={(e) => setFormData({ ...formData, study_name: e.target.value })}
                    placeholder="e.g., Chest X-Ray"
                    required
                  />
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Category *</label>
                  <select
                    value={formData.category}
                    onChange={(e) =>
                      setFormData({ ...formData, category: e.target.value as RadiologyStudyCategory })
                    }
                    required
                  >
                    <option value="X_RAY">X-Ray</option>
                    <option value="CT_SCAN">CT Scan</option>
                    <option value="MRI">MRI</option>
                    <option value="ULTRASOUND">Ultrasound</option>
                    <option value="MAMMOGRAPHY">Mammography</option>
                    <option value="DEXA_SCAN">DEXA Scan</option>
                    <option value="NUCLEAR_MEDICINE">Nuclear Medicine</option>
                    <option value="FLUOROSCOPY">Fluoroscopy</option>
                    <option value="ANGIOGRAPHY">Angiography</option>
                    <option value="ECHOCARDIOGRAM">Echocardiogram</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label>Body Part</label>
                  <input
                    type="text"
                    value={formData.body_part}
                    onChange={(e) => setFormData({ ...formData, body_part: e.target.value })}
                    placeholder="e.g., Head, Chest, Abdomen"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description of what the study examines"
                  rows={3}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Protocol</label>
                <textarea
                  value={formData.protocol}
                  onChange={(e) => setFormData({ ...formData, protocol: e.target.value })}
                  placeholder="Protocol or procedure details for performing the study"
                  rows={4}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Preparation Instructions</label>
                <textarea
                  value={formData.preparation_instructions}
                  onChange={(e) => setFormData({ ...formData, preparation_instructions: e.target.value })}
                  placeholder="Patient preparation instructions (e.g., fasting, contrast)"
                  rows={3}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Estimated Duration (minutes)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.estimated_duration_minutes || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        estimated_duration_minutes: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    placeholder="Estimated minutes"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Radiation Dose</label>
                  <input
                    type="text"
                    value={formData.radiation_dose}
                    onChange={(e) => setFormData({ ...formData, radiation_dose: e.target.value })}
                    placeholder="e.g., 2 mSv"
                  />
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.contrast_required}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          contrast_required: e.target.checked,
                          contrast_type: e.target.checked ? formData.contrast_type : '',
                        });
                      }}
                    />
                    Contrast Required
                  </label>
                </div>
                {formData.contrast_required && (
                  <div className={styles.formGroup}>
                    <label>Contrast Type *</label>
                    <input
                      type="text"
                      value={formData.contrast_type}
                      onChange={(e) => setFormData({ ...formData, contrast_type: e.target.value })}
                      placeholder="e.g., IV, Oral, Rectal"
                      required={formData.contrast_required}
                    />
                  </div>
                )}
                <div className={styles.formGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.requires_sedation}
                      onChange={(e) =>
                        setFormData({ ...formData, requires_sedation: e.target.checked })
                      }
                    />
                    Requires Sedation
                  </label>
                </div>
                <div className={styles.formGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    />
                    Active (available for ordering)
                  </label>
                </div>
              </div>

              <div className={styles.formActions}>
                <button
                  className={styles.saveButton}
                  onClick={editingStudyType ? handleUpdate : handleCreate}
                  disabled={
                    isSaving ||
                    !formData.study_code.trim() ||
                    !formData.study_name.trim() ||
                    (formData.contrast_required && (!formData.contrast_type || !formData.contrast_type.trim()))
                  }
                >
                  {isSaving ? 'Saving...' : editingStudyType ? 'Update Study Type' : 'Create Study Type'}
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

        {/* Study Types List */}
        <div className={styles.studyTypesList}>
          <h2>Radiology Study Types Catalog ({studyTypes.length})</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : studyTypes.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No radiology study types found. Create your first study type to get started.</p>
            </div>
          ) : (
            <div className={styles.studyTypesGrid}>
              {studyTypes.map((studyType) => (
                <div key={studyType.id} className={styles.studyTypeCard}>
                  <div className={styles.studyTypeHeader}>
                    <div>
                      <h3>{studyType.study_name}</h3>
                      <span className={styles.studyCode}>{studyType.study_code}</span>
                    </div>
                    <span className={`${styles.statusBadge} ${studyType.is_active ? styles.active : styles.inactive}`}>
                      {studyType.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className={styles.studyTypeDetails}>
                    <p><strong>Category:</strong> {studyType.category.replace('_', ' ')}</p>
                    {studyType.body_part && (
                      <p><strong>Body Part:</strong> {studyType.body_part}</p>
                    )}
                    {studyType.description && (
                      <p className={styles.description}>{studyType.description}</p>
                    )}
                    {studyType.protocol && (
                      <div className={styles.protocol}>
                        <strong>Protocol:</strong> {studyType.protocol}
                      </div>
                    )}
                    {studyType.preparation_instructions && (
                      <div className={styles.preparation}>
                        <strong>Preparation:</strong> {studyType.preparation_instructions}
                      </div>
                    )}
                    {studyType.contrast_required && (
                      <span className={styles.contrastBadge}>
                        ⚠️ Contrast Required: {studyType.contrast_type}
                      </span>
                    )}
                    {studyType.requires_sedation && (
                      <span className={styles.sedationBadge}>💊 Requires Sedation</span>
                    )}
                    {studyType.estimated_duration_minutes && (
                      <p><strong>Duration:</strong> {studyType.estimated_duration_minutes} minutes</p>
                    )}
                    {studyType.radiation_dose && (
                      <p><strong>Radiation Dose:</strong> {studyType.radiation_dose}</p>
                    )}
                  </div>
                  <div className={styles.studyTypeActions}>
                    <button
                      className={styles.editButton}
                      onClick={() => handleEdit(studyType)}
                    >
                      Edit
                    </button>
                    <button
                      className={styles.deleteButton}
                      onClick={() => handleDelete(studyType.id)}
                    >
                      Delete
                    </button>
                  </div>
                  <div className={styles.studyTypeMeta}>
                    <p>Created by: {studyType.created_by_name || 'Unknown'}</p>
                    <p>Created: {new Date(studyType.created_at).toLocaleDateString()}</p>
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
