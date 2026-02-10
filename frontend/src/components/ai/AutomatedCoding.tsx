/**
 * Automated Coding Component
 * 
 * Generates ICD-11 and CPT codes from clinical notes
 */
import React, { useState } from 'react';
import { generateMedicalCodes } from '../../api/ai';
import { applyAIDiagnosisCodes } from '../../api/diagnosisCodes';
import { useToast } from '../../hooks/useToast';
import LoadingSpinner from '../common/LoadingSpinner';
import type { AutomatedCodingRequest, AutomatedCodingResponse } from '../../types/ai';
import styles from '../../styles/AIComponents.module.css';

interface AutomatedCodingProps {
  visitId: string;
  consultationId: number;
  onResult?: (result: AutomatedCodingResponse) => void;
  onCodesApplied?: () => void;
}

const AutomatedCoding: React.FC<AutomatedCodingProps> = ({
  visitId,
  consultationId,
  onResult,
  onCodesApplied,
}) => {
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState<AutomatedCodingResponse | null>(null);
  const [codeTypes, setCodeTypes] = useState<('icd11' | 'cpt')[]>(['icd11']);
  const { showSuccess, showError } = useToast();

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const request: AutomatedCodingRequest = {
        consultation_id: consultationId,
        code_types: codeTypes,
      };

      const response = await generateMedicalCodes(visitId, request);
      setResult(response);
      if (onResult) {
        onResult(response);
      }
      showSuccess('Medical codes generated successfully');
    } catch (error: any) {
      showError(error.message || 'Failed to generate medical codes');
    } finally {
      setLoading(false);
    }
  };

  const toggleCodeType = (type: 'icd11' | 'cpt') => {
    if (codeTypes.includes(type)) {
      if (codeTypes.length > 1) {
        setCodeTypes(codeTypes.filter(t => t !== type));
      }
    } else {
      setCodeTypes([...codeTypes, type]);
    }
  };

  return (
    <div className={styles.aiComponent}>
      <div className={styles.aiHeader}>
        <h3>Automated Medical Coding</h3>
        <p className={styles.aiDescription}>
          Generate ICD-11 and CPT codes from clinical notes
        </p>
      </div>

      <div className={styles.aiOptions}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={codeTypes.includes('icd11')}
            onChange={() => toggleCodeType('icd11')}
            disabled={codeTypes.length === 1 && codeTypes.includes('icd11')}
          />
          ICD-11 Codes
        </label>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={codeTypes.includes('cpt')}
            onChange={() => toggleCodeType('cpt')}
            disabled={codeTypes.length === 1 && codeTypes.includes('cpt')}
          />
          CPT Codes
        </label>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={styles.aiButton}
      >
        {loading ? <LoadingSpinner /> : 'Generate Codes'}
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
              {result.icd11_codes && result.icd11_codes.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>ICD-11 Codes</h4>
                  <ul className={styles.codeList}>
                    {result.icd11_codes.map((code, idx) => (
                      <li key={idx} className={styles.codeItem}>
                        <strong>{code.code}</strong> - {code.description}
                        {code.confidence && (
                          <span className={styles.confidence}>
                            ({Math.round(code.confidence * 100)}% confidence)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={async () => {
                      if (!result.icd11_codes || result.icd11_codes.length === 0) {
                        showError('No ICD-11 codes to apply');
                        return;
                      }
                      setApplying(true);
                      try {
                        await applyAIDiagnosisCodes(visitId, {
                          icd11_codes: result.icd11_codes.map(c => ({
                            code: c.code,
                            description: c.description,
                            confidence: c.confidence,
                          })),
                          set_primary: true,
                        });
                        showSuccess('ICD-11 codes applied to consultation');
                        if (onCodesApplied) {
                          onCodesApplied();
                        }
                      } catch (error: any) {
                        showError(error.message || 'Failed to apply codes');
                      } finally {
                        setApplying(false);
                      }
                    }}
                    disabled={applying || !result.icd11_codes || result.icd11_codes.length === 0}
                    className={styles.aiButton}
                    style={{ marginTop: '1rem' }}
                  >
                    {applying ? <LoadingSpinner /> : 'Apply Codes to Consultation'}
                  </button>
                </div>
              )}

              {result.cpt_codes && result.cpt_codes.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>CPT Codes</h4>
                  <ul className={styles.codeList}>
                    {result.cpt_codes.map((code, idx) => (
                      <li key={idx} className={styles.codeItem}>
                        <strong>{code.code}</strong> - {code.description}
                        {code.confidence && (
                          <span className={styles.confidence}>
                            ({Math.round(code.confidence * 100)}% confidence)
                          </span>
                        )}
                      </li>
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

export default AutomatedCoding;
