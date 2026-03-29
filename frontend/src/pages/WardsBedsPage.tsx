/**
 * Wards & beds inventory — admin (same access as Service Catalog).
 * Controls dropdown options for the Admit Patient modal (active wards/beds).
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchWards,
  fetchBeds,
  createWard,
  patchWard,
  deleteWard,
  createBed,
  patchBed,
  deleteBed,
  Ward,
  Bed,
} from '../api/admissions';
import { extractPaginatedResults } from '../utils/pagination';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/ServiceCatalog.module.css';

const BED_TYPES: Bed['bed_type'][] = [
  'STANDARD',
  'PRIVATE',
  'SEMI_PRIVATE',
  'ICU',
  'ISOLATION',
  'MATERNITY',
];

const defaultWardForm = () => ({
  name: '',
  code: '',
  description: '',
  capacity: 0,
  is_active: true,
});

const defaultBedForm = (wardId: number) => ({
  ward: wardId,
  bed_number: '',
  bed_type: 'STANDARD' as Bed['bed_type'],
  is_available: true,
  is_active: true,
  notes: '',
});

export default function WardsBedsPage() {
  const { showError, showSuccess } = useToast();
  const [wards, setWards] = useState<Ward[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingBeds, setLoadingBeds] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showInactiveWards, setShowInactiveWards] = useState(true);
  const [selectedWardId, setSelectedWardId] = useState<number | ''>('');

  const [wardModal, setWardModal] = useState(false);
  const [editingWardId, setEditingWardId] = useState<number | null>(null);
  const [wardForm, setWardForm] = useState(defaultWardForm);

  const [bedModal, setBedModal] = useState(false);
  const [editingBedId, setEditingBedId] = useState<number | null>(null);
  const [bedForm, setBedForm] = useState(defaultBedForm(0));

  const loadWards = useCallback(async () => {
    try {
      setLoading(true);
      const raw = await fetchWards(showInactiveWards ? undefined : true);
      const list = extractPaginatedResults<Ward>(raw);
      setWards(list);
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to load wards');
      setWards([]);
    } finally {
      setLoading(false);
    }
  }, [showError, showInactiveWards]);

  const loadBeds = useCallback(
    async (wardId: number) => {
      try {
        setLoadingBeds(true);
        const raw = await fetchBeds({ ward: wardId });
        setBeds(extractPaginatedResults<Bed>(raw));
      } catch (e) {
        showError(e instanceof Error ? e.message : 'Failed to load beds');
        setBeds([]);
      } finally {
        setLoadingBeds(false);
      }
    },
    [showError]
  );

  useEffect(() => {
    loadWards();
  }, [loadWards]);

  useEffect(() => {
    if (selectedWardId === '') return;
    if (!wards.some((w) => w.id === selectedWardId)) {
      setSelectedWardId('');
    }
  }, [wards, selectedWardId]);

  useEffect(() => {
    if (typeof selectedWardId === 'number' && selectedWardId > 0) {
      loadBeds(selectedWardId);
    } else {
      setBeds([]);
    }
  }, [selectedWardId, loadBeds]);

  const openNewWard = () => {
    setEditingWardId(null);
    setWardForm(defaultWardForm());
    setWardModal(true);
  };

  const openEditWard = (w: Ward) => {
    setEditingWardId(w.id);
    setWardForm({
      name: w.name,
      code: w.code,
      description: w.description || '',
      capacity: w.capacity,
      is_active: w.is_active,
    });
    setWardModal(true);
  };

  const saveWard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wardForm.name.trim() || !wardForm.code.trim()) {
      showError('Name and code are required.');
      return;
    }
    try {
      setSaving(true);
      if (editingWardId != null) {
        await patchWard(editingWardId, {
          name: wardForm.name.trim(),
          code: wardForm.code.trim(),
          description: wardForm.description.trim(),
          capacity: wardForm.capacity,
          is_active: wardForm.is_active,
        });
        showSuccess('Ward updated.');
      } else {
        await createWard({
          name: wardForm.name.trim(),
          code: wardForm.code.trim(),
          description: wardForm.description.trim(),
          capacity: wardForm.capacity,
          is_active: wardForm.is_active,
        });
        showSuccess('Ward created.');
      }
      setWardModal(false);
      await loadWards();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save ward');
    } finally {
      setSaving(false);
    }
  };

  const deactivateWard = async (w: Ward) => {
    if (!window.confirm(`Deactivate ward "${w.name}"? It will disappear from admission dropdowns until reactivated.`)) return;
    try {
      await patchWard(w.id, { is_active: false });
      showSuccess('Ward deactivated.');
      await loadWards();
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to update ward');
    }
  };

  const tryDeleteWard = async (w: Ward) => {
    if (!window.confirm(`Permanently delete ward "${w.name}"? Only possible if no linked admissions/beds block deletion.`)) return;
    try {
      await deleteWard(w.id);
      showSuccess('Ward deleted.');
      if (selectedWardId === w.id) setSelectedWardId('');
      await loadWards();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Delete failed';
      showError(msg);
    }
  };

  const openNewBed = () => {
    if (typeof selectedWardId !== 'number') {
      showError('Select a ward first (dropdown under Beds).');
      return;
    }
    setEditingBedId(null);
    setBedForm(defaultBedForm(selectedWardId));
    setBedModal(true);
  };

  const openEditBed = (b: Bed) => {
    setEditingBedId(b.id);
    setBedForm({
      ward: b.ward,
      bed_number: b.bed_number,
      bed_type: b.bed_type,
      is_available: b.is_available,
      is_active: b.is_active,
      notes: b.notes || '',
    });
    setBedModal(true);
  };

  const saveBed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bedForm.bed_number.trim()) {
      showError('Bed number is required.');
      return;
    }
    try {
      setSaving(true);
      if (editingBedId != null) {
        await patchBed(editingBedId, {
          bed_number: bedForm.bed_number.trim(),
          bed_type: bedForm.bed_type,
          is_available: bedForm.is_available,
          is_active: bedForm.is_active,
          notes: bedForm.notes.trim(),
        });
        showSuccess('Bed updated.');
      } else {
        await createBed({
          ward: bedForm.ward,
          bed_number: bedForm.bed_number.trim(),
          bed_type: bedForm.bed_type,
          is_available: bedForm.is_available,
          is_active: bedForm.is_active,
          notes: bedForm.notes.trim(),
        });
        showSuccess('Bed created.');
      }
      setBedModal(false);
      await loadBeds(bedForm.ward);
      await loadWards();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save bed');
    } finally {
      setSaving(false);
    }
  };

  const deactivateBed = async (b: Bed) => {
    if (!window.confirm(`Deactivate bed "${b.bed_number}"?`)) return;
    try {
      await patchBed(b.id, { is_active: false });
      showSuccess('Bed deactivated.');
      await loadBeds(b.ward);
      await loadWards();
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Failed to update bed');
    }
  };

  const tryDeleteBed = async (b: Bed) => {
    if (!window.confirm(`Permanently delete bed "${b.bed_number}"?`)) return;
    try {
      await deleteBed(b.id);
      showSuccess('Bed deleted.');
      await loadBeds(b.ward);
      await loadWards();
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Delete failed — try deactivating instead.');
    }
  };

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Wards & beds</h1>
        {!wardModal && (
          <div className={styles.headerActions}>
            <button type="button" className={styles.importButton} onClick={() => setShowInactiveWards((v) => !v)}>
              {showInactiveWards ? 'Hide inactive wards' : 'Show inactive wards'}
            </button>
            <button type="button" className={styles.createButton} onClick={openNewWard}>
              + Add ward
            </button>
          </div>
        )}
      </header>

      <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
        Active wards and beds appear in the Admit Patient form. Deactivating removes an item from those dropdowns without
        deleting history when deletion is blocked.
      </p>

      {wardModal && (
        <div className={styles.formContainer}>
          <h2>{editingWardId != null ? 'Edit ward' : 'Add ward'}</h2>
          <form onSubmit={saveWard}>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Name *</label>
                <input
                  value={wardForm.name}
                  onChange={(e) => setWardForm({ ...wardForm, name: e.target.value })}
                  placeholder="e.g. General Ward"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Code *</label>
                <input
                  value={wardForm.code}
                  onChange={(e) => setWardForm({ ...wardForm, code: e.target.value })}
                  placeholder="e.g. GW"
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Description</label>
              <input
                value={wardForm.description}
                onChange={(e) => setWardForm({ ...wardForm, description: e.target.value })}
              />
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Capacity (bed count)</label>
                <input
                  type="number"
                  min={0}
                  value={wardForm.capacity}
                  onChange={(e) => setWardForm({ ...wardForm, capacity: parseInt(e.target.value, 10) || 0 })}
                />
              </div>
              <div className={styles.formGroup}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={wardForm.is_active}
                    onChange={(e) => setWardForm({ ...wardForm, is_active: e.target.checked })}
                  />
                  Active (shown in admission dropdowns)
                </label>
              </div>
            </div>
            <div className={styles.formActions}>
              <button type="submit" className={styles.saveButton} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button type="button" className={styles.cancelButton} onClick={() => setWardModal(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {!wardModal && (
        <>
          {loading ? (
            <LoadingSkeleton count={4} />
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Capacity</th>
                    <th>Available / Occupied</th>
                    <th>Active</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {wards.map((w) => (
                    <tr key={w.id}>
                      <td>{w.code}</td>
                      <td>{w.name}</td>
                      <td>{w.capacity}</td>
                      <td>
                        {w.available_beds_count} / {w.occupied_beds_count}
                      </td>
                      <td>
                        <span className={w.is_active ? styles.badgeActive : styles.badgeInactive}>
                          {w.is_active ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <div className={styles.cellActions}>
                          <button type="button" className={styles.editBtn} onClick={() => openEditWard(w)}>
                            Edit
                          </button>
                          {w.is_active && (
                            <button type="button" className={styles.deleteBtn} onClick={() => deactivateWard(w)}>
                              Deactivate
                            </button>
                          )}
                          <button type="button" className={styles.deleteBtn} onClick={() => tryDeleteWard(w)}>
                            Delete
                          </button>
                          <button
                            type="button"
                            className={styles.editBtn}
                            onClick={() => setSelectedWardId(w.id)}
                          >
                            Beds
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2 style={{ marginTop: '2rem', color: 'var(--text-primary)' }}>Beds</h2>
          <div className={styles.filterBar} style={{ marginBottom: '1rem' }}>
            <label>
              Ward:&nbsp;
              <select
                value={selectedWardId === '' ? '' : String(selectedWardId)}
                onChange={(e) => {
                  const v = e.target.value;
                  setSelectedWardId(v === '' ? '' : parseInt(v, 10));
                }}
              >
                <option value="">Select ward…</option>
                {wards.filter((w) => w.is_active).map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} — {w.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className={styles.createButton}
              onClick={openNewBed}
              disabled={typeof selectedWardId !== 'number'}
            >
              + Add bed
            </button>
          </div>

          {typeof selectedWardId === 'number' ? (
            loadingBeds ? (
              <LoadingSkeleton count={3} />
            ) : beds.length === 0 ? (
              <p className={styles.emptyMessage}>No beds for this ward yet. Add a bed above.</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Bed #</th>
                      <th>Type</th>
                      <th>Available</th>
                      <th>Active</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {beds.map((b) => (
                      <tr key={b.id}>
                        <td>{b.bed_number}</td>
                        <td>{b.bed_type}</td>
                        <td>{b.is_available ? 'Yes' : 'No'}</td>
                        <td>
                          <span className={b.is_active ? styles.badgeActive : styles.badgeInactive}>
                            {b.is_active ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td>
                          <div className={styles.cellActions}>
                            <button type="button" className={styles.editBtn} onClick={() => openEditBed(b)}>
                              Edit
                            </button>
                            {b.is_active && (
                              <button type="button" className={styles.deleteBtn} onClick={() => deactivateBed(b)}>
                                Deactivate
                              </button>
                            )}
                            <button type="button" className={styles.deleteBtn} onClick={() => tryDeleteBed(b)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            <p className={styles.emptyMessage}>Select a ward to list and manage beds.</p>
          )}
        </>
      )}

      {bedModal && (
        <div className={styles.modalOverlay} onClick={() => setBedModal(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <h2>{editingBedId != null ? 'Edit bed' : 'Add bed'}</h2>
            <form onSubmit={saveBed}>
              <div className={styles.formGroup}>
                <label>Bed number *</label>
                <input
                  value={bedForm.bed_number}
                  onChange={(e) => setBedForm({ ...bedForm, bed_number: e.target.value })}
                  placeholder="e.g. A1"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Type</label>
                <select
                  value={bedForm.bed_type}
                  onChange={(e) => setBedForm({ ...bedForm, bed_type: e.target.value as Bed['bed_type'] })}
                >
                  {BED_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.formRow}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={bedForm.is_available}
                    onChange={(e) => setBedForm({ ...bedForm, is_available: e.target.checked })}
                  />
                  Available for assignment
                </label>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={bedForm.is_active}
                    onChange={(e) => setBedForm({ ...bedForm, is_active: e.target.checked })}
                  />
                  Active
                </label>
              </div>
              <div className={styles.formGroup}>
                <label>Notes</label>
                <input
                  value={bedForm.notes}
                  onChange={(e) => setBedForm({ ...bedForm, notes: e.target.value })}
                />
              </div>
              <div className={styles.formActions}>
                <button type="submit" className={styles.saveButton} disabled={saving}>
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button type="button" className={styles.cancelButton} onClick={() => setBedModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
