/**
 * Lab Test Catalog Management Page
 * 
 * For Doctors and Lab Techs to create and manage lab tests in the catalog.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchLabTestCatalog,
  fetchActiveLabTests,
  getLabTestCategories,
  createLabTestCatalog,
  updateLabTestCatalog,
  deleteLabTestCatalog,
  LabTestCatalogFilters,
} from '../api/labCatalog';
import {
  LabTestCatalog,
  LabTestCatalogCreate,
  LabTestCatalogUpdate,
  LabTestCategory,
} from '../types/labCatalog';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/LabTestCatalog.module.css';

export default function LabTestCatalogPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  
  const [tests, setTests] = useState<LabTestCatalog[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTest, setEditingTest] = useState<LabTestCatalog | null>(null);
  
  // Filters
  const [filters, setFilters] = useState<LabTestCatalogFilters>({
    is_active: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form state
  const [formData, setFormData] = useState<LabTestCatalogCreate>({
    test_code: '',
    test_name: '',
    category: 'OTHER',
    description: '',
    reference_range_min: null,
    reference_range_max: null,
    reference_range_text: '',
    unit: '',
    is_active: true,
    requires_fasting: false,
    turnaround_time_hours: null,
    specimen_type: '',
  });

  useEffect(() => {
    loadTests();
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

  const loadTests = async () => {
    try {
      setLoading(true);
      const data = await fetchLabTestCatalog(filters);
      setTests(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading lab tests:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load lab tests';
      showError(errorMessage);
      setTests([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const cats = await getLabTestCategories();
      setCategories(cats);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const handleCreate = async () => {
    if (!formData.test_code.trim() || !formData.test_name.trim()) {
      showError('Test code and name are required');
      return;
    }

    try {
      setIsSaving(true);
      await createLabTestCatalog(formData);
      showSuccess('Lab test created successfully');
      resetForm();
      setShowCreateForm(false);
      await loadTests();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create lab test';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingTest) return;
    if (!formData.test_code.trim() || !formData.test_name.trim()) {
      showError('Test code and name are required');
      return;
    }

    try {
      setIsSaving(true);
      await updateLabTestCatalog(editingTest.id, formData as LabTestCatalogUpdate);
      showSuccess('Lab test updated successfully');
      resetForm();
      setEditingTest(null);
      setShowCreateForm(false);
      await loadTests();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update lab test';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (testId: number) => {
    if (!window.confirm('Are you sure you want to delete this lab test?')) {
      return;
    }

    try {
      await deleteLabTestCatalog(testId);
      showSuccess('Lab test deleted successfully');
      await loadTests();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete lab test';
      showError(errorMessage);
    }
  };

  const handleEdit = (test: LabTestCatalog) => {
    setEditingTest(test);
    setFormData({
      test_code: test.test_code,
      test_name: test.test_name,
      category: test.category,
      description: test.description || '',
      reference_range_min: test.reference_range_min,
      reference_range_max: test.reference_range_max,
      reference_range_text: test.reference_range_text || '',
      unit: test.unit || '',
      is_active: test.is_active,
      requires_fasting: test.requires_fasting,
      turnaround_time_hours: test.turnaround_time_hours,
      specimen_type: test.specimen_type || '',
    });
    setShowCreateForm(true);
  };

  const resetForm = () => {
    setFormData({
      test_code: '',
      test_name: '',
      category: 'OTHER',
      description: '',
      reference_range_min: null,
      reference_range_max: null,
      reference_range_text: '',
      unit: '',
      is_active: true,
      requires_fasting: false,
      turnaround_time_hours: null,
      specimen_type: '',
    });
    setEditingTest(null);
  };

  const handleCancel = () => {
    resetForm();
    setShowCreateForm(false);
  };

  const canManage = user?.role === 'DOCTOR' || user?.role === 'LAB_TECH';

  if (!canManage) {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Doctors and Lab Technicians only.</p>
      </div>
    );
  }

  return (
    <div className={styles.catalogPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Lab Test Catalog</h1>
        <p>Create and manage available lab tests and reference ranges</p>
      </header>

      <div className={styles.content}>
        <div className={styles.filters}>
          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by code, name, or description..."
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
                    category: e.target.value ? (e.target.value as LabTestCategory) : undefined,
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
              + Add New Lab Test
            </button>
          )}
        </div>

        {/* Create/Edit Form */}
        {showCreateForm && (
          <div className={styles.formContainer}>
            <h2>{editingTest ? 'Edit Lab Test' : 'Create New Lab Test'}</h2>
            <div className={styles.form}>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Test Code *</label>
                  <input
                    type="text"
                    value={formData.test_code}
                    onChange={(e) => setFormData({ ...formData, test_code: e.target.value.toUpperCase() })}
                    placeholder="e.g., CBC, HGB, GLU"
                    required
                    disabled={!!editingTest}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Test Name *</label>
                  <input
                    type="text"
                    value={formData.test_name}
                    onChange={(e) => setFormData({ ...formData, test_name: e.target.value })}
                    placeholder="e.g., Complete Blood Count"
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
                      setFormData({ ...formData, category: e.target.value as LabTestCategory })
                    }
                    required
                  >
                    <option value="HEMATOLOGY">Hematology</option>
                    <option value="CHEMISTRY">Chemistry</option>
                    <option value="MICROBIOLOGY">Microbiology</option>
                    <option value="IMMUNOLOGY">Immunology</option>
                    <option value="SEROLOGY">Serology</option>
                    <option value="ENDOCRINOLOGY">Endocrinology</option>
                    <option value="TOXICOLOGY">Toxicology</option>
                    <option value="URINALYSIS">Urinalysis</option>
                    <option value="BLOOD_BANK">Blood Bank</option>
                    <option value="MOLECULAR">Molecular</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label>Specimen Type</label>
                  <input
                    type="text"
                    value={formData.specimen_type}
                    onChange={(e) => setFormData({ ...formData, specimen_type: e.target.value })}
                    placeholder="e.g., Blood, Urine, Stool"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description of what the test measures"
                  rows={3}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Reference Range (Min)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.reference_range_min || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        reference_range_min: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="Minimum value"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Reference Range (Max)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.reference_range_max || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        reference_range_max: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="Maximum value"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Unit</label>
                  <input
                    type="text"
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    placeholder="e.g., g/dL, mg/dL, cells/μL"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Reference Range (Text)</label>
                <input
                  type="text"
                  value={formData.reference_range_text}
                  onChange={(e) => setFormData({ ...formData, reference_range_text: e.target.value })}
                  placeholder="e.g., Negative, Positive, Normal (for non-numeric tests)"
                />
                <small>Use this for non-numeric tests or when numeric ranges don't apply</small>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Turnaround Time (hours)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.turnaround_time_hours || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        turnaround_time_hours: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    placeholder="Expected hours"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.requires_fasting}
                      onChange={(e) =>
                        setFormData({ ...formData, requires_fasting: e.target.checked })
                      }
                    />
                    Requires Fasting
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
                  onClick={editingTest ? handleUpdate : handleCreate}
                  disabled={isSaving || !formData.test_code.trim() || !formData.test_name.trim()}
                >
                  {isSaving ? 'Saving...' : editingTest ? 'Update Test' : 'Create Test'}
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

        {/* Tests List */}
        <div className={styles.testsList}>
          <h2>Lab Test Catalog ({tests.length})</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : tests.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No lab tests found. Create your first test to get started.</p>
            </div>
          ) : (
            <div className={styles.testsGrid}>
              {tests.map((test) => (
                <div key={test.id} className={styles.testCard}>
                  <div className={styles.testHeader}>
                    <div>
                      <h3>{test.test_name}</h3>
                      <span className={styles.testCode}>{test.test_code}</span>
                    </div>
                    <span className={`${styles.statusBadge} ${test.is_active ? styles.active : styles.inactive}`}>
                      {test.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className={styles.testDetails}>
                    <p><strong>Category:</strong> {test.category.replace('_', ' ')}</p>
                    {test.description && <p className={styles.description}>{test.description}</p>}
                    <div className={styles.referenceRange}>
                      <strong>Reference Range:</strong>{' '}
                      {test.reference_range_display || 'Not specified'}
                    </div>
                    {test.specimen_type && (
                      <p><strong>Specimen:</strong> {test.specimen_type}</p>
                    )}
                    {test.requires_fasting && (
                      <span className={styles.fastingBadge}>⚠️ Requires Fasting</span>
                    )}
                    {test.turnaround_time_hours && (
                      <p><strong>Turnaround:</strong> {test.turnaround_time_hours} hours</p>
                    )}
                  </div>
                  <div className={styles.testActions}>
                    <button
                      className={styles.editButton}
                      onClick={() => handleEdit(test)}
                    >
                      Edit
                    </button>
                    <button
                      className={styles.deleteButton}
                      onClick={() => handleDelete(test.id)}
                    >
                      Delete
                    </button>
                  </div>
                  <div className={styles.testMeta}>
                    <p>Created by: {test.created_by_name || 'Unknown'}</p>
                    <p>Created: {new Date(test.created_at).toLocaleDateString()}</p>
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
