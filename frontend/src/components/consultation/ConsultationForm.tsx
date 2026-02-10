/**
 * ConsultationForm Component
 * 
 * Main form containing all consultation sections:
 * - History
 * - Examination
 * - Diagnosis
 * - Clinical Notes
 * 
 * All fields are editable and visit-scoped.
 */
import React, { useState, useEffect } from 'react';
import HistorySection from './sections/HistorySection';
import ExaminationSection from './sections/ExaminationSection';
import DiagnosisSection from './sections/DiagnosisSection';
import ClinicalNotesSection from './sections/ClinicalNotesSection';
import { ConsultationData } from '../../types/consultation';
import { fetchClinicalTemplates, applyClinicalTemplate } from '../../api/clinical';
import { ClinicalTemplate } from '../../types/clinical';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ConsultationFormProps {
  formData: ConsultationData;
  onFieldChange: (field: keyof ConsultationData, value: string) => void;
}

export default function ConsultationForm({
  formData,
  onFieldChange
}: ConsultationFormProps) {
  const { showSuccess, showError } = useToast();
  const [templates, setTemplates] = useState<ClinicalTemplate[]>([]);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const data = await fetchClinicalTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleUseTemplate = async (templateId: number) => {
    try {
      const templateData = await applyClinicalTemplate(templateId);
      onFieldChange('history', templateData.history || formData.history);
      onFieldChange('examination', templateData.examination || formData.examination);
      onFieldChange('diagnosis', templateData.diagnosis || formData.diagnosis);
      onFieldChange('clinical_notes', templateData.clinical_notes || formData.clinical_notes);
      setShowTemplateSelector(false);
      showSuccess('Template applied successfully');
    } catch (error: any) {
      showError(error.message || 'Failed to use template');
    }
  };

  return (
    <div className={styles.consultationForm}>
      <div className={styles.formHeader}>
        <h2>Consultation</h2>
        {templates.length > 0 && (
          <button
            type="button"
            className={styles.templateButton}
            onClick={() => setShowTemplateSelector(!showTemplateSelector)}
          >
            📋 Use Template
          </button>
        )}
      </div>

      {showTemplateSelector && (
        <div className={styles.templateSelector}>
          <h4>Select Template</h4>
          {loadingTemplates ? (
            <p>Loading templates...</p>
          ) : templates.length === 0 ? (
            <p>No templates available</p>
          ) : (
            <div className={styles.templateList}>
              {templates.map((template) => (
                <div
                  key={template.id}
                  className={styles.templateItem}
                  onClick={() => handleUseTemplate(template.id)}
                >
                  <strong>{template.name}</strong>
                  <span className={styles.templateCategory}>{template.category}</span>
                  {template.description && (
                    <p className={styles.templateDescription}>{template.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <button
            type="button"
            className={styles.closeButton}
            onClick={() => setShowTemplateSelector(false)}
          >
            Close
          </button>
        </div>
      )}

      <HistorySection
        value={formData.history}
        onChange={(value) => onFieldChange('history', value)}
      />
      
      <ExaminationSection
        value={formData.examination}
        onChange={(value) => onFieldChange('examination', value)}
      />
      
      <DiagnosisSection
        value={formData.diagnosis}
        onChange={(value) => onFieldChange('diagnosis', value)}
      />
      
      <ClinicalNotesSection
        value={formData.clinical_notes}
        onChange={(value) => onFieldChange('clinical_notes', value)}
      />
    </div>
  );
}
