/**
 * Inventory Management Page
 * 
 * For Pharmacists to manage drug inventory and stock levels.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
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
  InventoryFilters,
  RestockData,
  AdjustData,
  PaginatedInventoryResponse,
  PaginatedMovementResponse,
} from '../api/inventory';
import { fetchDrugs } from '../api/drug';
import { Drug } from '../types/drug';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Inventory.module.css';

export default function InventoryPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();

  const [inventory, setInventory] = useState<DrugInventory[]>([]);
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingInventory, setEditingInventory] = useState<DrugInventory | null>(null);
  const [selectedInventory, setSelectedInventory] = useState<DrugInventory | null>(null);
  const [showMovements, setShowMovements] = useState(false);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [loadingMovements, setLoadingMovements] = useState(false);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  
  // Filters
  const [viewMode, setViewMode] = useState<'all' | 'low_stock' | 'out_of_stock'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form data
  const [formData, setFormData] = useState<DrugInventoryCreateData>({
    drug: 0,
    current_stock: 0,
    unit: 'units',
    reorder_level: 0,
    batch_number: '',
    expiry_date: '',
    location: '',
  });
  
  // Restock/Adjust data
  const [restockData, setRestockData] = useState<RestockData>({
    quantity: 0,
    reference_number: '',
    notes: '',
  });
  
  const [adjustData, setAdjustData] = useState<AdjustData>({
    quantity: 0,
    reason: '',
    notes: '',
  });

  useEffect(() => {
    loadInventory();
    loadDrugs();
  }, [viewMode]);

  const loadInventory = async () => {
    try {
      setLoading(true);
      let response;
      
      if (viewMode === 'low_stock') {
        response = await fetchLowStockInventory();
      } else if (viewMode === 'out_of_stock') {
        response = await fetchOutOfStockInventory();
      } else {
        const filters: InventoryFilters = {};
        if (searchQuery) {
          filters.search = searchQuery;
        }
        response = await fetchInventory(filters);
      }
      
      const inventoryArray = Array.isArray(response)
        ? response
        : (response as PaginatedInventoryResponse)?.results || [];
      setInventory(inventoryArray);
    } catch (error) {
      console.error('Error loading inventory:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load inventory';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadDrugs = async () => {
    try {
      const response = await fetchDrugs();
      const drugsArray = Array.isArray(response) ? response : (response as any)?.results || [];
      setDrugs(drugsArray.filter((drug: Drug) => drug.is_active));
    } catch (error) {
      console.error('Error loading drugs:', error);
    }
  };

  const loadMovements = async (inventoryId: number) => {
    try {
      setLoadingMovements(true);
      const response = await fetchStockMovements({ inventory: inventoryId });
      const movementsArray = Array.isArray(response)
        ? response
        : (response as PaginatedMovementResponse)?.results || [];
      setMovements(movementsArray);
    } catch (error) {
      console.error('Error loading movements:', error);
      showError('Failed to load stock movements');
    } finally {
      setLoadingMovements(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.drug || formData.current_stock < 0 || formData.reorder_level < 0) {
      showError('Please fill in all required fields with valid values');
      return;
    }

    try {
      setIsSaving(true);
      await createInventory(formData);
      showSuccess('Inventory record created successfully');
      setShowCreateForm(false);
      resetForm();
      loadInventory();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create inventory record';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingInventory) return;

    try {
      setIsSaving(true);
      await updateInventory(editingInventory.id, formData as DrugInventoryUpdateData);
      showSuccess('Inventory record updated successfully');
      setEditingInventory(null);
      resetForm();
      setShowCreateForm(false);
      loadInventory();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update inventory record';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (inventoryId: number) => {
    if (!window.confirm('Are you sure you want to delete this inventory record?')) {
      return;
    }

    try {
      await deleteInventory(inventoryId);
      showSuccess('Inventory record deleted successfully');
      loadInventory();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete inventory record';
      showError(errorMessage);
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
      loadInventory();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to restock inventory';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAdjust = async () => {
    if (!selectedInventory || adjustData.quantity === 0) {
      showError('Please enter a valid adjustment quantity (cannot be zero)');
      return;
    }

    try {
      setIsSaving(true);
      await adjustInventory(selectedInventory.id, adjustData);
      showSuccess('Inventory adjusted successfully');
      setShowAdjustModal(false);
      setSelectedInventory(null);
      setAdjustData({ quantity: 0, reason: '', notes: '' });
      loadInventory();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to adjust inventory';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = (inventoryItem: DrugInventory) => {
    setEditingInventory(inventoryItem);
    setFormData({
      drug: inventoryItem.drug,
      current_stock: inventoryItem.current_stock,
      unit: inventoryItem.unit,
      reorder_level: inventoryItem.reorder_level,
      batch_number: inventoryItem.batch_number || '',
      expiry_date: inventoryItem.expiry_date ? inventoryItem.expiry_date.split('T')[0] : '',
      location: inventoryItem.location || '',
    });
    setShowCreateForm(true);
  };

  const handleViewMovements = async (inventoryItem: DrugInventory) => {
    setSelectedInventory(inventoryItem);
    setShowMovements(true);
    await loadMovements(inventoryItem.id);
  };

  const resetForm = () => {
    setFormData({
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

  const handleCancelForm = () => {
    setShowCreateForm(false);
    setEditingInventory(null);
    resetForm();
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getMovementTypeBadgeClass = (type: string) => {
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
      <div className={styles.inventoryPage}>
        <BackToDashboard />
        <div className={styles.accessDenied}>
          <h2>Access Denied</h2>
          <p>Only Pharmacists can manage inventory.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.inventoryPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Inventory Management</h1>
        {!showCreateForm && (
          <button
            className={styles.createButton}
            onClick={() => setShowCreateForm(true)}
          >
            + New Inventory Record
          </button>
        )}
      </header>

      {/* View Mode and Filters */}
      {!showCreateForm && !showMovements && (
        <div className={styles.filtersSection}>
          <div className={styles.viewModeButtons}>
            <button
              className={viewMode === 'all' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('all')}
            >
              All Items
            </button>
            <button
              className={viewMode === 'low_stock' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('low_stock')}
            >
              Low Stock
            </button>
            <button
              className={viewMode === 'out_of_stock' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('out_of_stock')}
            >
              Out of Stock
            </button>
          </div>

          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by drug name, code, or batch number..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  loadInventory();
                }
              }}
            />
            <button onClick={loadInventory}>Search</button>
          </div>
        </div>
      )}

      {/* Create/Edit Form */}
      {showCreateForm && (
        <div className={styles.formContainer}>
          <h2>{editingInventory ? 'Edit Inventory Record' : 'Create New Inventory Record'}</h2>
          
          <div className={styles.formGroup}>
            <label>Drug *</label>
            <select
              value={formData.drug}
              onChange={(e) => setFormData({ ...formData, drug: parseInt(e.target.value) })}
              required
              disabled={!!editingInventory}
            >
              <option value={0}>Select a drug...</option>
              {drugs.map((drug) => (
                <option key={drug.id} value={drug.id}>
                  {drug.name} {drug.drug_code && `(${drug.drug_code})`}
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
                value={formData.current_stock}
                onChange={(e) => setFormData({ ...formData, current_stock: parseFloat(e.target.value) || 0 })}
                required
              />
            </div>

            <div className={styles.formGroup}>
              <label>Unit *</label>
              <input
                type="text"
                value={formData.unit}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                placeholder="e.g., tablets, bottles, vials"
                required
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Reorder Level *</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={formData.reorder_level}
              onChange={(e) => setFormData({ ...formData, reorder_level: parseFloat(e.target.value) || 0 })}
              required
            />
            <small>Alert will be shown when stock falls below this level</small>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Batch Number</label>
              <input
                type="text"
                value={formData.batch_number}
                onChange={(e) => setFormData({ ...formData, batch_number: e.target.value })}
                placeholder="Optional"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Expiry Date</label>
              <input
                type="date"
                value={formData.expiry_date}
                onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Location</label>
            <input
              type="text"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              placeholder="e.g., Shelf A1, Refrigerator 1"
            />
          </div>

          <div className={styles.formActions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={handleCancelForm}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="button"
              className={styles.saveButton}
              onClick={editingInventory ? handleUpdate : handleCreate}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : editingInventory ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      )}

      {/* Stock Movements Modal */}
      {showMovements && selectedInventory && (
        <div className={styles.modalOverlay} onClick={() => {
          setShowMovements(false);
          setSelectedInventory(null);
          setMovements([]);
        }}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Stock Movements - {selectedInventory.drug_name}</h2>
              <button
                className={styles.closeButton}
                onClick={() => {
                  setShowMovements(false);
                  setSelectedInventory(null);
                  setMovements([]);
                }}
              >
                ×
              </button>
            </div>
            <div className={styles.modalBody}>
              {loadingMovements ? (
                <LoadingSkeleton count={5} />
              ) : movements.length === 0 ? (
                <p>No stock movements found</p>
              ) : (
                <div className={styles.movementsList}>
                  {movements.map((movement) => (
                    <div key={movement.id} className={styles.movementCard}>
                      <div className={styles.movementHeader}>
                        <span className={`${styles.movementTypeBadge} ${getMovementTypeBadgeClass(movement.movement_type)}`}>
                          {movement.movement_type}
                        </span>
                        <span className={styles.movementQuantity}>
                          {movement.quantity > 0 ? '+' : ''}{movement.quantity} {selectedInventory.unit}
                        </span>
                      </div>
                      <div className={styles.movementDetails}>
                        <p><strong>Date:</strong> {formatDateTime(movement.created_at)}</p>
                        {movement.reference_number && (
                          <p><strong>Reference:</strong> {movement.reference_number}</p>
                        )}
                        {movement.notes && (
                          <p><strong>Notes:</strong> {movement.notes}</p>
                        )}
                        {movement.created_by_name && (
                          <p><strong>By:</strong> {movement.created_by_name}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Restock Modal */}
      {showRestockModal && selectedInventory && (
        <div className={styles.modalOverlay} onClick={() => {
          setShowRestockModal(false);
          setSelectedInventory(null);
          setRestockData({ quantity: 0, reference_number: '', notes: '' });
        }}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Restock - {selectedInventory.drug_name}</h2>
              <button
                className={styles.closeButton}
                onClick={() => {
                  setShowRestockModal(false);
                  setSelectedInventory(null);
                  setRestockData({ quantity: 0, reference_number: '', notes: '' });
                }}
              >
                ×
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Quantity to Add *</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={restockData.quantity}
                  onChange={(e) => setRestockData({ ...restockData, quantity: parseFloat(e.target.value) || 0 })}
                  required
                />
              </div>
              <div className={styles.formGroup}>
                <label>Reference Number</label>
                <input
                  type="text"
                  value={restockData.reference_number}
                  onChange={(e) => setRestockData({ ...restockData, reference_number: e.target.value })}
                  placeholder="e.g., Invoice #12345"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Notes</label>
                <textarea
                  value={restockData.notes}
                  onChange={(e) => setRestockData({ ...restockData, notes: e.target.value })}
                  rows={3}
                  placeholder="Additional notes..."
                />
              </div>
              <div className={styles.formActions}>
                <button
                  className={styles.cancelButton}
                  onClick={() => {
                    setShowRestockModal(false);
                    setSelectedInventory(null);
                    setRestockData({ quantity: 0, reference_number: '', notes: '' });
                  }}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  className={styles.saveButton}
                  onClick={handleRestock}
                  disabled={isSaving}
                >
                  {isSaving ? 'Restocking...' : 'Restock'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Adjust Modal */}
      {showAdjustModal && selectedInventory && (
        <div className={styles.modalOverlay} onClick={() => {
          setShowAdjustModal(false);
          setSelectedInventory(null);
          setAdjustData({ quantity: 0, reason: '', notes: '' });
        }}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Adjust Stock - {selectedInventory.drug_name}</h2>
              <button
                className={styles.closeButton}
                onClick={() => {
                  setShowAdjustModal(false);
                  setSelectedInventory(null);
                  setAdjustData({ quantity: 0, reason: '', notes: '' });
                }}
              >
                ×
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Adjustment Quantity *</label>
                <input
                  type="number"
                  step="0.01"
                  value={adjustData.quantity}
                  onChange={(e) => setAdjustData({ ...adjustData, quantity: parseFloat(e.target.value) || 0 })}
                  required
                />
                <small>Positive to increase, negative to decrease</small>
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
                  rows={3}
                  placeholder="Additional notes..."
                />
              </div>
              <div className={styles.formActions}>
                <button
                  className={styles.cancelButton}
                  onClick={() => {
                    setShowAdjustModal(false);
                    setSelectedInventory(null);
                    setAdjustData({ quantity: 0, reason: '', notes: '' });
                  }}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  className={styles.saveButton}
                  onClick={handleAdjust}
                  disabled={isSaving}
                >
                  {isSaving ? 'Adjusting...' : 'Adjust'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inventory List */}
      {!showCreateForm && !showMovements && (
        <div className={styles.inventoryList}>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : inventory.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No inventory items found</p>
            </div>
          ) : (
            inventory.map((item) => (
              <div key={item.id} className={styles.inventoryCard}>
                <div className={styles.inventoryHeader}>
                  <div>
                    <h3>{item.drug_name}</h3>
                    {item.drug_code && <p className={styles.drugCode}>{item.drug_code}</p>}
                  </div>
                  <div className={styles.stockBadges}>
                    {item.is_out_of_stock && (
                      <span className={`${styles.stockBadge} ${styles.outOfStock}`}>
                        OUT OF STOCK
                      </span>
                    )}
                    {item.is_low_stock && !item.is_out_of_stock && (
                      <span className={`${styles.stockBadge} ${styles.lowStock}`}>
                        LOW STOCK
                      </span>
                    )}
                  </div>
                </div>

                <div className={styles.inventoryDetails}>
                  <div className={styles.stockInfo}>
                    <div className={styles.stockItem}>
                      <span className={styles.stockLabel}>Current Stock:</span>
                      <span className={styles.stockValue}>
                        {item.current_stock} {item.unit}
                      </span>
                    </div>
                    <div className={styles.stockItem}>
                      <span className={styles.stockLabel}>Reorder Level:</span>
                      <span className={styles.stockValue}>
                        {item.reorder_level} {item.unit}
                      </span>
                    </div>
                  </div>

                  {(item.batch_number || item.expiry_date || item.location) && (
                    <div className={styles.additionalInfo}>
                      {item.batch_number && (
                        <p><strong>Batch:</strong> {item.batch_number}</p>
                      )}
                      {item.expiry_date && (
                        <p><strong>Expiry:</strong> {formatDate(item.expiry_date)}</p>
                      )}
                      {item.location && (
                        <p><strong>Location:</strong> {item.location}</p>
                      )}
                    </div>
                  )}

                  {item.last_restocked_at && (
                    <div className={styles.restockInfo}>
                      <p>
                        <strong>Last Restocked:</strong> {formatDateTime(item.last_restocked_at)}
                        {item.last_restocked_by_name && ` by ${item.last_restocked_by_name}`}
                      </p>
                    </div>
                  )}
                </div>

                <div className={styles.inventoryActions}>
                  <button
                    className={styles.actionButton}
                    onClick={() => handleViewMovements(item)}
                  >
                    View Movements
                  </button>
                  <button
                    className={styles.restockButton}
                    onClick={() => {
                      setSelectedInventory(item);
                      setShowRestockModal(true);
                    }}
                  >
                    Restock
                  </button>
                  <button
                    className={styles.adjustButton}
                    onClick={() => {
                      setSelectedInventory(item);
                      setShowAdjustModal(true);
                    }}
                  >
                    Adjust
                  </button>
                  <button
                    className={styles.editButton}
                    onClick={() => handleEdit(item)}
                  >
                    Edit
                  </button>
                  <button
                    className={styles.deleteButton}
                    onClick={() => handleDelete(item.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
