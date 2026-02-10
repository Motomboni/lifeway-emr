/**
 * Diagnosis Codes Component
 * 
 * Displays and manages ICD-11 diagnosis codes for a consultation
 */
import React, { useState, useEffect } from 'react';
import {
  getDiagnosisCodes,
  createDiagnosisCode,
  updateDiagnosisCode,
  deleteDiagnosisCode,
} from '../../api/diagnosisCodes';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import type { DiagnosisCode, DiagnosisCodeData } from '../../types/consultation';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface DiagnosisCodesProps {
  visitId: string;
  consultationId: number;
}

export default function DiagnosisCodes({ visitId, consultationId }: DiagnosisCodesProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [codes, setCodes] = useState<DiagnosisCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<DiagnosisCodeData>({
    code_type: 'ICD11',
    code: '',
    description: '',
    is_primary: false,
  });

  useEffect(() => {
    loadCodes();
  }, [visitId, consultationId]);

  const loadCodes = async () => {
    try {
      setLoading(true);
      const data = await getDiagnosisCodes(visitId);
      // Ensure data is an array (handle paginated responses or direct arrays)
      const codesArray = Array.isArray(data) ? data : (data as any)?.results || [];
      setCodes(codesArray);
    } catch (error: any) {
      showError(error.message || 'Failed to load diagnosis codes');
      setCodes([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await updateDiagnosisCode(visitId, editingId, formData);
        showSuccess('Diagnosis code updated');
      } else {
        await createDiagnosisCode(visitId, formData);
        showSuccess('Diagnosis code added');
      }
      setShowAddForm(false);
      setEditingId(null);
      setFormData({
        code_type: 'ICD11',
        code: '',
        description: '',
        is_primary: false,
      });
      loadCodes();
    } catch (error: any) {
      showError(error.message || 'Failed to save diagnosis code');
    }
  };

  const handleEdit = (code: DiagnosisCode) => {
    setEditingId(code.id);
    setFormData({
      code_type: code.code_type,
      code: code.code,
      description: code.description,
      is_primary: code.is_primary,
    });
    setShowAddForm(true);
  };

  const handleDelete = async (codeId: number) => {
    if (!window.confirm('Are you sure you want to delete this diagnosis code?')) {
      return;
    }
    try {
      await deleteDiagnosisCode(visitId, codeId);
      showSuccess('Diagnosis code deleted');
      loadCodes();
    } catch (error: any) {
      showError(error.message || 'Failed to delete diagnosis code');
    }
  };

  const handleCancel = () => {
    setShowAddForm(false);
    setEditingId(null);
    setFormData({
      code_type: 'ICD11',
      code: '',
      description: '',
      is_primary: false,
    });
  };

  if (loading) {
    return (
      <div className={styles.inlineCard}>
        <div className={styles.cardHeader}>
          <h3>Diagnosis Codes (ICD-11)</h3>
        </div>
        <p>Loading...</p>
      </div>
    );
  }

  const canEdit = user?.role === 'DOCTOR';

  return (
    <div className={styles.inlineCard}>
      <div className={styles.cardHeader}>
        <h3>Diagnosis Codes (ICD-11)</h3>
        {canEdit && !showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            className={styles.primaryButton}
            type="button"
          >
            + Add Code
          </button>
        )}
      </div>

      {showAddForm && (
        <form onSubmit={handleSubmit} className={styles.formRow}>
          <div className={styles.formRow}>
            <label>
              Code Type <span className={styles.required}>*</span>
            </label>
            <select
              value={formData.code_type}
              onChange={(e) =>
                setFormData({ ...formData, code_type: e.target.value as 'ICD11' | 'ICD10' })
              }
              required
            >
              <option value="ICD11">ICD-11</option>
              <option value="ICD10">ICD-10</option>
            </select>
          </div>

          <div className={styles.formRow}>
            <label>
              Code <span className={styles.required}>*</span>
            </label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="e.g., CA40.Z"
              required
            />
          </div>

          <div className={styles.formRow}>
            <label>
              Description <span className={styles.required}>*</span>
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Diagnosis description"
              required
              rows={3}
            />
          </div>

          <div className={styles.formRow}>
            <label>
              <input
                type="checkbox"
                checked={formData.is_primary}
                onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
              />
              Set as Primary Diagnosis
            </label>
          </div>

          <div className={styles.formRow}>
            <button type="submit" className={styles.primaryButton}>
              {editingId ? 'Update' : 'Add'} Code
            </button>
            <button type="button" onClick={handleCancel} className={styles.secondaryButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {!Array.isArray(codes) || codes.length === 0 ? (
        <p className={styles.emptyText}>No diagnosis codes added yet.</p>
      ) : (
        <div className={styles.codeList}>
          {codes.map((code) => (
            <div key={code.id} className={styles.codeItem}>
              <div className={styles.codeHeader}>
                <div>
                  <strong className={code.is_primary ? styles.primaryCode : ''}>
                    {code.code}
                  </strong>
                  {code.is_primary && <span className={styles.primaryBadge}>Primary</span>}
                  {code.confidence && (
                    <span className={styles.confidenceBadge}>
                      {Math.round(code.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
                {canEdit && (
                  <div className={styles.codeActions}>
                    <button
                      onClick={() => handleEdit(code)}
                      className={styles.secondaryButton}
                      type="button"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(code.id)}
                      className={styles.secondaryButton}
                      type="button"
                      style={{ color: '#f44336' }}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
              <p className={styles.codeDescription}>{code.description}</p>
              {code.created_by_name && (
                <p className={styles.codeMeta}>
                  Added by {code.created_by_name} on{' '}
                  {new Date(code.created_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

