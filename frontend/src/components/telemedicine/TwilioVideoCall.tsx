/**
 * Twilio Video call — multi-participant virtual clinic layout.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { saveLiveTelemedicineTranscript } from '../../api/telemedicine';
import { logger } from '../../utils/logger';
import { VOICE_OPEN_INVITE_EVENT } from '../../utils/voiceIntents';
import styles from '../../styles/VideoCall.module.css';

interface TwilioVideoCallProps {
  token: string;
  roomName: string;
  sessionId?: number;
  liveTranscription?: boolean;
  onLeave: () => void;
  onError?: (error: Error) => void;
  inviteSlot?: React.ReactNode;
}

interface RemoteTile {
  sid: string;
  identity: string;
  hasVideo: boolean;
}

export default function TwilioVideoCall({
  token,
  roomName,
  sessionId,
  liveTranscription = true,
  onLeave,
  onError,
  inviteSlot,
}: TwilioVideoCallProps) {
  const { user } = useAuth();
  const { showError } = useToast();
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [remoteTiles, setRemoteTiles] = useState<RemoteTile[]>([]);
  const [connectionLost, setConnectionLost] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);

  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const roomRef = useRef<any>(null);
  const localVideoTrackRef = useRef<any>(null);
  const localAudioTrackRef = useRef<any>(null);
  const remoteTracksRef = useRef<Record<string, any>>({});
  const liveTranscriptRef = useRef('');

  const isDoctor = user?.role === 'DOCTOR';
  const speech = useSpeechRecognition({
    continuous: true,
    interimResults: true,
    lang: 'en-NG',
    onResult: (text, isFinal) => {
      if (isFinal && text.trim()) {
        liveTranscriptRef.current = `${liveTranscriptRef.current} ${text}`.trim();
      }
    },
  });

  useEffect(() => {
    if (!inviteSlot) return;
    const open = () => setShowInvite(true);
    window.addEventListener(VOICE_OPEN_INVITE_EVENT, open);
    return () => window.removeEventListener(VOICE_OPEN_INVITE_EVENT, open);
  }, [inviteSlot]);

  const refreshTiles = useCallback((room: any) => {
    const tiles: RemoteTile[] = [];
    room.participants.forEach((p: any) => {
      let hasVideo = false;
      p.tracks.forEach((pub: any) => {
        if (pub.track && pub.track.kind === 'video' && pub.isSubscribed !== false) {
          hasVideo = true;
        }
      });
      tiles.push({
        sid: p.sid,
        identity: p.identity || p.sid,
        hasVideo,
      });
    });
    setRemoteTiles(tiles);
  }, []);

  const attachRemoteVideo = useCallback((participantSid: string, track: any) => {
    const el = remoteVideoRefs.current[participantSid];
    if (!el || track.kind !== 'video') return;
    try {
      track.attach(el);
      el.play().catch(() => undefined);
    } catch (err) {
      logger.warn('Twilio attach remote failed', err);
    }
  }, []);

  const cleanup = useCallback(() => {
    Object.values(remoteTracksRef.current).forEach((track: any) => {
      try {
        track.detach?.();
        track.stop?.();
      } catch {
        // ignore
      }
    });
    remoteTracksRef.current = {};

    try {
      localVideoTrackRef.current?.stop?.();
      localAudioTrackRef.current?.stop?.();
    } catch {
      // ignore
    }
    localVideoTrackRef.current = null;
    localAudioTrackRef.current = null;

    try {
      roomRef.current?.disconnect?.();
    } catch {
      // ignore
    }
    roomRef.current = null;

    if (localVideoRef.current) localVideoRef.current.srcObject = null;
    Object.values(remoteVideoRefs.current).forEach((el) => {
      if (el) el.srcObject = null;
    });
    setRemoteTiles([]);
  }, []);

  useEffect(() => {
    if (isConnected && liveTranscription && isDoctor && speech.isSupported && !speech.isListening) {
      speech.startListening();
    }
  }, [isConnected, liveTranscription, isDoctor, speech.isSupported]);

  useEffect(() => {
    let mounted = true;

    const connectToRoom = async () => {
      try {
        const twilioVideo = await import('twilio-video');
        const { connect, createLocalVideoTrack, createLocalAudioTrack } = twilioVideo;
        if (typeof (twilioVideo as any).Logger?.setLogLevel === 'function') {
          (twilioVideo as any).Logger.setLogLevel('error');
        }

        const videoTrack = await createLocalVideoTrack({
          width: 1280,
          height: 720,
          frameRate: 24,
        });
        let audioTrack: any = null;
        try {
          audioTrack = await createLocalAudioTrack();
        } catch {
          showError('Microphone unavailable — joining with video only');
        }

        if (!mounted) {
          videoTrack.stop();
          audioTrack?.stop();
          return;
        }

        localVideoTrackRef.current = videoTrack;
        localAudioTrackRef.current = audioTrack;
        if (localVideoRef.current) {
          videoTrack.attach(localVideoRef.current);
          localVideoRef.current.play().catch(() => undefined);
        }

        const room = await connect(token, {
          name: roomName,
          tracks: audioTrack ? [videoTrack, audioTrack] : [videoTrack],
        });

        if (!mounted) {
          room.disconnect();
          videoTrack.stop();
          audioTrack?.stop();
          return;
        }

        roomRef.current = room;
        setIsConnecting(false);
        setIsConnected(true);

        const wireParticipant = (participant: any) => {
          participant.tracks.forEach((publication: any) => {
            if (publication.track) {
              if (publication.track.kind === 'video') {
                remoteTracksRef.current[participant.sid] = publication.track;
                attachRemoteVideo(participant.sid, publication.track);
              }
            }
          });
          participant.on('trackSubscribed', (track: any) => {
            if (track.kind === 'video') {
              remoteTracksRef.current[participant.sid] = track;
              attachRemoteVideo(participant.sid, track);
            }
            refreshTiles(room);
          });
          participant.on('trackUnsubscribed', (track: any) => {
            if (track.kind === 'video') {
              try {
                track.detach();
              } catch {
                // ignore
              }
              delete remoteTracksRef.current[participant.sid];
            }
            refreshTiles(room);
          });
          refreshTiles(room);
        };

        room.participants.forEach(wireParticipant);
        room.on('participantConnected', wireParticipant);
        room.on('participantDisconnected', (participant: any) => {
          const track = remoteTracksRef.current[participant.sid];
          if (track) {
            try {
              track.detach();
            } catch {
              // ignore
            }
            delete remoteTracksRef.current[participant.sid];
          }
          refreshTiles(room);
        });
        room.on('disconnected', (_r: any, error: any) => {
          setIsConnected(false);
          setConnectionLost(error?.message || 'Connection lost. You can return and rejoin the clinic.');
          cleanup();
        });
      } catch (error: any) {
        logger.error('Twilio connect failed', error);
        if (!mounted) return;
        setIsConnecting(false);
        showError(error?.message || 'Failed to connect to video call');
        cleanup();
        onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    };

    connectToRoom();
    return () => {
      mounted = false;
      if (speech.isListening) speech.stopListening();
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, roomName]);

  // Re-attach when tile refs mount
  useEffect(() => {
    remoteTiles.forEach((tile) => {
      const track = remoteTracksRef.current[tile.sid];
      if (track) attachRemoteVideo(tile.sid, track);
    });
  }, [remoteTiles, attachRemoteVideo]);

  const toggleVideo = () => {
    if (!localVideoTrackRef.current) return;
    if (isVideoEnabled) localVideoTrackRef.current.disable();
    else localVideoTrackRef.current.enable();
    setIsVideoEnabled(!isVideoEnabled);
  };

  const toggleAudio = () => {
    if (!localAudioTrackRef.current) return;
    if (isAudioEnabled) localAudioTrackRef.current.disable();
    else localAudioTrackRef.current.enable();
    setIsAudioEnabled(!isAudioEnabled);
  };

  const handleLeave = async () => {
    if (speech.isListening) speech.stopListening();
    const liveText = (
      liveTranscriptRef.current ||
      `${speech.transcript} ${speech.interimTranscript}`.trim()
    ).trim();
    if (sessionId && liveText && isDoctor) {
      try {
        await saveLiveTelemedicineTranscript(sessionId, liveText);
      } catch (err) {
        logger.warn('Failed to save live transcript', err);
      }
    }
    cleanup();
    onLeave();
  };

  if (isConnecting) {
    return (
      <div className={styles.videoCallContainer}>
        <div className={styles.connecting}>
          <div className={styles.spinner} />
          <p>Connecting to virtual clinic…</p>
        </div>
      </div>
    );
  }

  if (connectionLost) {
    return (
      <div className={styles.videoCallContainer}>
        <div className={styles.connecting}>
          <p className={styles.connectionLostMessage}>{connectionLost}</p>
          <button type="button" className={styles.controlButton} onClick={() => { setConnectionLost(null); onLeave(); }}>
            Return
          </button>
        </div>
      </div>
    );
  }

  const remoteCount = remoteTiles.length;

  return (
    <div className={styles.videoCallContainer}>
      <div className={styles.clinicTopBar}>
        <div>
          <strong>Virtual clinic</strong>
          <span className={styles.roomMeta}>
            {remoteCount === 0
              ? 'Waiting for others to join'
              : `${remoteCount + 1} in room`}
          </span>
        </div>
        {inviteSlot && (
          <button
            type="button"
            className={styles.inviteToggle}
            onClick={() => setShowInvite((v) => !v)}
          >
            {showInvite ? 'Hide team' : 'Invite staff'}
          </button>
        )}
      </div>

      <div
        className={`${styles.videoGrid} ${
          remoteCount > 1 ? styles.videoGridMulti : styles.videoGridSingle
        }`}
      >
        {remoteCount === 0 ? (
          <div className={styles.remoteVideoContainer}>
            <div className={styles.waitingForParticipant}>
              <p>Waiting for patient or invited staff…</p>
            </div>
          </div>
        ) : (
          remoteTiles.map((tile) => (
            <div key={tile.sid} className={styles.remoteVideoContainer}>
              <video
                ref={(el) => {
                  remoteVideoRefs.current[tile.sid] = el;
                }}
                autoPlay
                playsInline
                className={styles.remoteVideo}
              />
              {!tile.hasVideo && (
                <div className={styles.waitingForParticipant}>
                  <p>{tile.identity}</p>
                  <span>Camera off</span>
                </div>
              )}
              <div className={styles.remoteLabel}>{tile.identity}</div>
            </div>
          ))
        )}

        <div className={styles.localVideoContainer}>
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className={styles.localVideo}
            style={{ display: isVideoEnabled ? 'block' : 'none' }}
          />
          {!isVideoEnabled && (
            <div className={styles.videoDisabled}>
              <p>Camera Off</p>
            </div>
          )}
          <div className={styles.localVideoLabel}>
            {user?.first_name} {user?.last_name} (You)
          </div>
        </div>
      </div>

      {showInvite && inviteSlot && (
        <div className={styles.inviteDrawer}>{inviteSlot}</div>
      )}

      <div className={styles.controls}>
        <button
          type="button"
          onClick={toggleVideo}
          className={`${styles.controlButton} ${!isVideoEnabled ? styles.disabled : ''}`}
        >
          {isVideoEnabled ? 'Camera' : 'Cam off'}
        </button>
        <button
          type="button"
          onClick={toggleAudio}
          className={`${styles.controlButton} ${!isAudioEnabled ? styles.disabled : ''}`}
        >
          {isAudioEnabled ? 'Mic' : 'Muted'}
        </button>
        <button type="button" onClick={handleLeave} className={`${styles.controlButton} ${styles.leaveButton}`}>
          Leave clinic
        </button>
      </div>

      {isConnected && (
        <div className={styles.status}>
          <span className={styles.statusIndicator} />
          Connected
          {liveTranscription && isDoctor && speech.isSupported && (
            <span className={styles.liveTranscriptBadge}>
              {speech.isListening ? 'Live transcript on' : 'Live transcript paused'}
            </span>
          )}
        </div>
      )}

      {liveTranscription && isDoctor && (speech.transcript || speech.interimTranscript) && (
        <div className={styles.liveTranscriptPanel}>
          <strong>Live transcript</strong>
          <p>
            {liveTranscriptRef.current || speech.transcript}
            {speech.interimTranscript && (
              <span className={styles.interimText}> {speech.interimTranscript}</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
