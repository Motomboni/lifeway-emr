/**
 * Structured allergy editor for patient management.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  AllergenType,
  AllergySeverity,
  PatientAllergy,
  createPatientAllergy,
  deactivatePatientAllergy,
  fetchPatientAllergies,
} from '../../api/patientAllergies';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/PatientManagement.module.css';

interface PatientAllergiesPanelProps {
  patientId: number;
  readOnly?: boolean;
}

const ALLERGEN_TYPES: AllergenType[] = ['DRUG', 'FOOD', 'ENVIRONMENT', 'OTHER', 'UNKNOWN'];
const SEVERITIES: AllergySeverity[] = ['MILD', 'MODERATE', 'SEVERE', 'UNKNOWN'];

export default function PatientAllergiesPanel({
  patientId,
  readOnly = false,
}: PatientAllergiesPanelProps) {
  const { showError, showSuccess } = useToast();
  const [allergies, setAllergies] = useState<PatientAllergy[]>([]);
  const [loading, setLoading] = useState(true);
  const [allergen, setAllergen] = useState('');
  const [allergenType, setAllergenType] = useState<AllergenType>('DRUG');
  const [severity, setSeverity] = useState<AllergySeverity>('UNKNOWN');
  const [reaction, setReaction] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchPatientAllergies(patientId);
      setAllergies(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load allergies');
    } finally {
      setLoading(false);
    }
  }, [patientId, showError]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    if (!allergen.trim()) {
      showError('Allergen name is required');
      return;
    }
    setSaving(true);
    try {
      await createPatientAllergy(patientId, {
        allergen: allergen.trim(),
        allergen_type: allergenType,
        severity,
        reaction: reaction.trim() || undefined,
      });
      setAllergen('');
      setReaction('');
      showSuccess('Allergy added');
      await load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to add allergy');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (id: number) => {
    try {
      await deactivatePatientAllergy(patientId, id);
      showSuccess('Allergy removed');
      await load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to remove allergy');
    }
  };

  if (loading) {
    return <p className={styles.allergyPanelLoading}>Loading allergies…</p>;
  }

  return (
    <div className={styles.allergyPanel}>
      <h4>Structured allergies</h4>
      {allergies.length === 0 ? (
        <p className={styles.allergyPanelEmpty}>No structured allergies documented.</p>
      ) : (
        <ul className={styles.allergyPanelList}>
          {allergies.map((a) => (
            <li key={a.id} className={styles.allergyPanelItem}>
              <span>
                <strong>{a.allergen}</strong>
                {a.severity !== 'UNKNOWN' && ` · ${a.severity}`}
                {a.allergen_type !== 'UNKNOWN' && ` · ${a.allergen_type}`}
                {a.reaction && ` — ${a.reaction}`}
              </span>
              {!readOnly && (
                <button type="button" onClick={() => handleRemove(a.id)}>
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {!readOnly && (
        <div className={styles.allergyPanelForm}>
          <input
            type="text"
            value={allergen}
            onChange={(e) => setAllergen(e.target.value)}
            placeholder="Allergen (e.g. Penicillin)"
          />
          <select
            value={allergenType}
            onChange={(e) => setAllergenType(e.target.value as AllergenType)}
          >
            {ALLERGEN_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as AllergySeverity)}
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={reaction}
            onChange={(e) => setReaction(e.target.value)}
            placeholder="Reaction (optional)"
          />
          <button type="button" disabled={saving} onClick={handleAdd}>
            {saving ? 'Adding…' : 'Add allergy'}
          </button>
        </div>
      )}
    </div>
  );
}
