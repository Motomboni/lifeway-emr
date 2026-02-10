/**
 * LabOrderDetailsForm Component
 * 
 * Modal form for doctors to enter lab order details when ordering laboratory services.
 * Used from Service Catalog (with serviceName) and from Lab section (with optional initial values).
 * 
 * Fields:
 * - Tests Requested (required, list of tests to be performed)
 * - Clinical Indication (optional, reason for the tests)
 */
import React, { useState, useEffect } from 'react';
import styles from '../pharmacy/PrescriptionDetailsForm.module.css';

interface LabOrderDetailsFormProps {
  /** When ordering from catalog, the selected service name; when from Lab section, e.g. "Lab tests" or omit subtitle */
  serviceName?: string;
  /** Pre-fill tests (e.g. from template); one item per line in the textarea */
  initialTests?: string[];
  /** Pre-fill clinical indication */
  initialClinicalIndication?: string;
  onSubmit: (labOrderDetails: LabOrderDetails) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export interface LabOrderDetails {
  tests_requested: string[];
  clinical_indication?: string;
}

export default function LabOrderDetailsForm({
  serviceName = 'Lab tests',
  initialTests,
  initialClinicalIndication,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: LabOrderDetailsFormProps) {
  const [testsText, setTestsText] = useState(() =>
    initialTests?.length
      ? initialTests.join('\n')
      : serviceName && serviceName !== 'Lab tests'
        ? serviceName
        : ''
  );
  const [clinicalIndication, setClinicalIndication] = useState(initialClinicalIndication ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Sync when parent passes new initial values (e.g. after selecting a template)
  useEffect(() => {
    if (initialTests?.length) setTestsText(initialTests.join('\n'));
    if (initialClinicalIndication !== undefined) setClinicalIndication(initialClinicalIndication);
  }, [initialTests, initialClinicalIndication]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!testsText.trim()) {
      newErrors.tests = 'At least one test must be specified';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    // Parse tests from textarea (one per line or comma-separated)
    const tests = testsText
      .split(/[\n,]/)
      .map(test => test.trim())
      .filter(test => test.length > 0);

    onSubmit({
      tests_requested: tests,
      clinical_indication: clinicalIndication.trim() || undefined,
    });
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3>🔬 Lab Order Details</h3>
          {serviceName && <p className={styles.drugName}>{serviceName}</p>}
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* Tests Requested */}
          <div className={styles.formGroup}>
            <label className={styles.required}>Tests Requested</label>
            <textarea
              value={testsText}
              onChange={(e) => setTestsText(e.target.value)}
              placeholder="Enter tests (one per line or comma-separated)&#10;e.g.,&#10;Complete Blood Count&#10;Blood Sugar (Fasting)&#10;Malaria Parasite"
              rows={5}
              className={errors.tests ? styles.inputError : ''}
              disabled={isSubmitting}
            />
            {errors.tests && <span className={styles.error}>{errors.tests}</span>}
            <span className={styles.hint}>List the specific tests to be performed</span>
          </div>

          {/* Clinical Indication */}
          <div className={styles.formGroup}>
            <label>Clinical Indication (Optional)</label>
            <textarea
              value={clinicalIndication}
              onChange={(e) => setClinicalIndication(e.target.value)}
              placeholder="e.g., Suspected malaria, Follow-up for diabetes, Pre-operative screening"
              rows={3}
              disabled={isSubmitting}
            />
            <span className={styles.hint}>Reason for ordering these tests</span>
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
              {isSubmitting ? 'Ordering...' : '✓ Order Lab Tests'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

