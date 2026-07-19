/**
 * Video call router — Twilio Video or LiveKit based on backend provider.
 */
import React from 'react';
import TwilioVideoCall from './TwilioVideoCall';
import LiveKitVideoCall from './LiveKitVideoCall';

export type VideoProvider = 'twilio' | 'livekit';

export interface VideoCallProps {
  token: string;
  roomName: string;
  sessionId?: number;
  liveTranscription?: boolean;
  videoProvider?: VideoProvider;
  livekitUrl?: string;
  onLeave: () => void;
  onError?: (error: Error) => void;
  inviteSlot?: React.ReactNode;
}

export default function VideoCall({
  videoProvider = 'twilio',
  livekitUrl,
  inviteSlot,
  ...props
}: VideoCallProps) {
  if (videoProvider === 'livekit') {
    if (!livekitUrl) {
      return (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          LiveKit is not configured (missing server URL). Check LIVEKIT_URL in backend settings.
        </div>
      );
    }
    return <LiveKitVideoCall {...props} livekitUrl={livekitUrl} inviteSlot={inviteSlot} />;
  }

  return <TwilioVideoCall {...props} inviteSlot={inviteSlot} />;
}
