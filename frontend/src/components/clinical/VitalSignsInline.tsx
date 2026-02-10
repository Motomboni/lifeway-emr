/**
 * Vital Signs Inline Component
 * 
 * Inline component for recording vital signs within consultation workspace.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { fetchVitalSigns, createVitalSigns } from '../../api/clinical';
import { fetchVisitDetails } from '../../api/visits';
import { VitalSigns, VitalSignsCreate } from '../../types/clinical';
import styles from '../../styles/ConsultationWorkspace.module.css';

const formatBMI = (bmi: unknown): string | null => {
  const num =
    typeof bmi === 'number'
      ? bmi
      : bmi !== null && bmi !== undefined
        ? parseFloat(bmi as any)
        : NaN;
  if (!Number.isFinite(num)) return null;
  return num.toFixed(1);
};

interface VitalSignsInlineProps {
  visitId: string;
}

export default function VitalSignsInline({ visitId }: VitalSignsInlineProps) {
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
      const data = await fetchVitalSigns(parseInt(visitId));
      setVitalSigns(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load vital signs');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      // Clean up form data - ensure null/0/empty values are sent as null
      // For male patients, ensure female-specific fields are null or empty string for CharField
      const isFemale = patientGender === 'FEMALE';
      const dataToSend: VitalSignsCreate = {
        temperature: formData.temperature && formData.temperature > 0 ? formData.temperature : null,
        systolic_bp: formData.systolic_bp && formData.systolic_bp > 0 ? formData.systolic_bp : null,
        diastolic_bp: formData.diastolic_bp && formData.diastolic_bp > 0 ? formData.diastolic_bp : null,
        pulse: formData.pulse && formData.pulse > 0 ? formData.pulse : null,
        respiratory_rate: formData.respiratory_rate && formData.respiratory_rate > 0 ? formData.respiratory_rate : null,
        oxygen_saturation: formData.oxygen_saturation && formData.oxygen_saturation > 0 ? formData.oxygen_saturation : null,
        weight: formData.weight && formData.weight > 0 ? formData.weight : null,
        height: formData.height && formData.height > 0 ? formData.height : null,
        muac: formData.muac && formData.muac > 0 ? formData.muac : null,
        urine_anc: isFemale ? (formData.urine_anc || '') : '',
        lmp: isFemale ? (formData.lmp || null) : null,
        edd: isFemale ? (formData.edd || null) : null,
        ega_weeks: isFemale ? (formData.ega_weeks && formData.ega_weeks > 0 ? formData.ega_weeks : null) : null,
        ega_days: isFemale ? (formData.ega_days && formData.ega_days >= 0 ? formData.ega_days : null) : null,
        notes: formData.notes || '',
      };
      
      // Ensure urine_anc is never null (CharField requires empty string)
      if (!isFemale) {
        dataToSend.urine_anc = '';
        dataToSend.lmp = null;
        dataToSend.edd = null;
        dataToSend.ega_weeks = null;
        dataToSend.ega_days = null;
      } else {
        if (!dataToSend.urine_anc) {
          dataToSend.urine_anc = '';
        }
      }
      
      // Validate temperature range (30.0-45.0°C)
      if (dataToSend.temperature !== null && dataToSend.temperature !== undefined) {
        if (dataToSend.temperature < 30.0 || dataToSend.temperature > 45.0) {
          showError('Temperature must be between 30.0°C and 45.0°C');
          setSaving(false);
          return;
        }
      }
      
      const cleanedData = dataToSend;
      
      await createVitalSigns(parseInt(visitId), cleanedData);
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
        urine_anc: null,
        lmp: null,
        edd: null,
        ega_weeks: null,
        ega_days: null,
        notes: '',
      });
      await loadVitalSigns();
    } catch (error: any) {
      showError(error.message || 'Failed to record vital signs');
    } finally {
      setSaving(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Vital Signs</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Vital Signs</h3>
        {!showForm && (
          <button
            className={styles.addButton}
            onClick={() => setShowForm(true)}
            type="button"
          >
            + Record Vital Signs
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className={styles.createForm}>
          <h4>Record Vital Signs</h4>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Temperature (°C)</label>
              <input
                type="number"
                step="0.1"
                min="30"
                max="45"
                value={formData.temperature || ''}
                onChange={(e) => setFormData({ ...formData, temperature: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Systolic BP (mmHg)</label>
              <input
                type="number"
                min="50"
                max="300"
                value={formData.systolic_bp || ''}
                onChange={(e) => setFormData({ ...formData, systolic_bp: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Diastolic BP (mmHg)</label>
              <input
                type="number"
                min="30"
                max="200"
                value={formData.diastolic_bp || ''}
                onChange={(e) => setFormData({ ...formData, diastolic_bp: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Pulse (bpm)</label>
              <input
                type="number"
                min="30"
                max="250"
                value={formData.pulse || ''}
                onChange={(e) => setFormData({ ...formData, pulse: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Respiratory Rate (bpm)</label>
              <input
                type="number"
                min="8"
                max="50"
                value={formData.respiratory_rate || ''}
                onChange={(e) => setFormData({ ...formData, respiratory_rate: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Oxygen Saturation (%)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={formData.oxygen_saturation || ''}
                onChange={(e) => setFormData({ ...formData, oxygen_saturation: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="500"
                value={formData.weight || ''}
                onChange={(e) => setFormData({ ...formData, weight: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>Height (cm)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="300"
                value={formData.height || ''}
                onChange={(e) => setFormData({ ...formData, height: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </div>
            
            <div className={styles.formGroup}>
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
                <div className={styles.formGroup}>
                  <label>Urine (ANC)</label>
                  <input
                    type="text"
                    placeholder="e.g., Protein: Negative, Glucose: Negative"
                    value={formData.urine_anc || ''}
                    onChange={(e) => setFormData({ ...formData, urine_anc: e.target.value || null })}
                  />
                </div>
                
                <div className={styles.formGroup}>
                  <label>LMP (Last Menstrual Period)</label>
                  <input
                    type="date"
                    value={formData.lmp || ''}
                    onChange={(e) => setFormData({ ...formData, lmp: e.target.value || null })}
                  />
                </div>
                
                <div className={styles.formGroup}>
                  <label>EDD (Expected Due Date)</label>
                  <input
                    type="date"
                    value={formData.edd || ''}
                    onChange={(e) => setFormData({ ...formData, edd: e.target.value || null })}
                  />
                </div>
                
                <div className={styles.formGroup}>
                  <label>EGA - Weeks</label>
                  <input
                    type="number"
                    min="0"
                    max="45"
                    value={formData.ega_weeks || ''}
                    onChange={(e) => setFormData({ ...formData, ega_weeks: e.target.value ? parseInt(e.target.value) : null })}
                  />
                </div>
                
                <div className={styles.formGroup}>
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
          
          <div className={styles.formGroup}>
            <label>Notes</label>
            <textarea
              value={formData.notes || ''}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={2}
            />
          </div>
          
          <div className={styles.formActions}>
            <button type="submit" disabled={saving} className={styles.saveButton}>
              {saving ? 'Recording...' : 'Record Vital Signs'}
            </button>
            <button
              type="button"
              onClick={() => {
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
                  urine_anc: null,
                  lmp: null,
                  edd: null,
                  ega_weeks: null,
                  ega_days: null,
                  notes: '',
                });
              }}
              className={styles.cancelButton}
              disabled={saving}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {vitalSigns.length === 0 && !showForm && (
        <p className={styles.emptyState}>No vital signs recorded for this visit.</p>
      )}

      {vitalSigns.map((vs) => (
        <div key={vs.id} className={styles.vitalSignsCard}>
          <div className={styles.vitalSignsHeader}>
            <strong>Recorded: {formatDateTime(vs.recorded_at)}</strong>
            <span>By: {vs.recorded_by_name}</span>
          </div>
          
          {vs.abnormal_flags.length > 0 && (
            <div className={styles.alertBanner}>
              ⚠️ Abnormal: {vs.abnormal_flags.join(', ')}
            </div>
          )}
          
          <div className={styles.vitalSignsGrid}>
            {vs.temperature && (
              <div>
                <strong>Temperature:</strong> {vs.temperature}°C
              </div>
            )}
            {vs.systolic_bp && vs.diastolic_bp && (
              <div>
                <strong>Blood Pressure:</strong> {vs.systolic_bp}/{vs.diastolic_bp} mmHg
              </div>
            )}
            {vs.pulse && (
              <div>
                <strong>Pulse:</strong> {vs.pulse} bpm
              </div>
            )}
            {vs.respiratory_rate && (
              <div>
                <strong>Respiratory Rate:</strong> {vs.respiratory_rate} bpm
              </div>
            )}
            {vs.oxygen_saturation && (
              <div>
                <strong>Oxygen Saturation:</strong> {vs.oxygen_saturation}%
              </div>
            )}
            {vs.weight && (
              <div>
                <strong>Weight:</strong> {vs.weight} kg
              </div>
            )}
            {vs.height && (
              <div>
                <strong>Height:</strong> {vs.height} cm
              </div>
            )}
            {formatBMI(vs.bmi) && (
              <div>
                <strong>BMI:</strong> {formatBMI(vs.bmi)}
              </div>
            )}
            {vs.muac && (
              <div>
                <strong>MUAC (Paed):</strong> {vs.muac} cm
              </div>
            )}
            {patientGender === 'FEMALE' && vs.urine_anc && (
              <div>
                <strong>Urine (ANC):</strong> {vs.urine_anc}
              </div>
            )}
            {patientGender === 'FEMALE' && vs.lmp && (
              <div>
                <strong>LMP:</strong> {new Date(vs.lmp).toLocaleDateString()}
              </div>
            )}
            {patientGender === 'FEMALE' && vs.edd && (
              <div>
                <strong>EDD:</strong> {new Date(vs.edd).toLocaleDateString()}
              </div>
            )}
            {patientGender === 'FEMALE' && (vs.ega_weeks !== null && vs.ega_weeks !== undefined) && (
              <div>
                <strong>EGA:</strong> {vs.ega_weeks} weeks {vs.ega_days ? `and ${vs.ega_days} days` : ''}
              </div>
            )}
          </div>
          
          {vs.notes && (
            <div className={styles.vitalSignsNotes}>
              <strong>Notes:</strong> {vs.notes}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
