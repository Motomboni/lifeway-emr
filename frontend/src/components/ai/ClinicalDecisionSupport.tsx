/**
 * Clinical Decision Support Component
 * 
 * Provides AI-powered diagnosis suggestions and treatment recommendations
 */
import React, { useState } from 'react';
import { getClinicalDecisionSupport } from '../../api/ai';
import { useToast } from '../../hooks/useToast';
import LoadingSpinner from '../common/LoadingSpinner';
import type { ClinicalDecisionSupportRequest, ClinicalDecisionSupportResponse } from '../../types/ai';
import styles from '../../styles/AIComponents.module.css';

interface ClinicalDecisionSupportProps {
  visitId: string;
  consultationId?: number;
  patientSymptoms?: string;
  patientHistory?: string;
  currentMedications?: string[];
  onResult?: (result: ClinicalDecisionSupportResponse) => void;
}

const ClinicalDecisionSupport: React.FC<ClinicalDecisionSupportProps> = ({
  visitId,
  consultationId,
  patientSymptoms,
  patientHistory,
  currentMedications,
  onResult,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClinicalDecisionSupportResponse | null>(null);
  const [includeDifferential, setIncludeDifferential] = useState(true);
  const [includeTreatment, setIncludeTreatment] = useState(true);
  const { showSuccess, showError } = useToast();

  const handleSubmit = async () => {
    if (!consultationId && !patientSymptoms && !patientHistory) {
      showError('Please provide consultation ID, symptoms, or patient history');
      return;
    }

    setLoading(true);
    try {
      const request: ClinicalDecisionSupportRequest = {
        consultation_id: consultationId,
        patient_symptoms: patientSymptoms,
        patient_history: patientHistory,
        current_medications: currentMedications,
        include_differential_diagnosis: includeDifferential,
        include_treatment_suggestions: includeTreatment,
      };

      const response = await getClinicalDecisionSupport(visitId, request);
      setResult(response);
      if (onResult) {
        onResult(response);
      }
      showSuccess('Clinical decision support generated successfully');
    } catch (error: any) {
      showError(error.message || 'Failed to generate clinical decision support');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.aiComponent}>
      <div className={styles.aiHeader}>
        <h3>Clinical Decision Support</h3>
        <p className={styles.aiDescription}>
          Get AI-powered diagnosis suggestions and treatment recommendations
        </p>
      </div>

      <div className={styles.aiOptions}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={includeDifferential}
            onChange={(e) => setIncludeDifferential(e.target.checked)}
          />
          Include differential diagnosis
        </label>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={includeTreatment}
            onChange={(e) => setIncludeTreatment(e.target.checked)}
          />
          Include treatment suggestions
        </label>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={styles.aiButton}
      >
        {loading ? <LoadingSpinner /> : 'Generate Suggestions'}
      </button>

      {result && (
        <div className={styles.aiResult}>
          {result.raw_response ? (
            <div className={styles.rawResponse}>
              <h4>AI Response:</h4>
              <pre>{result.raw_response}</pre>
            </div>
          ) : (
            <>
              {result.suggested_diagnoses && result.suggested_diagnoses.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>Suggested Diagnoses</h4>
                  <ul>
                    {result.suggested_diagnoses.map((diagnosis, idx) => (
                      <li key={idx}>
                        <strong>{diagnosis.diagnosis}</strong>
                        {diagnosis.confidence && (
                          <span className={styles.confidence}>
                            ({Math.round(diagnosis.confidence * 100)}% confidence)
                          </span>
                        )}
                        {diagnosis.icd11_code && (
                          <span className={styles.code}>ICD-11: {diagnosis.icd11_code}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.differential_diagnosis && result.differential_diagnosis.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>Differential Diagnosis</h4>
                  <ul>
                    {result.differential_diagnosis.map((diagnosis, idx) => (
                      <li key={idx}>
                        <strong>{diagnosis.diagnosis}</strong>
                        {diagnosis.confidence && (
                          <span className={styles.confidence}>
                            ({Math.round(diagnosis.confidence * 100)}% confidence)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.treatment_suggestions && result.treatment_suggestions.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>Treatment Suggestions</h4>
                  <ul>
                    {result.treatment_suggestions.map((treatment, idx) => (
                      <li key={idx}>
                        <strong>{treatment.treatment}</strong>
                        {treatment.rationale && <p>{treatment.rationale}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.warnings && result.warnings.length > 0 && (
                <div className={styles.warnings}>
                  <h4>Warnings</h4>
                  <ul>
                    {result.warnings.map((warning, idx) => (
                      <li key={idx} className={styles.warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ClinicalDecisionSupport;
