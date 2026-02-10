/**
 * Service Catalog Management Page
 *
 * Admin-only: add, edit, and manage billable services (e.g. Telemedicine Consultation TELEMED-001).
 */
import React, { useState, useEffect } from 'react';
import {
  fetchServiceCatalog,
  createServiceCatalog,
  updateServiceCatalog,
  deleteServiceCatalog,
  fetchServiceCatalogChoices,
} from '../api/serviceCatalog';
import type {
  ServiceCatalogItem,
  ServiceCatalogCreate,
  ServiceCatalogChoices,
} from '../types/serviceCatalog';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/ServiceCatalog.module.css';

const defaultForm: ServiceCatalogCreate = {
  service_code: '',
  name: '',
  department: 'CONSULTATION',
  workflow_type: 'OTHER',
  amount: '',
  description: '',
  is_active: true,
};

export default function ServiceCatalogPage() {
  const { showError, showSuccess } = useToast();
  const [services, setServices] = useState<ServiceCatalogItem[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [choices, setChoices] = useState<ServiceCatalogChoices | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ServiceCatalogCreate>(defaultForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const loadChoices = async () => {
    try {
      const c = await fetchServiceCatalogChoices();
      setChoices(c);
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to load choices');
    }
  };

  const loadServices = async () => {
    try {
      setLoading(true);
      const res = await fetchServiceCatalog({
        page,
        page_size: 50,
        active_only: false,
        department: departmentFilter || undefined,
        search: searchQuery || undefined,
      });
      setServices(res.results);
      setTotalPages(res.total_pages);
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to load services');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChoices();
  }, []);

  useEffect(() => {
    loadServices();
  }, [page, departmentFilter, searchQuery]);

  const openAdd = () => {
    setEditingId(null);
    setForm(defaultForm);
    setFormError(null);
    setShowForm(true);
  };

  const openEdit = (item: ServiceCatalogItem) => {
    setEditingId(item.id);
    setForm({
      service_code: item.service_code,
      name: item.name,
      department: item.department,
      workflow_type: item.workflow_type,
      amount: item.amount,
      description: item.description || '',
      is_active: item.is_active,
    });
    setFormError(null);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(defaultForm);
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!form.service_code.trim()) {
      setFormError('Service code is required.');
      return;
    }
    if (!form.name.trim()) {
      setFormError('Name is required.');
      return;
    }
    const amountNum = parseFloat(form.amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setFormError('Amount must be greater than zero.');
      return;
    }
    try {
      setSaving(true);
      if (editingId != null) {
        await updateServiceCatalog(editingId, form);
        showSuccess('Service updated successfully.');
      } else {
        await createServiceCatalog(form);
        showSuccess('Service added successfully.');
      }
      closeForm();
      loadServices();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save service.';
      setFormError(msg);
      showError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, code: string) => {
    if (!window.confirm(`Delete service "${code}"? This cannot be undone.`)) return;
    try {
      await deleteServiceCatalog(id);
      showSuccess('Service deleted.');
      loadServices();
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to delete service');
    }
  };

  const formatAmount = (s: string) => {
    const n = parseFloat(s);
    if (isNaN(n)) return s;
    return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  };

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Service Catalog</h1>
        {!showForm && (
          <button type="button" className={styles.createButton} onClick={openAdd}>
            + Add Service
          </button>
        )}
      </header>

      {showForm && (
        <div className={styles.formContainer}>
          <h2>{editingId != null ? 'Edit Service' : 'Add Service'}</h2>
          <form onSubmit={handleSubmit}>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Service code *</label>
                <input
                  type="text"
                  value={form.service_code}
                  onChange={(e) => setForm({ ...form, service_code: e.target.value })}
                  placeholder="e.g. TELEMED-001"
                  maxLength={100}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Telemedicine Consultation"
                />
              </div>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Department *</label>
                <select
                  value={form.department}
                  onChange={(e) =>
                    setForm({ ...form, department: e.target.value as ServiceCatalogCreate['department'] })
                  }
                >
                  {choices?.departments.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                  {!choices?.departments?.length && (
                    <>
                      <option value="CONSULTATION">Consultation</option>
                      <option value="LAB">Laboratory</option>
                      <option value="PHARMACY">Pharmacy</option>
                      <option value="RADIOLOGY">Radiology</option>
                      <option value="PROCEDURE">Procedure</option>
                    </>
                  )}
                </select>
              </div>
              <div className={styles.formGroup}>
                <label>Workflow type *</label>
                <select
                  value={form.workflow_type}
                  onChange={(e) =>
                    setForm({ ...form, workflow_type: e.target.value as ServiceCatalogCreate['workflow_type'] })
                  }
                >
                  {choices?.workflow_types.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                  {!choices?.workflow_types?.length && (
                    <>
                      <option value="OTHER">Other</option>
                      <option value="GOPD_CONSULT">GOPD Consultation</option>
                      <option value="IVF">IVF</option>
                      <option value="LAB_ORDER">Laboratory Order</option>
                      <option value="DRUG_DISPENSE">Drug Dispensing</option>
                      <option value="PROCEDURE">Procedure</option>
                      <option value="RADIOLOGY_STUDY">Radiology Study</option>
                    </>
                  )}
                </select>
              </div>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Amount (fee) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Active</label>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={form.is_active !== false}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  Yes (service available for billing)
                </label>
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Description (optional)</label>
              <input
                type="text"
                value={form.description || ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Brief description"
              />
            </div>
            {formError && <p className={styles.errorText}>{formError}</p>}
            <div className={styles.formActions}>
              <button type="submit" className={styles.saveButton} disabled={saving}>
                {saving ? 'Saving...' : editingId != null ? 'Update' : 'Add Service'}
              </button>
              <button type="button" className={styles.cancelButton} onClick={closeForm}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className={styles.filterBar}>
        <input
          type="text"
          placeholder="Search by code or name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
        >
          <option value="">All departments</option>
          {choices?.departments.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <LoadingSkeleton count={5} />
      ) : services.length === 0 ? (
        <p className={styles.emptyMessage}>
          No services found. Add a service (e.g. Telemedicine Consultation with code TELEMED-001) to use it in billing.
        </p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Department</th>
                <th>Workflow</th>
                <th>Amount</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {services.map((s) => (
                <tr key={s.id}>
                  <td>{s.service_code}</td>
                  <td>{s.name}</td>
                  <td>{choices?.departments?.find((d) => d.value === s.department)?.label ?? s.department}</td>
                  <td>{choices?.workflow_types?.find((w) => w.value === s.workflow_type)?.label ?? s.workflow_type}</td>
                  <td>{formatAmount(s.amount)}</td>
                  <td>
                    <span className={s.is_active ? styles.badgeActive : styles.badgeInactive}>
                      {s.is_active ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td>
                    <div className={styles.cellActions}>
                      <button type="button" className={styles.editBtn} onClick={() => openEdit(s)}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className={styles.deleteBtn}
                        onClick={() => handleDelete(s.id, s.service_code)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
