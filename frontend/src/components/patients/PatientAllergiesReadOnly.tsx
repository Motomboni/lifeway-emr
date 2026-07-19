/**
 * Read-only structured allergy list for patient portal and profile views.
 */
import React from 'react';
import type { StructuredAllergySummary } from '../../api/patientAllergies';
import styles from '../../styles/PatientPortal.module.css';

interface PatientAllergiesReadOnlyProps {
  structuredAllergies?: StructuredAllergySummary[];
  allergiesSummary?: string;
}

export default function PatientAllergiesReadOnly({
  structuredAllergies = [],
  allergiesSummary,
}: PatientAllergiesReadOnlyProps) {
  const active = structuredAllergies.filter((a) => a.allergen?.trim());

  if (active.length === 0 && !allergiesSummary?.trim()) {
    return <p className={styles.emptyText}>No allergies documented.</p>;
  }

  if (active.length === 0) {
    return (
      <div className={styles.infoRow}>
        <strong>Allergies:</strong> {allergiesSummary}
      </div>
    );
  }

  return (
    <div className={styles.allergyReadOnlyList}>
      {active.map((a) => (
        <div key={a.id} className={styles.allergyReadOnlyItem}>
          <strong>{a.allergen}</strong>
          {a.severity && a.severity !== 'UNKNOWN' && (
            <span className={styles.allergyTag}>{a.severity}</span>
          )}
          {a.reaction && <span> — {a.reaction}</span>}
        </div>
      ))}
    </div>
  );
}
