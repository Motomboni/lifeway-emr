/**
 * Drug Catalog & Inventory - Unified page for pharmacists.
 *
 * Merges Drug Catalog and Inventory Management into a single view.
 * Each drug shows catalog info + stock levels in one place.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchDrugs,
  createDrug,
  updateDrug,
  deleteDrug,
  DrugCreateData,
  DrugUpdateData,
  PaginatedDrugResponse,
} from '../api/drug';
import {
  fetchInventory,
  fetchLowStockInventory,
  fetchOutOfStockInventory,
  createInventory,
  updateInventory,
  deleteInventory,
  restockInventory,
  adjustInventory,
  fetchStockMovements,
  DrugInventory,
  DrugInventoryCreateData,
  DrugInventoryUpdateData,
  StockMovement,
  RestockData,
  AdjustData,
  PaginatedInventoryResponse,
  PaginatedMovementResponse,
} from '../api/inventory';
import { Drug } from '../types/drug';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/DrugCatalogInventory.module.css';

type ViewMode = 'all' | 'low_stock' | 'out_of_stock';

export default function DrugCatalogInventoryPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();

  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [inventoryList, setInventoryList] = useState<DrugInventory[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('all');

  // Drug form
  const [showDrugForm, setShowDrugForm] = useState(false);
  const [editingDrug, setEditingDrug] = useState<Drug | null>(null);
  const [drugFormData, setDrugFormData] = useState<DrugCreateData>({
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

  // Inventory form
  const [showInventoryForm, setShowInventoryForm] = useState(false);
  const [editingInventory, setEditingInventory] = useState<DrugInventory | null>(null);
  const [inventoryFormData, setInventoryFormData] = useState<DrugInventoryCreateData>({
    drug: 0,
    current_stock: 0,
    unit: 'units',
    reorder_level: 0,
    batch_number: '',
    expiry_date: '',
    location: '',
  });

  // Modals
  const [selectedInventory, setSelectedInventory] = useState<DrugInventory | null>(null);
  const [showMovements, setShowMovements] = useState(false);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [loadingMovements, setLoadingMovements] = useState(false);
  const [restockData, setRestockData] = useState<RestockData>({ quantity: 0, reference_number: '', notes: '' });
  const [adjustData, setAdjustData] = useState<AdjustData>({ quantity: 0, reason: '', notes: '' });

  const loadDrugs = useCallback(async () => {
    try {
      const response = await fetchDrugs();
      const drugsArray = Array.isArray(response)
        ? response
        : (response as PaginatedDrugResponse)?.results || [];
      setDrugs(drugsArray);
    } catch (error) {
      console.error('Error loading drugs:', error);
      showError(error instanceof Error ? error.message : 'Failed to load drugs');
      setDrugs([]);
    }
  }, [showError]);

  const loadInventory = useCallback(async () => {
    try {
      let response;
      if (viewMode === 'low_stock') {
        response = await fetchLowStockInventory();
      } else if (viewMode === 'out_of_stock') {
        response = await fetchOutOfStockInventory();
      } else {
        response = await fetchInventory(searchQuery ? { search: searchQuery } : {});
      }
      const arr = Array.isArray(response)
        ? response
        : (response as PaginatedInventoryResponse)?.results || [];
      setInventoryList(arr);
    } catch (error) {
      console.error('Error loading inventory:', error);
      showError(error instanceof Error ? error.message : 'Failed to load inventory');
      setInventoryList([]);
    }
  }, [viewMode, searchQuery, showError]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([loadDrugs(), loadInventory()]).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [loadDrugs, loadInventory]);

  const inventoryByDrugId = React.useMemo(() => {
    const map: Record<number, DrugInventory> = {};
    inventoryList.forEach((inv) => {
      map[inv.drug] = inv;
    });
    return map;
  }, [inventoryList]);

  const displayedDrugs = React.useMemo(() => {
    if (viewMode === 'all') {
      return drugs.filter((d) => {
        if (!d.is_active && !inventoryByDrugId[d.id]) return false;
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
          d.name.toLowerCase().includes(q) ||
          (d.drug_code || '').toLowerCase().includes(q) ||
          (d.generic_name || '').toLowerCase().includes(q)
        );
      });
    }
    if (viewMode === 'low_stock' || viewMode === 'out_of_stock') {
      const drugIds = new Set(inventoryList.map((i) => i.drug));
      return drugs.filter((d) => drugIds.has(d.id));
    }
    return drugs;
  }, [drugs, inventoryList, viewMode, searchQuery, inventoryByDrugId]);

  const loadMovements = async (inventoryId: number) => {
    try {
      setLoadingMovements(true);
      const response = await fetchStockMovements({ inventory: inventoryId });
      setMovements(
        Array.isArray(response)
          ? response
          : (response as PaginatedMovementResponse)?.results || []
      );
    } catch (error) {
      console.error('Error loading movements:', error);
      showError('Failed to load stock movements');
    } finally {
      setLoadingMovements(false);
    }
  };

  const handleCreateDrug = async () => {
    if (!drugFormData.name.trim()) {
      showError('Drug name is required');
      return;
    }
    try {
      setIsSaving(true);
      await createDrug(drugFormData);
      showSuccess('Drug created successfully');
      resetDrugForm();
      setShowDrugForm(false);
      await loadDrugs();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to create drug');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateDrug = async () => {
    if (!editingDrug) return;
    if (!drugFormData.name.trim()) {
      showError('Drug name is required');
      return;
    }
    try {
      setIsSaving(true);
      await updateDrug(editingDrug.id, drugFormData as DrugUpdateData);
      showSuccess('Drug updated successfully');
      resetDrugForm();
      setEditingDrug(null);
      setShowDrugForm(false);
      await loadDrugs();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to update drug');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDrug = async (drugId: number) => {
    if (!window.confirm('Are you sure you want to deactivate this drug?')) return;
    try {
      await deleteDrug(drugId);
      showSuccess('Drug deactivated successfully');
      await loadDrugs();
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to deactivate drug');
    }
  };

  const handleCreateInventory = async () => {
    if (!inventoryFormData.drug || inventoryFormData.current_stock < 0 || inventoryFormData.reorder_level < 0) {
      showError('Please fill in all required fields with valid values');
      return;
    }
    try {
      setIsSaving(true);
      await createInventory(inventoryFormData);
      showSuccess('Inventory record created successfully');
      resetInventoryForm();
      setShowInventoryForm(false);
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to create inventory');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateInventory = async () => {
    if (!editingInventory) return;
    try {
      setIsSaving(true);
      await updateInventory(editingInventory.id, inventoryFormData as DrugInventoryUpdateData);
      showSuccess('Inventory updated successfully');
      resetInventoryForm();
      setEditingInventory(null);
      setShowInventoryForm(false);
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to update inventory');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteInventory = async (inventoryId: number) => {
    if (!window.confirm('Are you sure you want to delete this inventory record?')) return;
    try {
      await deleteInventory(inventoryId);
      showSuccess('Inventory deleted successfully');
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to delete inventory');
    }
  };

  const handleRestock = async () => {
    if (!selectedInventory || restockData.quantity <= 0) {
      showError('Please enter a valid quantity');
      return;
    }
    try {
      setIsSaving(true);
      await restockInventory(selectedInventory.id, restockData);
      showSuccess('Inventory restocked successfully');
      setShowRestockModal(false);
      setSelectedInventory(null);
      setRestockData({ quantity: 0, reference_number: '', notes: '' });
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to restock');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAdjust = async () => {
    if (!selectedInventory || adjustData.quantity === 0) {
      showError('Please enter a valid adjustment quantity');
      return;
    }
    try {
      setIsSaving(true);
      await adjustInventory(selectedInventory.id, adjustData);
      showSuccess('Inventory adjusted successfully');
      setShowAdjustModal(false);
      setSelectedInventory(null);
      setAdjustData({ quantity: 0, reason: '', notes: '' });
      await loadInventory();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to adjust');
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditDrug = (drug: Drug) => {
    setEditingDrug(drug);
    setDrugFormData({
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
    setShowDrugForm(true);
  };

  const handleEditInventory = (inv: DrugInventory) => {
    setEditingInventory(inv);
    setInventoryFormData({
      drug: inv.drug,
      current_stock: inv.current_stock,
      unit: inv.unit,
      reorder_level: inv.reorder_level,
      batch_number: inv.batch_number || '',
      expiry_date: inv.expiry_date ? inv.expiry_date.split('T')[0] : '',
      location: inv.location || '',
    });
    setShowInventoryForm(true);
  };

  const handleAddInventory = (drug: Drug) => {
    setEditingInventory(null);
    setInventoryFormData({
      drug: drug.id,
      current_stock: 0,
      unit: 'units',
      reorder_level: 0,
      batch_number: '',
      expiry_date: '',
      location: '',
    });
    setShowInventoryForm(true);
  };

  const resetDrugForm = () => {
    setDrugFormData({
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

  const resetInventoryForm = () => {
    setInventoryFormData({
      drug: 0,
      current_stock: 0,
      unit: 'units',
      reorder_level: 0,
      batch_number: '',
      expiry_date: '',
      location: '',
    });
    setEditingInventory(null);
  };

  const formatDateTime = (s: string) =>
    new Date(s).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  const formatDate = (s: string) =>
    new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

  const getMovementBadgeClass = (type: string) => {
    switch (type) {
      case 'IN':
      case 'RETURNED':
        return styles.movementIn;
      case 'OUT':
      case 'DISPENSED':
      case 'EXPIRED':
      case 'DAMAGED':
        return styles.movementOut;
      case 'ADJUSTMENT':
        return styles.movementAdjustment;
      default:
        return '';
    }
  };

  if (user?.role !== 'PHARMACIST') {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <div className={styles.accessDenied}>
          <h2>Access Denied</h2>
          <p>This page is for Pharmacists only.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Drug Catalog & Inventory</h1>
        <p>Manage drugs and stock levels in one place</p>
        <div className={styles.headerActions}>
          {!showDrugForm && !showInventoryForm && (
            <>
              <button className={styles.addDrugButton} onClick={() => { resetDrugForm(); setShowDrugForm(true); }}>
                + Add Drug
              </button>
            </>
          )}
        </div>
      </header>

      {/* Filters */}
      {!showDrugForm && !showInventoryForm && (
        <div className={styles.filters}>
          <div className={styles.viewModeButtons}>
            <button
              className={viewMode === 'all' ? styles.activeBtn : styles.inactiveBtn}
              onClick={() => setViewMode('all')}
            >
              All
            </button>
            <button
              className={viewMode === 'low_stock' ? styles.activeBtn : styles.inactiveBtn}
              onClick={() => setViewMode('low_stock')}
            >
              Low Stock
            </button>
            <button
              className={viewMode === 'out_of_stock' ? styles.activeBtn : styles.inactiveBtn}
              onClick={() => setViewMode('out_of_stock')}
            >
              Out of Stock
            </button>
          </div>
          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by drug name, code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadInventory()}
            />
            <button onClick={loadInventory}>Search</button>
          </div>
        </div>
      )}

      {/* Drug form */}
      {showDrugForm && (
        <div className={styles.formCard}>
          <h2>{editingDrug ? 'Edit Drug' : 'Create New Drug'}</h2>
          <div className={styles.form}>
            <div className={styles.formGroup}>
              <label>Drug Name *</label>
              <input
                type="text"
                value={drugFormData.name}
                onChange={(e) => setDrugFormData({ ...drugFormData, name: e.target.value })}
                placeholder="e.g., Paracetamol"
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label>Generic Name</label>
              <input
                type="text"
                value={drugFormData.generic_name}
                onChange={(e) => setDrugFormData({ ...drugFormData, generic_name: e.target.value })}
                placeholder="e.g., Acetaminophen"
              />
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Drug Code</label>
                <input
                  type="text"
                  value={drugFormData.drug_code}
                  onChange={(e) => setDrugFormData({ ...drugFormData, drug_code: e.target.value })}
                  placeholder="e.g., NDC code"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Drug Class</label>
                <input
                  type="text"
                  value={drugFormData.drug_class}
                  onChange={(e) => setDrugFormData({ ...drugFormData, drug_class: e.target.value })}
                  placeholder="e.g., Antibiotic"
                />
              </div>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Dosage Forms</label>
                <input
                  type="text"
                  value={drugFormData.dosage_forms}
                  onChange={(e) => setDrugFormData({ ...drugFormData, dosage_forms: e.target.value })}
                  placeholder="Tablet, Capsule, Syrup"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Common Dosages</label>
                <input
                  type="text"
                  value={drugFormData.common_dosages}
                  onChange={(e) => setDrugFormData({ ...drugFormData, common_dosages: e.target.value })}
                  placeholder="250mg, 500mg"
                />
              </div>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Cost Price (₦)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={drugFormData.cost_price ?? ''}
                  onChange={(e) =>
                    setDrugFormData({
                      ...drugFormData,
                      cost_price: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                  placeholder="0.00"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Sales Price (₦)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={drugFormData.sales_price ?? ''}
                  onChange={(e) =>
                    setDrugFormData({
                      ...drugFormData,
                      sales_price: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                  placeholder="0.00"
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Description</label>
              <textarea
                value={drugFormData.description}
                onChange={(e) => setDrugFormData({ ...drugFormData, description: e.target.value })}
                placeholder="Description, indications..."
                rows={3}
              />
            </div>
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={drugFormData.is_active}
                  onChange={(e) => setDrugFormData({ ...drugFormData, is_active: e.target.checked })}
                />
                Active
              </label>
            </div>
            <div className={styles.formActions}>
              <button
                className={styles.saveBtn}
                onClick={editingDrug ? handleUpdateDrug : handleCreateDrug}
                disabled={isSaving || !drugFormData.name.trim()}
              >
                {isSaving ? 'Saving...' : editingDrug ? 'Update' : 'Create'}
              </button>
              <button className={styles.cancelBtn} onClick={() => { resetDrugForm(); setShowDrugForm(false); }} disabled={isSaving}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inventory form */}
      {showInventoryForm && (
        <div className={styles.formCard}>
          <h2>{editingInventory ? 'Edit Inventory' : 'Add Inventory Record'}</h2>
          <div className={styles.form}>
            <div className={styles.formGroup}>
              <label>Drug *</label>
              <select
                value={inventoryFormData.drug}
                onChange={(e) => setInventoryFormData({ ...inventoryFormData, drug: parseInt(e.target.value) })}
                disabled={!!editingInventory}
              >
                <option value={0}>Select drug...</option>
                {drugs.filter((d) => d.is_active).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} {d.drug_code ? `(${d.drug_code})` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Current Stock *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={inventoryFormData.current_stock}
                  onChange={(e) =>
                    setInventoryFormData({
                      ...inventoryFormData,
                      current_stock: parseFloat(e.target.value) || 0,
                    })
                  }
                />
              </div>
              <div className={styles.formGroup}>
                <label>Unit *</label>
                <input
                  type="text"
                  value={inventoryFormData.unit}
                  onChange={(e) => setInventoryFormData({ ...inventoryFormData, unit: e.target.value })}
                  placeholder="tablets, bottles..."
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Reorder Level *</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={inventoryFormData.reorder_level}
                onChange={(e) =>
                  setInventoryFormData({
                    ...inventoryFormData,
                    reorder_level: parseFloat(e.target.value) || 0,
                  })
                }
              />
              <small>Alert when stock falls below this</small>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Batch Number</label>
                <input
                  type="text"
                  value={inventoryFormData.batch_number}
                  onChange={(e) => setInventoryFormData({ ...inventoryFormData, batch_number: e.target.value })}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Expiry Date</label>
                <input
                  type="date"
                  value={inventoryFormData.expiry_date}
                  onChange={(e) => setInventoryFormData({ ...inventoryFormData, expiry_date: e.target.value })}
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Location</label>
              <input
                type="text"
                value={inventoryFormData.location}
                onChange={(e) => setInventoryFormData({ ...inventoryFormData, location: e.target.value })}
                placeholder="Shelf A1..."
              />
            </div>
            <div className={styles.formActions}>
              <button className={styles.cancelBtn} onClick={() => { resetInventoryForm(); setShowInventoryForm(false); }} disabled={isSaving}>
                Cancel
              </button>
              <button
                className={styles.saveBtn}
                onClick={editingInventory ? handleUpdateInventory : handleCreateInventory}
                disabled={isSaving}
              >
                {isSaving ? 'Saving...' : editingInventory ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unified list */}
      {!showDrugForm && !showInventoryForm && (
        <div className={styles.listSection}>
          <h2>Drugs ({displayedDrugs.length})</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : displayedDrugs.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No drugs found. Add your first drug to get started.</p>
            </div>
          ) : (
            <div className={styles.cardsGrid}>
              {displayedDrugs.map((drug) => {
                const inv = inventoryByDrugId[drug.id];
                return (
                  <div key={drug.id} className={styles.card}>
                    <div className={styles.cardHeader}>
                      <div>
                        <h3>{drug.name}</h3>
                        {drug.drug_code && <span className={styles.drugCode}>{drug.drug_code}</span>}
                      </div>
                      <span className={`${styles.badge} ${drug.is_active ? styles.activeBadge : styles.inactiveBadge}`}>
                        {drug.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    <div className={styles.cardBody}>
                      <div className={styles.drugInfo}>
                        {drug.generic_name && <p><strong>Generic:</strong> {drug.generic_name}</p>}
                        {drug.drug_class && <p><strong>Class:</strong> {drug.drug_class}</p>}
                        {(drug.cost_price != null || drug.sales_price != null) && (
                          <div className={styles.pricing}>
                            {drug.cost_price != null && <span>Cost: ₦{Number(drug.cost_price).toFixed(2)}</span>}
                            {drug.sales_price != null && <span>Sales: ₦{Number(drug.sales_price).toFixed(2)}</span>}
                          </div>
                        )}
                      </div>

                      <div className={styles.inventoryInfo}>
                        {inv ? (
                          <>
                            <div className={styles.stockRow}>
                              <span className={styles.stockLabel}>Stock:</span>
                              <span className={styles.stockValue}>
                                {inv.current_stock} {inv.unit}
                                {inv.is_out_of_stock && <span className={styles.outStock}> (Out)</span>}
                                {inv.is_low_stock && !inv.is_out_of_stock && <span className={styles.lowStock}> (Low)</span>}
                              </span>
                            </div>
                            <div className={styles.stockRow}>
                              <span className={styles.stockLabel}>Reorder:</span>
                              <span>{inv.reorder_level} {inv.unit}</span>
                            </div>
                            {inv.expiry_date && (
                              <p className={styles.expiry}>Expiry: {formatDate(inv.expiry_date)}</p>
                            )}
                          </>
                        ) : (
                          <p className={styles.noInventory}>No inventory record</p>
                        )}
                      </div>
                    </div>

                    <div className={styles.cardActions}>
                      <button className={styles.btnEdit} onClick={() => handleEditDrug(drug)}>
                        Edit Drug
                      </button>
                      {drug.is_active && (
                        <button className={styles.btnDeactivate} onClick={() => handleDeleteDrug(drug.id)}>
                          Deactivate
                        </button>
                      )}
                      {inv ? (
                        <>
                          <button className={styles.btnMovements} onClick={() => { setSelectedInventory(inv); setShowMovements(true); loadMovements(inv.id); }}>
                            Movements
                          </button>
                          <button className={styles.btnRestock} onClick={() => { setSelectedInventory(inv); setShowRestockModal(true); setRestockData({ quantity: 0, reference_number: '', notes: '' }); }}>
                            Restock
                          </button>
                          <button className={styles.btnAdjust} onClick={() => { setSelectedInventory(inv); setShowAdjustModal(true); setAdjustData({ quantity: 0, reason: '', notes: '' }); }}>
                            Adjust
                          </button>
                          <button className={styles.btnEdit} onClick={() => handleEditInventory(inv)}>
                            Edit Inventory
                          </button>
                          <button className={styles.btnDelete} onClick={() => handleDeleteInventory(inv.id)}>
                            Delete Inv
                          </button>
                        </>
                      ) : (
                        drug.is_active && (
                          <button className={styles.btnAddInv} onClick={() => handleAddInventory(drug)}>
                            + Add Inventory
                          </button>
                        )
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showMovements && selectedInventory && (
        <div
          className={styles.modalOverlay}
          onClick={() => { setShowMovements(false); setSelectedInventory(null); setMovements([]); }}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Stock Movements – {selectedInventory.drug_name}</h2>
              <button className={styles.closeBtn} onClick={() => { setShowMovements(false); setSelectedInventory(null); setMovements([]); }}>×</button>
            </div>
            <div className={styles.modalBody}>
              {loadingMovements ? (
                <LoadingSkeleton count={3} />
              ) : movements.length === 0 ? (
                <p>No movements</p>
              ) : (
                movements.map((m) => (
                  <div key={m.id} className={styles.movementCard}>
                    <span className={`${styles.movementBadge} ${getMovementBadgeClass(m.movement_type)}`}>{m.movement_type}</span>
                    <span className={styles.movementQty}>{m.quantity > 0 ? '+' : ''}{m.quantity} {selectedInventory.unit}</span>
                    <p>{formatDateTime(m.created_at)} {m.created_by_name && `by ${m.created_by_name}`}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {showRestockModal && selectedInventory && (
        <div
          className={styles.modalOverlay}
          onClick={() => { setShowRestockModal(false); setSelectedInventory(null); setRestockData({ quantity: 0, reference_number: '', notes: '' }); }}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Restock – {selectedInventory.drug_name}</h2>
              <button className={styles.closeBtn} onClick={() => { setShowRestockModal(false); setSelectedInventory(null); setRestockData({ quantity: 0, reference_number: '', notes: '' }); }}>×</button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Quantity *</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={restockData.quantity}
                  onChange={(e) => setRestockData({ ...restockData, quantity: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Reference</label>
                <input
                  type="text"
                  value={restockData.reference_number}
                  onChange={(e) => setRestockData({ ...restockData, reference_number: e.target.value })}
                  placeholder="Invoice #..."
                />
              </div>
              <div className={styles.formGroup}>
                <label>Notes</label>
                <textarea
                  value={restockData.notes}
                  onChange={(e) => setRestockData({ ...restockData, notes: e.target.value })}
                  rows={2}
                />
              </div>
              <div className={styles.formActions}>
                <button className={styles.cancelBtn} onClick={() => { setShowRestockModal(false); setSelectedInventory(null); setRestockData({ quantity: 0, reference_number: '', notes: '' }); }} disabled={isSaving}>Cancel</button>
                <button className={styles.saveBtn} onClick={handleRestock} disabled={isSaving}>{isSaving ? 'Restocking...' : 'Restock'}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showAdjustModal && selectedInventory && (
        <div
          className={styles.modalOverlay}
          onClick={() => { setShowAdjustModal(false); setSelectedInventory(null); setAdjustData({ quantity: 0, reason: '', notes: '' }); }}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Adjust Stock – {selectedInventory.drug_name}</h2>
              <button className={styles.closeBtn} onClick={() => { setShowAdjustModal(false); setSelectedInventory(null); setAdjustData({ quantity: 0, reason: '', notes: '' }); }}>×</button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Quantity * (+/-)</label>
                <input
                  type="number"
                  step="0.01"
                  value={adjustData.quantity}
                  onChange={(e) => setAdjustData({ ...adjustData, quantity: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Reason</label>
                <input
                  type="text"
                  value={adjustData.reason}
                  onChange={(e) => setAdjustData({ ...adjustData, reason: e.target.value })}
                  placeholder="Reason for adjustment"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Notes</label>
                <textarea
                  value={adjustData.notes}
                  onChange={(e) => setAdjustData({ ...adjustData, notes: e.target.value })}
                  rows={2}
                />
              </div>
              <div className={styles.formActions}>
                <button className={styles.cancelBtn} onClick={() => { setShowAdjustModal(false); setSelectedInventory(null); setAdjustData({ quantity: 0, reason: '', notes: '' }); }} disabled={isSaving}>Cancel</button>
                <button className={styles.saveBtn} onClick={handleAdjust} disabled={isSaving}>{isSaving ? 'Adjusting...' : 'Adjust'}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
