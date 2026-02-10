/**
 * Drug Interaction Check Component
 * 
 * Checks for drug interactions using AI
 */
import React, { useState } from 'react';
import { checkDrugInteractions } from '../../api/ai';
import { useToast } from '../../hooks/useToast';
import LoadingSpinner from '../common/LoadingSpinner';
import type { DrugInteractionCheckRequest, DrugInteractionCheckResponse } from '../../types/ai';
import styles from '../../styles/AIComponents.module.css';

interface DrugInteractionCheckProps {
  visitId: string;
  currentMedications?: string[];
  onResult?: (result: DrugInteractionCheckResponse) => void;
}

const DrugInteractionCheck: React.FC<DrugInteractionCheckProps> = ({
  visitId,
  currentMedications = [],
  onResult,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DrugInteractionCheckResponse | null>(null);
  const [newMedication, setNewMedication] = useState('');
  const [medications, setMedications] = useState<string[]>(currentMedications);
  const [newMedInput, setNewMedInput] = useState('');
  const { showSuccess, showError } = useToast();

  const handleAddMedication = () => {
    if (newMedInput.trim()) {
      setMedications([...medications, newMedInput.trim()]);
      setNewMedInput('');
    }
  };

  const handleRemoveMedication = (index: number) => {
    setMedications(medications.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!newMedication.trim()) {
      showError('Please enter a medication to check');
      return;
    }

    if (medications.length === 0) {
      showError('Please add at least one current medication');
      return;
    }

    setLoading(true);
    try {
      const request: DrugInteractionCheckRequest = {
        current_medications: medications,
        new_medication: newMedication.trim(),
      };

      const response = await checkDrugInteractions(visitId, request);
      setResult(response);
      if (onResult) {
        onResult(response);
      }
      showSuccess('Drug interaction check completed');
    } catch (error: any) {
      showError(error.message || 'Failed to check drug interactions');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.aiComponent}>
      <div className={styles.aiHeader}>
        <h3>Drug Interaction Check</h3>
        <p className={styles.aiDescription}>
          Check for potential drug interactions
        </p>
      </div>

      <div className={styles.drugInputSection}>
        <div className={styles.inputGroup}>
          <label>Current Medications:</label>
          <div className={styles.medicationList}>
            {medications.map((med, idx) => (
              <div key={idx} className={styles.medicationTag}>
                {med}
                <button
                  type="button"
                  onClick={() => handleRemoveMedication(idx)}
                  className={styles.removeButton}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className={styles.addMedication}>
            <input
              type="text"
              value={newMedInput}
              onChange={(e) => setNewMedInput(e.target.value)}
              placeholder="Add medication"
              onKeyPress={(e) => e.key === 'Enter' && handleAddMedication()}
            />
            <button type="button" onClick={handleAddMedication}>
              Add
            </button>
          </div>
        </div>

        <div className={styles.inputGroup}>
          <label>New Medication to Check:</label>
          <input
            type="text"
            value={newMedication}
            onChange={(e) => setNewMedication(e.target.value)}
            placeholder="Enter medication name"
          />
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={styles.aiButton}
      >
        {loading ? <LoadingSpinner /> : 'Check Interactions'}
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
              <div className={styles.resultSection}>
                <div className={result.has_interaction ? styles.interactionWarning : styles.noInteraction}>
                  <h4>
                    {result.has_interaction ? '⚠️ Interaction Detected' : '✓ No Interaction'}
                  </h4>
                  {result.severity && (
                    <span className={`${styles.severity} ${styles[result.severity]}`}>
                      Severity: {result.severity.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>

              {result.description && (
                <div className={styles.resultSection}>
                  <h4>Description</h4>
                  <p>{result.description}</p>
                </div>
              )}

              {result.recommendations && result.recommendations.length > 0 && (
                <div className={styles.resultSection}>
                  <h4>Recommendations</h4>
                  <ul>
                    {result.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
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

export default DrugInteractionCheck;
