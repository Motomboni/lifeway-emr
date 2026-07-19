/**
 * RoleLaunchWelcome — first-login welcome card before the spotlight tour.
 */
import React from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import { getRoleLaunchSteps } from '../../data/roleLaunchSteps';
import { roleSupportsSandbox } from '../../utils/roleLaunchPaths';
import styles from '../../styles/Guide.module.css';

interface RoleLaunchWelcomeProps {
  onPracticeSandbox: () => void;
}

export default function RoleLaunchWelcome({ onPracticeSandbox }: RoleLaunchWelcomeProps) {
  const { user } = useAuth();
  const { startRoleLaunch, skipRoleLaunch, dismissRoleLaunchWelcome, guideModules } = useGuide();

  const steps = getRoleLaunchSteps(user?.role, guideModules);
  const hasTour = steps.length > 0;
  const canSandbox = roleSupportsSandbox(user?.role);

  const handleSkip = async () => {
    dismissRoleLaunchWelcome();
    await skipRoleLaunch();
  };

  return createPortal(
    <>
      <div className={styles.launchWelcomeBackdrop} role="presentation" aria-hidden="true" />
      <div
        className={styles.launchWelcomeCard}
        role="dialog"
        aria-modal="true"
        aria-labelledby="role-launch-welcome-title"
      >
        <h2 id="role-launch-welcome-title">Welcome to your EMR</h2>
        <p>
          {hasTour
            ? `Take a ${Math.min(steps.length * 30, 180)}-second guided tour tailored to your ${user?.role?.toLowerCase().replace('_', ' ')} workflow — no videos required.`
            : 'Use the Guide button anytime for contextual help on this screen.'}
        </p>
        <div className={styles.launchWelcomeActions}>
          {hasTour && (
            <button type="button" className={styles.launchPrimary} onClick={startRoleLaunch}>
              Start tour
            </button>
          )}
          {canSandbox && (
            <button type="button" className={styles.launchSecondary} onClick={onPracticeSandbox}>
              Practice in sandbox
            </button>
          )}
          <button type="button" className={styles.launchSkip} onClick={handleSkip}>
            Skip for now
          </button>
        </div>
      </div>
    </>,
    document.body
  );
}
