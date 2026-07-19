/**
 * ConsultationForm Component
 */
import React, { useEffect, useRef, useState } from 'react';
import HistorySection from './sections/HistorySection';
import ExaminationSection from './sections/ExaminationSection';
import DiagnosisSection from './sections/DiagnosisSection';
import ClinicalNotesSection from './sections/ClinicalNotesSection';
import { ConsultationData } from '../../types/consultation';
import { fetchClinicalTemplates, applyClinicalTemplate } from '../../api/clinical';
import { ClinicalTemplate } from '../../types/clinical';
import { CONSULTATION_MACROS } from '../../data/consultationMacros';
import { pickDefaultClinicalTemplate } from '../../utils/clinicalTemplatePick';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ConsultationFormProps {
  formData: ConsultationData;
  onFieldChange: (field: keyof ConsultationData, value: string) => void;
  onApplyFormPatch: (patch: Partial<ConsultationData>) => void;
  visitId?: string;
  isNewConsultation?: boolean;
  visitType?: string;
}

function isFormEmpty(formData: ConsultationData): boolean {
  return (
    !formData.history?.trim() &&
    !formData.examination?.trim() &&
    !formData.diagnosis?.trim() &&
    !formData.clinical_notes?.trim()
  );
}

export default function ConsultationForm({
  formData,
  onFieldChange,
  onApplyFormPatch,
  visitId,
  isNewConsultation = false,
  visitType,
}: ConsultationFormProps) {
  const { showSuccess, showError } = useToast();
  const [templates, setTemplates] = useState<ClinicalTemplate[]>([]);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const defaultTemplateAttempted = useRef(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    defaultTemplateAttempted.current = false;
  }, [visitId]);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const data = await fetchClinicalTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const applyTemplateById = async (templateId: number, silent = false) => {
    try {
      const templateData = await applyClinicalTemplate(templateId);
      onApplyFormPatch({
        history: templateData.history || formData.history,
        examination: templateData.examination || formData.examination,
        diagnosis: templateData.diagnosis || formData.diagnosis,
        clinical_notes: templateData.clinical_notes || formData.clinical_notes,
      });
      setShowTemplateSelector(false);
      if (!silent) {
        showSuccess('Template applied successfully');
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to use template';
      showError(message);
    }
  };

  const handleUseTemplate = (templateId: number) => {
    void applyTemplateById(templateId);
  };

  useEffect(() => {
    if (
      !isNewConsultation ||
      !visitId ||
      loadingTemplates ||
      templates.length === 0 ||
      defaultTemplateAttempted.current ||
      !isFormEmpty(formData)
    ) {
      return;
    }

    const storageKey = `guide-default-template-${visitId}`;
    if (sessionStorage.getItem(storageKey)) {
      defaultTemplateAttempted.current = true;
      return;
    }

    const match = pickDefaultClinicalTemplate(templates, visitType);
    if (!match) return;

    defaultTemplateAttempted.current = true;
    sessionStorage.setItem(storageKey, '1');
    void applyTemplateById(match.id, true);
  }, [
    isNewConsultation,
    visitId,
    visitType,
    loadingTemplates,
    templates,
    formData,
    onApplyFormPatch,
  ]);

  const macroFields = {
    history: formData.history,
    examination: formData.examination,
    diagnosis: formData.diagnosis,
    clinical_notes: formData.clinical_notes,
  };

  return (
    <div className={styles.consultationForm} data-guide-id="consultation-form">
      <div className={styles.formHeader}>
        <div>
          <h2>Consultation</h2>
          <p className={styles.macroHint}>
            Type a macro ({CONSULTATION_MACROS.map((macro) => macro.trigger).join(', ')}) then Tab to
            expand · <kbd>Ctrl</kbd>+<kbd>K</kbd> for commands
          </p>
        </div>
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
        formData={macroFields}
        onChange={(value) => onFieldChange('history', value)}
        onMacroExpand={onApplyFormPatch}
      />

      <ExaminationSection
        value={formData.examination}
        formData={macroFields}
        onChange={(value) => onFieldChange('examination', value)}
        onMacroExpand={onApplyFormPatch}
      />

      <DiagnosisSection
        value={formData.diagnosis}
        formData={macroFields}
        onChange={(value) => onFieldChange('diagnosis', value)}
        onMacroExpand={onApplyFormPatch}
      />

      <ClinicalNotesSection
        value={formData.clinical_notes}
        formData={macroFields}
        onChange={(value) => onFieldChange('clinical_notes', value)}
        onMacroExpand={onApplyFormPatch}
      />
    </div>
  );
}
