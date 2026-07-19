/**
 * WorkflowRail — visit-scoped checklist docked under the visit header.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { fetchVisitWorkflow } from '../../api/guide';
import { useGuide } from '../../contexts/GuideContext';
import type { WorkflowPack, WorkflowStep } from '../../types/guide';
import styles from '../../styles/Guide.module.css';

interface WorkflowRailProps {
  visitId: string | number;
}

function StepChip({
  step,
  onSelect,
}: {
  step: WorkflowStep;
  onSelect: (step: WorkflowStep) => void;
}) {
  const statusClass =
    step.status === 'completed'
      ? styles.workflowStepComplete
      : step.status === 'active'
        ? styles.workflowStepActive
        : step.status === 'skipped'
          ? styles.workflowStepSkipped
          : styles.workflowStepPending;

  const icon =
    step.status === 'completed' ? '✓' : step.status === 'skipped' ? '—' : step.status === 'active' ? '●' : '○';

  return (
    <button
      type="button"
      className={`${styles.workflowStep} ${statusClass}`}
      onClick={() => onSelect(step)}
      title={step.label}
    >
      <span className={styles.workflowStepIcon} aria-hidden="true">
        {icon}
      </span>
      <span className={styles.workflowStepLabel}>{step.label}</span>
    </button>
  );
}

export default function WorkflowRail({ visitId }: WorkflowRailProps) {
  const { showSpotlightForTarget } = useGuide();
  const [workflows, setWorkflows] = useState<WorkflowPack[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchVisitWorkflow(Number(visitId));
      setWorkflows(data.workflows);
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, [visitId]);

  useEffect(() => {
    void loadWorkflows();
  }, [loadWorkflows]);

  const handleStepSelect = async (step: WorkflowStep) => {
    if (step.guide_target) {
      await showSpotlightForTarget(step.guide_target, step.label);
    }
  };

  if (loading) {
    return (
      <div className={styles.workflowRail} data-guide-id="workflow-rail">
        <p className={styles.workflowLoading}>Loading workflow…</p>
      </div>
    );
  }

  if (workflows.length === 0) {
    return null;
  }

  return (
    <div className={styles.workflowRail} data-guide-id="workflow-rail">
      <div className={styles.workflowRailHeader}>
        <span className={styles.workflowRailTitle}>Workflow</span>
        <button
          type="button"
          className={styles.workflowCollapseBtn}
          onClick={() => setCollapsed((c) => !c)}
          aria-expanded={!collapsed}
        >
          {collapsed ? 'Show' : 'Hide'}
        </button>
      </div>

      {!collapsed &&
        workflows.map((pack) => (
          <div key={pack.pack_id} className={styles.workflowPack}>
            <div className={styles.workflowPackHeader}>
              <strong>{pack.title}</strong>
              <span className={styles.workflowPackProgress}>
                {pack.completed_count}/{pack.total_count}
              </span>
            </div>
            <div className={styles.workflowSteps}>
              {pack.steps.map((step) => (
                <StepChip key={step.id} step={step} onSelect={handleStepSelect} />
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}
