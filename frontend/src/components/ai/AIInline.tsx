/**
 * AI Features Inline Component
 * 
 * Provides AI features in a collapsible panel for the consultation workspace
 */
import React, { useState, useEffect } from 'react';
import ClinicalDecisionSupport from './ClinicalDecisionSupport';
import NLPSummarization from './NLPSummarization';
import AutomatedCoding from './AutomatedCoding';
import DrugInteractionCheck from './DrugInteractionCheck';
import { usePrescriptions } from '../../hooks/usePrescriptions';
import styles from '../../styles/AIComponents.module.css';

interface AIInlineProps {
  visitId: string;
  consultationId?: number;
  consultationData?: {
    history?: string;
    examination?: string;
    diagnosis?: string;
    clinical_notes?: string;
  };
}

const AIInline: React.FC<AIInlineProps> = ({
  visitId,
  consultationId,
  consultationData,
}) => {
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const { prescriptions } = usePrescriptions(visitId);
  
  // Extract current medications from prescriptions
  const currentMedications = prescriptions
    .filter(p => p.status === 'DISPENSED' || p.status === 'PENDING')
    .map(p => p.drug);

  const tabs = [
    { id: 'decision-support', label: 'Clinical Decision Support', icon: '🧠' },
    { id: 'summarization', label: 'NLP Summarization', icon: '📝' },
    { id: 'coding', label: 'Automated Coding', icon: '🏷️' },
    { id: 'interactions', label: 'Drug Interactions', icon: '💊' },
  ];

  return (
    <div className={styles.aiInline}>
      <div className={styles.aiHeader}>
        <h3>AI-Powered Features</h3>
        <p className={styles.aiSubtitle}>
          Get AI assistance for clinical decision-making
        </p>
      </div>

      <div className={styles.aiTabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(activeTab === tab.id ? null : tab.id)}
            className={`${styles.aiTab} ${activeTab === tab.id ? styles.active : ''}`}
          >
            <span className={styles.tabIcon}>{tab.icon}</span>
            <span className={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className={styles.aiContent}>
        {activeTab === 'decision-support' && (
          <ClinicalDecisionSupport
            visitId={visitId}
            consultationId={consultationId}
            patientSymptoms={consultationData?.examination}
            patientHistory={consultationData?.history}
            currentMedications={currentMedications}
          />
        )}

        {activeTab === 'summarization' && (
          <NLPSummarization
            visitId={visitId}
            consultationId={consultationId}
            text={
              consultationData
                ? `${consultationData.history || ''}\n${consultationData.examination || ''}\n${consultationData.diagnosis || ''}\n${consultationData.clinical_notes || ''}`
                : undefined
            }
          />
        )}

        {activeTab === 'coding' && consultationId && (
          <AutomatedCoding
            visitId={visitId}
            consultationId={consultationId}
            onCodesApplied={() => {
              // Trigger reload of consultation to show updated codes
              // This will be handled by parent component
            }}
          />
        )}

        {activeTab === 'interactions' && (
          <DrugInteractionCheck
            visitId={visitId}
            currentMedications={currentMedications}
          />
        )}

        {activeTab === 'coding' && !consultationId && (
          <div className={styles.aiMessage}>
            Please create a consultation first to generate medical codes.
          </div>
        )}
      </div>
    </div>
  );
};

export default AIInline;
