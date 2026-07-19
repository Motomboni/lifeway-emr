/**
 * GuideOrb — persistent entry point for the interactive guide.
 */
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import styles from '../../styles/Guide.module.css';

export default function GuideOrb() {
  const { user } = useAuth();
  const { toggleDrawer, drawerOpen, progress } = useGuide();

  const roleLaunchDone =
    !user?.role || progress?.role_launch_completed?.[user.role] === true;
  const showBadge = progress != null && !roleLaunchDone;

  return (
    <button
      type="button"
      className={styles.guideOrb}
      onClick={toggleDrawer}
      aria-label={drawerOpen ? 'Close guide' : 'Open guide help'}
      aria-expanded={drawerOpen}
      data-guide-id="guide-orb"
      title="Guide — help & walkthroughs"
    >
      ?
      {showBadge && <span className={styles.guideOrbBadge} aria-hidden="true" />}
    </button>
  );
}
