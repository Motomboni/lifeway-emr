/**
 * Prominent allergy banner for clinical contexts (consultation, visit details).
 */
import React, { useEffect, useState } from 'react';
import {
  fetchPatientAllergies,
  type PatientAllergy,
  type StructuredAllergySummary,
} from '../../api/patientAllergies';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface PatientAllergyBannerProps {
  allergies?: StructuredAllergySummary[];
  allergiesText?: string;
  compact?: boolean;
}

function severityClass(severity: string): string {
  switch (severity) {
    case 'SEVERE':
      return styles.allergyBannerSevere;
    case 'MODERATE':
      return styles.allergyBannerModerate;
    default:
      return styles.allergyBannerMild;
  }
}

export default function PatientAllergyBanner({
  allergies = [],
  allergiesText,
  compact = false,
}: PatientAllergyBannerProps) {
  const active = allergies.filter((a) => a.allergen?.trim());
  const hasLegacyOnly = active.length === 0 && !!(allergiesText || '').trim();

  if (active.length === 0 && !hasLegacyOnly) {
    return null;
  }

  if (hasLegacyOnly) {
    return (
      <div
        className={`${styles.allergyBanner} ${styles.allergyBannerModerate}`}
        role="alert"
        data-guide-id="patient-allergies"
      >
        <strong>⚠ Allergies:</strong>{' '}
        <span>{allergiesText}</span>
        {!compact && (
          <span className={styles.allergyBannerHint}>
            {' '}
            (legacy free-text — consider documenting structured allergies)
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={styles.allergyBannerGroup} role="alert" data-guide-id="patient-allergies">
      <div className={styles.allergyBannerTitle}>⚠ Documented allergies</div>
      <ul className={styles.allergyBannerList}>
        {active.map((a) => (
          <li
            key={a.id}
            className={`${styles.allergyBannerItem} ${severityClass(a.severity)}`}
          >
            <strong>{a.allergen}</strong>
            {a.severity && a.severity !== 'UNKNOWN' && (
              <span className={styles.allergySeverityTag}>{a.severity}</span>
            )}
            {a.allergen_type && a.allergen_type !== 'UNKNOWN' && (
              <span className={styles.allergyTypeTag}>{a.allergen_type}</span>
            )}
            {a.reaction && !compact && (
              <span className={styles.allergyReaction}> — {a.reaction}</span>
            )}
            {a.verified && <span className={styles.allergyVerifiedTag}>verified</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Fetches structured allergies when only patientId is available (e.g. visit details). */
export function PatientAllergyBannerForPatient({
  patientId,
  allergiesText,
}: {
  patientId: number;
  allergiesText?: string;
}) {
  const [allergies, setAllergies] = useState<StructuredAllergySummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchPatientAllergies(patientId)
      .then((rows: PatientAllergy[]) => {
        if (!cancelled) {
          setAllergies(
            rows.map((r) => ({
              id: r.id,
              allergen: r.allergen,
              allergen_type: r.allergen_type,
              severity: r.severity,
              reaction: r.reaction,
              verified: r.verified,
            })),
          );
        }
      })
      .catch(() => {
        if (!cancelled) setAllergies([]);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  return (
    <PatientAllergyBanner allergies={allergies} allergiesText={allergiesText} />
  );
}
