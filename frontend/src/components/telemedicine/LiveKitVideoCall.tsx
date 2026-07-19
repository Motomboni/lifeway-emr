/**
 * LiveKit video call for telemedicine virtual clinic (multi-participant).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
  createLocalVideoTrack,
  type LocalVideoTrack,
  type LocalAudioTrack,
  type RemoteParticipant,
  type RemoteTrack,
  type RemoteTrackPublication,
} from 'livekit-client';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { saveLiveTelemedicineTranscript } from '../../api/telemedicine';
import { logger } from '../../utils/logger';
import { VOICE_OPEN_INVITE_EVENT } from '../../utils/voiceIntents';
import styles from '../../styles/VideoCall.module.css';

interface LiveKitVideoCallProps {
  token: string;
  roomName: string;
  livekitUrl: string;
  sessionId?: number;
  liveTranscription?: boolean;
  onLeave: () => void;
  onError?: (error: Error) => void;
  inviteSlot?: React.ReactNode;
}

interface RemoteTile {
  identity: string;
  name: string;
  hasVideo: boolean;
}

function participantLabel(p: RemoteParticipant): string {
  return p.name || p.identity || 'Participant';
}

export default function LiveKitVideoCall({
  token,
  roomName,
  livekitUrl,
  sessionId,
  liveTranscription = true,
  onLeave,
  onError,
  inviteSlot,
}: LiveKitVideoCallProps) {
  const { user } = useAuth();
  const { showError } = useToast();
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [remoteTiles, setRemoteTiles] = useState<RemoteTile[]>([]);
  const [connectionLost, setConnectionLost] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);

  useEffect(() => {
    if (!inviteSlot) return;
    const open = () => setShowInvite(true);
    window.addEventListener(VOICE_OPEN_INVITE_EVENT, open);
    return () => window.removeEventListener(VOICE_OPEN_INVITE_EVENT, open);
  }, [inviteSlot]);

  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const roomRef = useRef<Room | null>(null);
  const localVideoTrackRef = useRef<LocalVideoTrack | null>(null);
  const localAudioTrackRef = useRef<LocalAudioTrack | null>(null);
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

  const refreshRemoteTiles = useCallback((room: Room) => {
    const tiles: RemoteTile[] = [];
    room.remoteParticipants.forEach((p) => {
      const hasVideo = Array.from(p.videoTrackPublications.values()).some(
        (pub) => pub.track && !pub.isMuted,
      );
      tiles.push({
        identity: p.identity,
        name: participantLabel(p),
        hasVideo,
      });
    });
    setRemoteTiles(tiles);
  }, []);

  const attachRemoteTrack = useCallback(
    (participant: RemoteParticipant, track: RemoteTrack) => {
      if (track.kind !== Track.Kind.Video) return;
      const el = remoteVideoRefs.current[participant.identity];
      if (!el) return;
      track.attach(el);
      el.play().catch(() => undefined);
      if (roomRef.current) refreshRemoteTiles(roomRef.current);
    },
    [refreshRemoteTiles],
  );

  const cleanup = useCallback(() => {
    localVideoTrackRef.current?.stop();
    localAudioTrackRef.current?.stop();
    localVideoTrackRef.current = null;
    localAudioTrackRef.current = null;

    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }

    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
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

    const connect = async () => {
      try {
        const room = new Room({ adaptiveStream: true, dynacast: true });
        roomRef.current = room;

        room.on(
          RoomEvent.TrackSubscribed,
          (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
            attachRemoteTrack(participant, track);
          },
        );

        room.on(RoomEvent.TrackUnsubscribed, (track) => {
          if (track.kind === Track.Kind.Video) {
            track.detach();
          }
          if (roomRef.current) refreshRemoteTiles(roomRef.current);
        });

        room.on(RoomEvent.ParticipantConnected, () => {
          if (roomRef.current) refreshRemoteTiles(roomRef.current);
        });

        room.on(RoomEvent.ParticipantDisconnected, () => {
          if (roomRef.current) refreshRemoteTiles(roomRef.current);
        });

        room.on(RoomEvent.Disconnected, () => {
          if (!mounted) return;
          setIsConnected(false);
          setConnectionLost('Connection lost. You can return and rejoin the clinic.');
        });

        await room.connect(livekitUrl, token);

        const videoTrack = await createLocalVideoTrack({ resolution: { width: 1280, height: 720 } });
        const audioTrack = await createLocalAudioTrack();
        localVideoTrackRef.current = videoTrack;
        localAudioTrackRef.current = audioTrack;

        if (localVideoRef.current) {
          videoTrack.attach(localVideoRef.current);
        }

        await room.localParticipant.publishTrack(videoTrack);
        await room.localParticipant.publishTrack(audioTrack);

        // Attach any already-subscribed remote videos
        room.remoteParticipants.forEach((p) => {
          p.videoTrackPublications.forEach((pub) => {
            if (pub.track) attachRemoteTrack(p, pub.track);
          });
        });
        refreshRemoteTiles(room);

        if (!mounted) {
          cleanup();
          return;
        }
        setIsConnecting(false);
        setIsConnected(true);
      } catch (err) {
        logger.error('LiveKit connect failed', err);
        if (!mounted) return;
        setIsConnecting(false);
        const error = err instanceof Error ? err : new Error('Failed to connect');
        showError(error.message);
        onError?.(error);
      }
    };

    connect();
    return () => {
      mounted = false;
      if (speech.isListening) speech.stopListening();
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, livekitUrl, roomName]);

  // Re-attach remote tracks when tile refs mount/change
  useEffect(() => {
    const room = roomRef.current;
    if (!room) return;
    remoteTiles.forEach((tile) => {
      const participant = room.remoteParticipants.get(tile.identity);
      if (!participant) return;
      participant.videoTrackPublications.forEach((pub) => {
        if (pub.track) attachRemoteTrack(participant, pub.track);
      });
    });
  }, [remoteTiles, attachRemoteTrack]);

  const toggleVideo = async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !isVideoEnabled;
    await room.localParticipant.setCameraEnabled(next);
    setIsVideoEnabled(next);
  };

  const toggleAudio = async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !isAudioEnabled;
    await room.localParticipant.setMicrophoneEnabled(next);
    setIsAudioEnabled(next);
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
            <div key={tile.identity} className={styles.remoteVideoContainer}>
              <video
                ref={(el) => {
                  remoteVideoRefs.current[tile.identity] = el;
                }}
                autoPlay
                playsInline
                className={styles.remoteVideo}
              />
              {!tile.hasVideo && (
                <div className={styles.waitingForParticipant}>
                  <p>{tile.name}</p>
                  <span>Camera off</span>
                </div>
              )}
              <div className={styles.remoteLabel}>{tile.name}</div>
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
          aria-label={isVideoEnabled ? 'Turn camera off' : 'Turn camera on'}
        >
          {isVideoEnabled ? 'Camera' : 'Cam off'}
        </button>
        <button
          type="button"
          onClick={toggleAudio}
          className={`${styles.controlButton} ${!isAudioEnabled ? styles.disabled : ''}`}
          aria-label={isAudioEnabled ? 'Mute' : 'Unmute'}
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
