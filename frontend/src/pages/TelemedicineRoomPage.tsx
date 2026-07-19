/**
 * Telemedicine Room Page — virtual clinic join route
 * /telemedicine/room/:sessionId
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getTelemedicineSession,
  getTelemedicineAccessToken,
  leaveTelemedicineSession,
  startTelemedicineSession,
  respondTelemedicineInvite,
} from '../api/telemedicine';
import { TelemedicineSession } from '../types/telemedicine';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import VideoCall from '../components/telemedicine/VideoCall';
import StaffInvitePanel from '../components/telemedicine/StaffInvitePanel';
import styles from '../styles/Telemedicine.module.css';
import clinicStyles from '../styles/VirtualClinic.module.css';

const CLINIC_JOIN_ROLES = [
  'DOCTOR',
  'PATIENT',
  'NURSE',
  'LAB_TECH',
  'RADIOLOGY_TECH',
  'PHARMACIST',
  'ADMIN',
  'IVF_SPECIALIST',
  'EMBRYOLOGIST',
];

export default function TelemedicineRoomPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [session, setSession] = useState<TelemedicineSession | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [videoProvider, setVideoProvider] = useState<'twilio' | 'livekit'>('twilio');
  const [livekitUrl, setLivekitUrl] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsAccept, setNeedsAccept] = useState(false);

  const isHost =
    !!user && !!session && user.role === 'DOCTOR' && session.doctor === user.id;

  useEffect(() => {
    if (!sessionId || !user) return;

    const parsedId = parseInt(sessionId, 10);
    if (Number.isNaN(parsedId)) {
      setError('Invalid session link.');
      setLoading(false);
      return;
    }

    let cancelled = false;

    const joinRoom = async () => {
      try {
        setLoading(true);
        setError(null);

        if (!CLINIC_JOIN_ROLES.includes(user.role || '')) {
          setError('Your role cannot join telemedicine sessions.');
          return;
        }

        const sessionData = await getTelemedicineSession(parsedId);
        if (cancelled) return;

        if (sessionData.my_invite_status === 'PENDING') {
          setSession(sessionData);
          setNeedsAccept(true);
          return;
        }

        if (
          user.role === 'DOCTOR' &&
          sessionData.doctor === user.id &&
          sessionData.status === 'SCHEDULED'
        ) {
          await startTelemedicineSession(parsedId);
          sessionData.status = 'IN_PROGRESS';
        }

        const tokenData = await getTelemedicineAccessToken(parsedId);
        if (cancelled) return;

        setSession(sessionData);
        setAccessToken(tokenData.token);
        setVideoProvider(tokenData.video_provider || sessionData.video_provider || 'twilio');
        setLivekitUrl(tokenData.livekit_url);
        showSuccess('Joined virtual clinic');
      } catch (err: unknown) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : 'Failed to join telemedicine session';
        setError(message);
        showError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    joinRoom();
    return () => {
      cancelled = true;
    };
  }, [sessionId, user, showError, showSuccess]);

  const handleAcceptInvite = async (accept: boolean) => {
    if (!session) return;
    try {
      setLoading(true);
      await respondTelemedicineInvite(session.id, accept);
      if (!accept) {
        showSuccess('Invite declined');
        navigate('/telemedicine', { replace: true });
        return;
      }
      const tokenData = await getTelemedicineAccessToken(session.id);
      setNeedsAccept(false);
      setAccessToken(tokenData.token);
      setVideoProvider(tokenData.video_provider || session.video_provider || 'twilio');
      setLivekitUrl(tokenData.livekit_url);
      showSuccess('Joined virtual clinic');
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Could not respond to invite');
    } finally {
      setLoading(false);
    }
  };

  const handleLeave = async () => {
    if (session) {
      try {
        await leaveTelemedicineSession(session.id);
      } catch {
        // Best-effort cleanup
      }
    }
    setSession(null);
    setAccessToken(null);

    if (user?.role === 'PATIENT') {
      navigate('/patient-portal/telemedicine', { replace: true });
    } else {
      navigate('/telemedicine', { replace: true });
    }
  };

  if (loading) {
    return (
      <div className={styles.telemedicinePage}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (needsAccept && session) {
    return (
      <div className={styles.telemedicinePage}>
        <div className={clinicStyles.inviteBanner}>
          <div>
            <strong>Virtual clinic invite</strong>
            <span>
              Dr. {session.doctor_name} invited you to join {session.patient_name}&apos;s visit
              {session.participants?.find((p) => p.user === user?.id)?.invite_message
                ? `: “${session.participants.find((p) => p.user === user?.id)?.invite_message}”`
                : '.'}
            </span>
          </div>
          <div className={clinicStyles.inviteBannerActions}>
            <button type="button" className={clinicStyles.acceptBtn} onClick={() => handleAcceptInvite(true)}>
              Accept & join
            </button>
            <button type="button" className={clinicStyles.declineBtn} onClick={() => handleAcceptInvite(false)}>
              Decline
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error || !session || !accessToken) {
    return (
      <div className={styles.telemedicinePage}>
        <div className={styles.emptyState}>
          <p>{error || 'Unable to join this session.'}</p>
          <button
            type="button"
            className={styles.actionButton}
            onClick={() =>
              navigate(
                user?.role === 'PATIENT'
                  ? '/patient-portal/telemedicine'
                  : '/telemedicine',
                { replace: true },
              )
            }
          >
            Back to Telemedicine
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.telemedicinePage}>
      <VideoCall
        key={`${session.id}-${accessToken}`}
        token={accessToken}
        roomName={session.twilio_room_name}
        sessionId={session.id}
        videoProvider={videoProvider}
        livekitUrl={livekitUrl}
        liveTranscription={session.recording_enabled !== false}
        onLeave={handleLeave}
        inviteSlot={
          isHost ? (
            <StaffInvitePanel
              session={session}
              canInvite
              compact
              onUpdated={(participants) =>
                setSession((prev) => (prev ? { ...prev, participants } : prev))
              }
            />
          ) : null
        }
      />
    </div>
  );
}
