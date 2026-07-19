/**
 * GuideShell — mounts guide UI for authenticated staff only.
 */
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import { isStaffUser } from '../../utils/roleUtils';
import GuideOrb from './GuideOrb';
import CommandPalette from './CommandPalette';
import GuideJitMonitor from './GuideJitMonitor';
import HelpDrawer from './HelpDrawer';
import RoleLaunchTour from './RoleLaunchTour';
import SpotlightCoach from './SpotlightCoach';
import VoiceCommandBar from '../voice/VoiceCommandBar';

export default function GuideShell() {
  const { isAuthenticated, user } = useAuth();
  const { guideEnabled } = useGuide();

  if (!isAuthenticated || !isStaffUser(user)) {
    return null;
  }

  return (
    <>
      <VoiceCommandBar />
      {guideEnabled && (
        <>
          <GuideOrb />
          <HelpDrawer />
          <SpotlightCoach />
          <GuideJitMonitor />
          <CommandPalette />
          <RoleLaunchTour />
        </>
      )}
    </>
  );
}
