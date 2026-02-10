/**
 * RadiologyOrderDetailsForm Component
 *
 * Modal form for doctors to enter radiology order details when ordering from the Service Catalog.
 * Used at: Consultation Page → Service Catalog → select service with workflow_type = RADIOLOGY_STUDY.
 *
 * Submitting this form creates a RadiologyRequest (not RadiologyOrder) and a BillingLineItem.
 * System-controlled fields (not exposed in UI): visit_id, consultation_id, ordered_by, status, study_code.
 *
 * Doctor-facing fields:
 * - Study Type (required) → RadiologyRequest.study_type; pre-filled with Service Catalog item name.
 * - Clinical Indication (optional) → RadiologyRequest.clinical_indication (maps to Provisional Diagnosis / Clinical Notes).
 * - Special Instructions (optional) → RadiologyRequest.instructions (maps to Instructions to Radiographer).
 */
import React, { useState } from 'react';
import styles from '../pharmacy/PrescriptionDetailsForm.module.css';

interface RadiologyOrderDetailsFormProps {
  serviceName: string;
  onSubmit: (radiologyOrderDetails: RadiologyOrderDetails) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

/** Standard film/format sizes (cm) for X-ray imaging. */
export const FILM_FORMAT_SIZES = [
  '35 x 43cm',
  '35 x 35cm',
  '30 x 40cm',
  '24 x 30cm',
  '18 x 24cm',
  '20 x 40cm',
  '13 x 18cm',
] as const;

/** Patient / equipment location options for imaging (mobility, transfer, or equipment type). */
export const PATIENT_LOCATION_OPTIONS = [
  'WALKING',
  'CHAIR',
  'TROLLEY',
  'PORTABLE',
  'THEATRE',
] as const;

/** View / projection type options (e.g. occlusal, dental). */
export const VIEW_TYPE_OPTIONS = [
  'OCCLUSAL',
  'DENTAL',
] as const;

export interface RadiologyOrderDetails {
  study_type: string;
  clinical_indication?: string;
  instructions?: string;
  film_size?: string;
  patient_location?: string;
  view_type?: string;
}

export default function RadiologyOrderDetailsForm({
  serviceName,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: RadiologyOrderDetailsFormProps) {
  const [studyType, setStudyType] = useState(serviceName); // Pre-fill with service name
  const [clinicalIndication, setClinicalIndication] = useState('');
  const [instructions, setInstructions] = useState('');
  const [filmSize, setFilmSize] = useState<string>('');
  const [patientLocation, setPatientLocation] = useState<string>('');
  const [viewType, setViewType] = useState<string>('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!studyType.trim()) {
      newErrors.studyType = 'Study type is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    onSubmit({
      study_type: studyType.trim(),
      clinical_indication: clinicalIndication.trim() || undefined,
      instructions: instructions.trim() || undefined,
      film_size: filmSize.trim() || undefined,
      patient_location: patientLocation.trim() || undefined,
      view_type: viewType.trim() || undefined,
    });
  };

  return (
    <div className={styles.modalOverlay} data-testid="radiology-order-details-modal">
      <div className={styles.modalContent} style={{ overflowY: 'auto', maxHeight: '90vh' }}>
        <div className={styles.modalHeader}>
          <h3>🔬 Radiology Order Details</h3>
          <p className={styles.drugName}>{serviceName}</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form} style={{ paddingBottom: 24 }}>
          {/* Study Type */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Study Type</label>
            <input
              type="text"
              value={studyType}
              onChange={(e) => setStudyType(e.target.value)}
              placeholder="e.g., Chest X-Ray PA, CT Scan Head, Ultrasound Abdomen"
              className={errors.studyType ? styles.inputError : ''}
              disabled={isSubmitting}
            />
            {errors.studyType && <span className={styles.error}>{errors.studyType}</span>}
            <span className={styles.hint}>Type of imaging study to be performed</span>
          </div>

          {/* Film/Format size (optional) */}
          <div className={styles.formGroup}>
            <label>Film/Format size (Optional)</label>
            <select
              value={filmSize}
              onChange={(e) => setFilmSize(e.target.value)}
              disabled={isSubmitting}
              className={styles.input}
            >
              <option value="">— Select size —</option>
              {FILM_FORMAT_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
            <span className={styles.hint}>Standard film/format size for X-ray imaging</span>
          </div>

          {/* Patient / Equipment (optional) */}
          <div className={styles.formGroup}>
            <label>Patient / Equipment (Optional)</label>
            <select
              value={patientLocation}
              onChange={(e) => setPatientLocation(e.target.value)}
              disabled={isSubmitting}
              className={styles.input}
            >
              <option value="">— Select —</option>
              {PATIENT_LOCATION_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span className={styles.hint}>Walking, chair, trolley, portable, or theatre</span>
          </div>

          {/* View / Projection (optional) — OCCLUSAL, DENTAL */}
          <div className={styles.formGroup}>
            <label>View / Projection (Optional)</label>
            <select
              value={viewType}
              onChange={(e) => setViewType(e.target.value)}
              disabled={isSubmitting}
              className={styles.input}
            >
              <option value="">— Select —</option>
              {VIEW_TYPE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span className={styles.hint}>Occlusal or dental view</span>
          </div>

          {/* Clinical Indication → RadiologyRequest.clinical_indication (Provisional Diagnosis / Clinical Notes) */}
          <div className={styles.formGroup}>
            <label>Clinical Indication (Optional)</label>
            <textarea
              value={clinicalIndication}
              onChange={(e) => setClinicalIndication(e.target.value)}
              placeholder="e.g., Suspected pneumonia, Follow-up for fracture, Abdominal pain (Provisional diagnosis / clinical notes)"
              rows={3}
              disabled={isSubmitting}
            />
            <span className={styles.hint}>Provisional diagnosis / clinical notes. Reason for ordering this imaging study.</span>
          </div>

          {/* Special Instructions → RadiologyRequest.instructions (Instructions to Radiographer) */}
          <div className={styles.formGroup}>
            <label>Special Instructions (Optional)</label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Focus on right lower lobe, Compare with previous study, Patient has metal implant"
              rows={3}
              disabled={isSubmitting}
            />
            <span className={styles.hint}>Instructions to radiographer.</span>
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
              {isSubmitting ? 'Ordering...' : '✓ Order Imaging Study'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

