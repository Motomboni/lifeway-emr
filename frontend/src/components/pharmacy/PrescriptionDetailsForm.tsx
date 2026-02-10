/**
 * PrescriptionDetailsForm Component
 * 
 * Modal form for doctors to enter prescription details when ordering pharmacy services.
 * 
 * Fields:
 * - Drug Name (pre-filled from service catalog)
 * - Dosage (e.g., "500mg", "2 tablets", "10ml")
 * - Frequency (e.g., "Twice daily", "Every 8 hours", "3 times a day")
 * - Duration (e.g., "7 days", "14 days", "Until symptoms resolve")
 * - Instructions (e.g., "Take with food", "Take on empty stomach")
 * - Quantity (optional)
 */
import React, { useState } from 'react';
import styles from './PrescriptionDetailsForm.module.css';

interface PrescriptionDetailsFormProps {
  drugName: string;
  onSubmit: (prescriptionDetails: PrescriptionDetails) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export interface PrescriptionDetails {
  dosage: string;
  frequency: string;
  duration: string;
  instructions: string;
  quantity?: string;
}

// Common frequency options
const FREQUENCY_OPTIONS = [
  'Once daily',
  'Twice daily',
  'Three times daily',
  'Four times daily',
  'Every 4 hours',
  'Every 6 hours',
  'Every 8 hours',
  'Every 12 hours',
  'As needed',
  'At bedtime',
  'In the morning',
  'With meals',
];

export default function PrescriptionDetailsForm({
  drugName,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: PrescriptionDetailsFormProps) {
  const [dosage, setDosage] = useState('');
  const [frequency, setFrequency] = useState('');
  const [customFrequency, setCustomFrequency] = useState('');
  const [duration, setDuration] = useState('');
  const [instructions, setInstructions] = useState('');
  const [quantity, setQuantity] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!dosage.trim()) {
      newErrors.dosage = 'Dosage is required (e.g., "500mg", "2 tablets")';
    }

    const finalFrequency = frequency === 'Custom' ? customFrequency : frequency;
    if (!finalFrequency.trim()) {
      newErrors.frequency = 'Frequency is required (e.g., "Twice daily")';
    }

    if (!duration.trim()) {
      newErrors.duration = 'Duration is required (e.g., "7 days")';
    }

    if (!instructions.trim()) {
      newErrors.instructions = 'Instructions are required (e.g., "Take with food")';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    const finalFrequency = frequency === 'Custom' ? customFrequency : frequency;

    onSubmit({
      dosage: dosage.trim(),
      frequency: finalFrequency.trim(),
      duration: duration.trim(),
      instructions: instructions.trim(),
      quantity: quantity.trim() || undefined,
    });
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3>📝 Prescription Details</h3>
          <p className={styles.drugName}>{drugName}</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* Dosage */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Dosage</label>
            <input
              type="text"
              value={dosage}
              onChange={(e) => setDosage(e.target.value)}
              placeholder="e.g., 500mg, 2 tablets, 10ml"
              className={errors.dosage ? styles.inputError : ''}
              disabled={isSubmitting}
            />
            {errors.dosage && <span className={styles.error}>{errors.dosage}</span>}
            <span className={styles.hint}>Enter the dosage amount per administration</span>
          </div>

          {/* Frequency */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Frequency</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className={errors.frequency ? styles.inputError : ''}
              disabled={isSubmitting}
            >
              <option value="">-- Select frequency --</option>
              {FREQUENCY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
              <option value="Custom">Custom (enter below)</option>
            </select>
            {errors.frequency && <span className={styles.error}>{errors.frequency}</span>}

            {frequency === 'Custom' && (
              <input
                type="text"
                value={customFrequency}
                onChange={(e) => setCustomFrequency(e.target.value)}
                placeholder="Enter custom frequency"
                className={styles.customInput}
                disabled={isSubmitting}
              />
            )}
          </div>

          {/* Duration */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Duration</label>
            <input
              type="text"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="e.g., 7 days, 2 weeks, Until symptoms resolve"
              className={errors.duration ? styles.inputError : ''}
              disabled={isSubmitting}
            />
            {errors.duration && <span className={styles.error}>{errors.duration}</span>}
            <span className={styles.hint}>How long should the patient take this medication?</span>
          </div>

          {/* Instructions */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Instructions</label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Take with food, Take on empty stomach, Avoid alcohol"
              rows={3}
              className={errors.instructions ? styles.inputError : ''}
              disabled={isSubmitting}
            />
            {errors.instructions && <span className={styles.error}>{errors.instructions}</span>}
            <span className={styles.hint}>Provide clear instructions for the patient</span>
          </div>

          {/* Quantity (Optional) */}
          <div className={styles.formGroup}>
            <label>Quantity (Optional)</label>
            <input
              type="text"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="e.g., 20 tablets, 100ml"
              disabled={isSubmitting}
            />
            <span className={styles.hint}>Total amount to dispense</span>
          </div>

          {/* Form Actions */}
          <div className={styles.formActions}>
            <button
              type="button"
              onClick={onCancel}
              className={styles.cancelButton}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Prescribing...' : '✓ Prescribe Medication'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

