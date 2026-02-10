/**
 * Vital Signs Section Component
 * 
 * Allows Nurse to record and view vital signs.
 * Visit-scoped and permission-aware.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { fetchVitalSignsNurse, createVitalSignsNurse } from '../../api/nursing';
import { fetchVisitDetails } from '../../api/visits';
import { VitalSigns, VitalSignsCreate } from '../../types/clinical';
import SpeechToTextButton from '../common/SpeechToTextButton';
import styles from '../../styles/NurseVisit.module.css';
import { logger } from '../../utils/logger';

interface VitalSignsSectionProps {
  visitId: string;
  canCreate: boolean;
}

export default function VitalSignsSection({ visitId, canCreate }: VitalSignsSectionProps) {
  const { showSuccess, showError } = useToast();
  const [vitalSigns, setVitalSigns] = useState<VitalSigns[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [patientGender, setPatientGender] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<VitalSignsCreate>({
    temperature: null,
    systolic_bp: null,
    diastolic_bp: null,
    pulse: null,
    respiratory_rate: null,
    oxygen_saturation: null,
    weight: null,
    height: null,
    muac: null,
    urine_anc: null,
    lmp: null,
    edd: null,
    ega_weeks: null,
    ega_days: null,
    notes: '',
  });

  useEffect(() => {
    loadVitalSigns();
    loadPatientGender();
  }, [visitId]);

  const loadPatientGender = async () => {
    try {
      const visitDetails = await fetchVisitDetails(visitId);
      const gender = visitDetails.patient_details?.gender || null;
      setPatientGender(gender);
    } catch (error) {
      console.error('Failed to load patient gender:', error);
      // Don't show error to user, just leave gender as null
    }
  };

  const loadVitalSigns = async () => {
    try {
      setLoading(true);
      const data = await fetchVitalSignsNurse(parseInt(visitId));
      setVitalSigns(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Error loading vital signs:', error);
      // Only show error if we don't have any vital signs yet
      // If we're refreshing after a save, silently fail to avoid duplicate error messages
      if (vitalSigns.length === 0) {
        showError(error.message || 'Failed to load vital signs');
      }
      // Ensure we set empty array on error to show empty state
      setVitalSigns([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!canCreate) {
      showError('Cannot record vital signs. Visit must be OPEN and payment cleared.');
      return;
    }
    
    try {
      setSaving(true);
      // Convert temperature from Fahrenheit to Celsius if provided
      // For male patients, ensure female-specific fields are null
      const isFemale = patientGender === 'FEMALE';
      const dataToSend: VitalSignsCreate = { ...formData };
      
      // Clear female-specific fields for male patients
      if (!isFemale) {
        // For CharField fields, use empty string instead of null
        dataToSend.urine_anc = '';
        dataToSend.lmp = null;
        dataToSend.edd = null;
        dataToSend.ega_weeks = null;
        dataToSend.ega_days = null;
      } else {
        // For female patients, ensure urine_anc is empty string if not provided
        if (!dataToSend.urine_anc) {
          dataToSend.urine_anc = '';
        }
      }
      
      // Handle temperature conversion and validation
      if (dataToSend.temperature && dataToSend.temperature > 0) {
        // Convert Fahrenheit to Celsius: C = (F - 32) * 5/9
        // Round to 2 decimal places to match backend max_digits=5, decimal_places=2 constraint
        const celsiusTemp = (dataToSend.temperature - 32) * 5 / 9;
        // Round to exactly 2 decimal places using toFixed and parseFloat
        const roundedTemp = parseFloat(celsiusTemp.toFixed(2));
        
        // Validate temperature is within acceptable range (30.0-45.0°C)
        if (roundedTemp < 30.0 || roundedTemp > 45.0) {
          showError(`Temperature ${roundedTemp.toFixed(1)}°C is out of range. Must be between 30.0°C and 45.0°C.`);
          setSaving(false);
          return;
        }
        
        dataToSend.temperature = roundedTemp;
      } else {
        // If temperature is not provided or invalid, set to null
        dataToSend.temperature = null;
      }
      const savedVitalSigns = await createVitalSignsNurse(parseInt(visitId), dataToSend);
      logger.debug('Vital signs saved successfully:', savedVitalSigns);
      showSuccess('Vital signs recorded successfully');
      setShowForm(false);
      setFormData({
        temperature: null,
        systolic_bp: null,
        diastolic_bp: null,
        pulse: null,
        respiratory_rate: null,
        oxygen_saturation: null,
        weight: null,
        height: null,
        muac: null,
        nutritional_status: null,
        urine_anc: null,
        lmp: null,
        edd: null,
        ega_weeks: null,
        ega_days: null,
        notes: '',
      });
      // Add a small delay to ensure the backend has processed the save
      await new Promise(resolve => setTimeout(resolve, 300));
      // Reload vital signs - if it fails, we'll still show the saved one
      try {
        await loadVitalSigns();
      } catch (reloadError: any) {
        console.error('Error reloading vital signs after save:', reloadError);
        // If reload fails but we have a saved vital sign, add it to the list
        if (savedVitalSigns) {
          setVitalSigns(prev => [savedVitalSigns, ...prev]);
        }
        // Show a warning but don't fail the whole operation
        showError('Vital signs saved but failed to refresh list. Please refresh the page.');
      }
    } catch (error: any) {
      console.error('Error saving vital signs:', error);
      // Parse error message to show more user-friendly messages
      let errorMessage = 'Failed to record vital signs';
      if (error.responseData) {
        if (error.responseData.errors) {
          // Handle field-specific errors
          const fieldErrors = Object.entries(error.responseData.errors)
            .map(([field, messages]: [string, any]) => {
              const fieldName = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
              return `${fieldName}: ${Array.isArray(messages) ? messages.join(', ') : messages}`;
            })
            .join('. ');
          errorMessage = fieldErrors || error.responseData.detail || errorMessage;
        } else if (error.responseData.detail) {
          errorMessage = error.responseData.detail;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      showError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const formatBMI = (bmi: unknown): string | null => {
    const num = typeof bmi === 'number' ? bmi : (bmi !== null && bmi !== undefined ? parseFloat(bmi as any) : NaN);
    if (!Number.isFinite(num)) return null;
    return num.toFixed(1);
  };

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3>📊 Vital Signs</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={() => setShowForm(!showForm)}
            disabled={saving}
          >
            {showForm ? 'Cancel' : '+ Record Vital Signs'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.vitalSignsForm}>
          <div className={styles.formGrid}>
            <div className={styles.formField}>
              <label>Temperature (°F)</label>
              <input
                type="number"
                step="0.1"
                value={formData.temperature || ''}
                onChange={(e) => setFormData({ ...formData, temperature: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Systolic BP (mmHg)</label>
              <input
                type="number"
                value={formData.systolic_bp || ''}
                onChange={(e) => setFormData({ ...formData, systolic_bp: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Diastolic BP (mmHg)</label>
              <input
                type="number"
                value={formData.diastolic_bp || ''}
                onChange={(e) => setFormData({ ...formData, diastolic_bp: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Heart Rate (bpm)</label>
              <input
                type="number"
                value={formData.pulse || ''}
                onChange={(e) => setFormData({ ...formData, pulse: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Respiratory Rate (breaths/min)</label>
              <input
                type="number"
                value={formData.respiratory_rate || ''}
                onChange={(e) => setFormData({ ...formData, respiratory_rate: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Oxygen Saturation (%)</label>
              <input
                type="number"
                value={formData.oxygen_saturation || ''}
                onChange={(e) => setFormData({ ...formData, oxygen_saturation: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={formData.weight || ''}
                onChange={(e) => setFormData({ ...formData, weight: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>Height (cm)</label>
              <input
                type="number"
                step="0.1"
                value={formData.height || ''}
                onChange={(e) => setFormData({ ...formData, height: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            <div className={styles.formField}>
              <label>MUAC (Paed) (cm)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="50"
                value={formData.muac || ''}
                onChange={(e) => setFormData({ ...formData, muac: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            {patientGender === 'FEMALE' && (
              <>
                <div className={styles.formField}>
                  <label>Urine (ANC)</label>
                  <input
                    type="text"
                    placeholder="e.g., Protein: Negative, Glucose: Negative"
                    value={formData.urine_anc || ''}
                    onChange={(e) => setFormData({ ...formData, urine_anc: e.target.value || null })}
                  />
                </div>
                <div className={styles.formField}>
                  <label>LMP (Last Menstrual Period)</label>
                  <input
                    type="date"
                    value={formData.lmp || ''}
                    onChange={(e) => setFormData({ ...formData, lmp: e.target.value || null })}
                  />
                </div>
                <div className={styles.formField}>
                  <label>EDD (Expected Due Date)</label>
                  <input
                    type="date"
                    value={formData.edd || ''}
                    onChange={(e) => setFormData({ ...formData, edd: e.target.value || null })}
                  />
                </div>
                <div className={styles.formField}>
                  <label>EGA - Weeks</label>
                  <input
                    type="number"
                    min="0"
                    max="45"
                    value={formData.ega_weeks || ''}
                    onChange={(e) => setFormData({ ...formData, ega_weeks: e.target.value ? parseInt(e.target.value) : null })}
                  />
                </div>
                <div className={styles.formField}>
                  <label>EGA - Days</label>
                  <input
                    type="number"
                    min="0"
                    max="6"
                    value={formData.ega_days || ''}
                    onChange={(e) => setFormData({ ...formData, ega_days: e.target.value ? parseInt(e.target.value) : null })}
                  />
                </div>
              </>
            )}
          </div>
          <div className={styles.formField}>
            <label>Notes</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
              />
              <SpeechToTextButton
                value={formData.notes}
                onTranscribe={(text) => setFormData((prev) => ({ ...prev, notes: text }))}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={saving} className={styles.saveButton}>
              {saving ? 'Saving...' : 'Save Vital Signs'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className={styles.cancelButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className={styles.loading}>Loading vital signs...</div>
      ) : vitalSigns.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No vital signs recorded yet.</p>
          {canCreate && <p>Click "Record Vital Signs" to add the first entry.</p>}
        </div>
      ) : (
        <div className={styles.vitalSignsList}>
          {vitalSigns.map((vs) => (
            <div key={vs.id} className={styles.vitalSignsCard}>
              <div className={styles.vitalSignsHeader}>
                <span className={styles.recordedBy}>
                  Recorded by {vs.recorded_by_name || 'Nurse'} on {new Date(vs.recorded_at).toLocaleString()}
                </span>
              </div>
              <div className={styles.vitalSignsGrid}>
                {vs.temperature && (
                  <div className={styles.vitalSignItem}>
                    <label>Temperature:</label>
                    <span>{((parseFloat(vs.temperature.toString()) * 9 / 5) + 32).toFixed(1)}°F</span>
                  </div>
                )}
                {vs.systolic_bp && vs.diastolic_bp && (
                  <div className={styles.vitalSignItem}>
                    <label>Blood Pressure:</label>
                    <span>{vs.systolic_bp}/{vs.diastolic_bp} mmHg</span>
                  </div>
                )}
                {vs.pulse && (
                  <div className={styles.vitalSignItem}>
                    <label>Heart Rate:</label>
                    <span>{vs.pulse} bpm</span>
                  </div>
                )}
                {vs.respiratory_rate && (
                  <div className={styles.vitalSignItem}>
                    <label>Respiratory Rate:</label>
                    <span>{vs.respiratory_rate} breaths/min</span>
                  </div>
                )}
                {vs.oxygen_saturation && (
                  <div className={styles.vitalSignItem}>
                    <label>Oxygen Saturation:</label>
                    <span>{vs.oxygen_saturation}%</span>
                  </div>
                )}
                {vs.weight && (
                  <div className={styles.vitalSignItem}>
                    <label>Weight:</label>
                    <span>{vs.weight} kg</span>
                  </div>
                )}
                {vs.height && (
                  <div className={styles.vitalSignItem}>
                    <label>Height:</label>
                    <span>{vs.height} cm</span>
                  </div>
                )}
                {formatBMI(vs.bmi) && (
                  <div className={styles.vitalSignItem}>
                    <label>BMI:</label>
                    <span>{formatBMI(vs.bmi)}</span>
                  </div>
                )}
                {vs.muac && (
                  <div className={styles.vitalSignItem}>
                    <label>MUAC (Paed):</label>
                    <span>{vs.muac} cm</span>
                  </div>
                )}
                {patientGender === 'FEMALE' && vs.urine_anc && (
                  <div className={styles.vitalSignItem}>
                    <label>Urine (ANC):</label>
                    <span>{vs.urine_anc}</span>
                  </div>
                )}
                {patientGender === 'FEMALE' && vs.lmp && (
                  <div className={styles.vitalSignItem}>
                    <label>LMP:</label>
                    <span>{new Date(vs.lmp).toLocaleDateString()}</span>
                  </div>
                )}
                {patientGender === 'FEMALE' && vs.edd && (
                  <div className={styles.vitalSignItem}>
                    <label>EDD:</label>
                    <span>{new Date(vs.edd).toLocaleDateString()}</span>
                  </div>
                )}
                {patientGender === 'FEMALE' && (vs.ega_weeks !== null && vs.ega_weeks !== undefined) && (
                  <div className={styles.vitalSignItem}>
                    <label>EGA:</label>
                    <span>{vs.ega_weeks} weeks {vs.ega_days ? `and ${vs.ega_days} days` : ''}</span>
                  </div>
                )}
              </div>
              {vs.notes && (
                <div className={styles.vitalSignsNotes}>
                  <label>Notes:</label>
                  <p>{vs.notes}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
