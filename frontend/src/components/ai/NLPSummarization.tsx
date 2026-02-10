/**
 * NLP Summarization Component
 * 
 * Summarizes clinical notes using AI
 */
import React, { useState } from 'react';
import { summarizeClinicalNotes } from '../../api/ai';
import { useToast } from '../../hooks/useToast';
import LoadingSpinner from '../common/LoadingSpinner';
import type { NLPSummarizationRequest, NLPSummarizationResponse } from '../../types/ai';
import styles from '../../styles/AIComponents.module.css';

interface NLPSummarizationProps {
  visitId: string;
  consultationId?: number;
  text?: string;
  onResult?: (result: NLPSummarizationResponse) => void;
}

const NLPSummarization: React.FC<NLPSummarizationProps> = ({
  visitId,
  consultationId,
  text,
  onResult,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NLPSummarizationResponse | null>(null);
  const [summaryType, setSummaryType] = useState<'brief' | 'detailed' | 'structured'>('brief');
  const { showSuccess, showError } = useToast();

  const handleSubmit = async () => {
    if (!consultationId && !text) {
      showError('Please provide consultation ID or text to summarize');
      return;
    }

    setLoading(true);
    try {
      const request: NLPSummarizationRequest = {
        consultation_id: consultationId,
        text: text,
        summary_type: summaryType,
      };

      const response = await summarizeClinicalNotes(visitId, request);
      setResult(response);
      if (onResult) {
        onResult(response);
      }
      showSuccess('Summary generated successfully');
    } catch (error: any) {
      showError(error.message || 'Failed to generate summary');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.aiComponent}>
      <div className={styles.aiHeader}>
        <h3>NLP Summarization</h3>
        <p className={styles.aiDescription}>
          Summarize clinical notes using AI-powered natural language processing
        </p>
      </div>

      <div className={styles.aiOptions}>
        <label>
          Summary Type:
          <select
            value={summaryType}
            onChange={(e) => setSummaryType(e.target.value as any)}
            className={styles.select}
          >
            <option value="brief">Brief</option>
            <option value="detailed">Detailed</option>
            <option value="structured">Structured</option>
          </select>
        </label>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={styles.aiButton}
      >
        {loading ? <LoadingSpinner /> : 'Generate Summary'}
      </button>

      {result && (
        <div className={styles.aiResult}>
          <div className={styles.resultSection}>
            <h4>Summary</h4>
            <p className={styles.summaryText}>{result.summary}</p>
          </div>

          {result.key_points && result.key_points.length > 0 && (
            <div className={styles.resultSection}>
              <h4>Key Points</h4>
              <ul>
                {result.key_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NLPSummarization;
