/**
 * Telemedicine Page
 * 
 * Manage and join telemedicine video consultations.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchTelemedicineSessions,
  createTelemedicineSession,
  startTelemedicineSession,
  endTelemedicineSession,
  getTelemedicineAccessToken,
  leaveTelemedicineSession,
  requestTelemedicineTranscription,
  getTelemedicineRecordingUrl,
  respondTelemedicineInvite,
} from '../api/telemedicine';
import { getAuthToken } from '../utils/apiClient';
import { TelemedicineSession } from '../types/telemedicine';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import VideoCall from '../components/telemedicine/VideoCall';
import StaffInvitePanel from '../components/telemedicine/StaffInvitePanel';
import TelemedicinePricingPanel from '../components/telemedicine/TelemedicinePricingPanel';
import { fetchVisits, Visit } from '../api/visits';
import styles from '../styles/Telemedicine.module.css';
import clinicStyles from '../styles/VirtualClinic.module.css';
import { PENDING_INVITE_STORAGE_KEY } from '../utils/voiceIntents';
import { isAdminUser } from '../utils/roleUtils';

export default function TelemedicinePage() {
  const { visitId } = useParams<{ visitId?: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();
  
  const [sessions, setSessions] = useState<TelemedicineSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<TelemedicineSession | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [videoProvider, setVideoProvider] = useState<'twilio' | 'livekit'>('twilio');
  const [livekitUrl, setLivekitUrl] = useState<string | undefined>();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [availableVisits, setAvailableVisits] = useState<Visit[]>([]);
  const [loadingVisits, setLoadingVisits] = useState(false);
  const [selectedVisitId, setSelectedVisitId] = useState<string | null>(visitId || null);
  const [endSessionModal, setEndSessionModal] = useState<{ session: TelemedicineSession; addBilling: boolean } | null>(null);
  const [endingSession, setEndingSession] = useState(false);
  const [requestingTranscription, setRequestingTranscription] = useState<number | null>(null);
  const [loadingRecording, setLoadingRecording] = useState<number | null>(null);
  
  const [formData, setFormData] = useState({
    scheduled_start: new Date().toISOString().slice(0, 16),
    recording_enabled: true,
    recording_consent_acknowledged: false,
    notes: '',
  });
  const [invitePanelSessionId, setInvitePanelSessionId] = useState<number | null>(null);
  const [respondingInviteId, setRespondingInviteId] = useState<number | null>(null);

  const isDoctorHost = user?.role === 'DOCTOR';
  const isInvitedStaff = !!user && user.role !== 'DOCTOR' && user.role !== 'PATIENT';
  const canEditPricing = isAdminUser(user);

  useEffect(() => {
    loadSessions();
    if (!visitId && user?.role === 'DOCTOR') {
      loadAvailableVisits();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visitId]); // Only depend on visitId to avoid excessive re-renders

  // Soft-poll so nurses see new invites without refreshing
  useEffect(() => {
    if (!isInvitedStaff) return undefined;
    const timer = window.setInterval(() => {
      loadSessions();
    }, 20000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInvitedStaff]);

  // Voice "invite nurse" lands on clinic list — open invite panel on host session
  useEffect(() => {
    if (user?.role !== 'DOCTOR' || invitePanelSessionId) return;
    let pending: string | null = null;
    try {
      pending = sessionStorage.getItem(PENDING_INVITE_STORAGE_KEY);
    } catch {
      pending = null;
    }
    if (!pending) return;
    const host = sessions.find(
      (s) =>
        s.doctor === user.id &&
        (s.status === 'IN_PROGRESS' || s.status === 'SCHEDULED'),
    );
    if (host) setInvitePanelSessionId(host.id);
  }, [sessions, user, invitePanelSessionId]);

  // Poll while automatic transcription is processing
  useEffect(() => {
    const pending = sessions.some(
      (s) =>
        s.transcription_status === 'PENDING' || s.transcription_status === 'PROCESSING',
    );
    if (!pending) return undefined;
    const timer = window.setInterval(() => {
      loadSessions();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [sessions]);

  // Cleanup effect when component unmounts or navigating away
  useEffect(() => {
    return () => {
      // This ensures cleanup when navigating away
      if (activeSession && accessToken) {
        // Cleanup will be handled by VideoCall component's cleanup
        setActiveSession(null);
        setAccessToken(null);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on unmount

  const loadAvailableVisits = async () => {
    try {
      setLoadingVisits(true);
      const response = await fetchVisits();
      const allVisits = Array.isArray(response) ? response : (response as any).results;
      // Filter for OPEN visits with cleared payment (including PARTIALLY_PAID)
      // This ensures doctors can create telemedicine sessions for visits where clinical work can proceed
      const openVisits = allVisits.filter((v: Visit) => {
        if (v.status !== 'OPEN') return false;
        if (v.payment_gates) {
          return v.payment_gates.registration_paid;
        }
        return (
          v.payment_status === 'PAID' ||
          v.payment_status === 'SETTLED' ||
          v.payment_status === 'PARTIALLY_PAID' ||
          v.payment_status === 'CLEARED' ||
          v.payment_status === 'INSURANCE_CLAIMED'
        );
      });
      setAvailableVisits(openVisits);
    } catch (error: any) {
      console.error('Failed to load visits:', error);
      setAvailableVisits([]);
    } finally {
      setLoadingVisits(false);
    }
  };

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await fetchTelemedicineSessions(visitId ? parseInt(visitId) : undefined);
      // Ensure data is an array (handle both direct array and paginated response)
      const sessionsArray = Array.isArray(data) 
        ? data 
        : ((data as any)?.results || []);
      setSessions(sessionsArray);
    } catch (error: any) {
      showError(error.message || 'Failed to load telemedicine sessions');
      setSessions([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const visitIdToUse = visitId || selectedVisitId;
    if (!visitIdToUse) {
      showError('Please select a visit');
      return;
    }

    if (formData.recording_enabled && !formData.recording_consent_acknowledged) {
      showError('Confirm patient recording consent before creating a recorded session.');
      return;
    }
    
    try {
      setCreating(true);
      const session = await createTelemedicineSession({
        visit: parseInt(visitIdToUse),
        scheduled_start: formData.scheduled_start,
        recording_enabled: formData.recording_enabled,
        recording_consent_acknowledged: formData.recording_consent_acknowledged,
        notes: formData.notes || undefined,
      });
      
      showSuccess('Telemedicine session created successfully');
      setShowCreateForm(false);
      setFormData({
        scheduled_start: new Date().toISOString().slice(0, 16),
        recording_enabled: true,
        recording_consent_acknowledged: false,
        notes: '',
      });
      // If we created from visit selection, navigate to the visit-specific page
      if (!visitId && selectedVisitId) {
        navigate(`/visits/${selectedVisitId}/telemedicine`);
      } else {
        loadSessions();
      }
    } catch (error: any) {
      showError(error.message || 'Failed to create telemedicine session');
    } finally {
      setCreating(false);
    }
  };

  const handleStartSession = async (session: TelemedicineSession) => {
    try {
      await startTelemedicineSession(session.id);
      showSuccess('Session started');
      loadSessions();
    } catch (error: any) {
      showError(error.message || 'Failed to start session');
    }
  };

  const handleJoinSession = async (session: TelemedicineSession) => {
    try {
      if (session.my_invite_status === 'PENDING') {
        await respondTelemedicineInvite(session.id, true);
      }
      // Host doctor starts the encounter; invited staff just join
      if (
        session.status === 'SCHEDULED' &&
        user?.role === 'DOCTOR' &&
        session.doctor === user.id
      ) {
        await startTelemedicineSession(session.id);
        session = { ...session, status: 'IN_PROGRESS' };
      }
      const tokenData = await getTelemedicineAccessToken(session.id);
      setAccessToken(tokenData.token);
      setVideoProvider(tokenData.video_provider || session.video_provider || 'twilio');
      setLivekitUrl(tokenData.livekit_url);
      setActiveSession(session);
      loadSessions();
    } catch (error: any) {
      showError(error.message || 'Failed to join session');
    }
  };

  const handleRespondInvite = async (session: TelemedicineSession, accept: boolean) => {
    try {
      setRespondingInviteId(session.id);
      await respondTelemedicineInvite(session.id, accept);
      showSuccess(accept ? 'Invite accepted' : 'Invite declined');
      if (accept) {
        await handleJoinSession({ ...session, my_invite_status: 'ACCEPTED' });
      } else {
        loadSessions();
      }
    } catch (error: any) {
      showError(error.message || 'Failed to respond to invite');
    } finally {
      setRespondingInviteId(null);
    }
  };

  const handleEndSessionClick = (session: TelemedicineSession) => {
    setEndSessionModal({ session, addBilling: false });
  };

  const handleEndSessionConfirm = async () => {
    if (!endSessionModal) return;
    const { session, addBilling } = endSessionModal;
    setEndingSession(true);
    try {
      const result = await endTelemedicineSession(session.id, { add_billing: addBilling });
      showSuccess(
        result?.billing_added
          ? 'Session ended. Transcription will run automatically from the recording.'
          : 'Session ended. Automatic transcription started.',
      );
      setEndSessionModal(null);
      loadSessions();
    } catch (error: any) {
      showError(error.message || 'Failed to end session');
    } finally {
      setEndingSession(false);
    }
  };

  const handleRequestTranscription = async (session: TelemedicineSession) => {
    setRequestingTranscription(session.id);
    try {
      await requestTelemedicineTranscription(session.id);
      showSuccess('Transcription requested. It may take a moment to process.');
      loadSessions();
    } catch (error: any) {
      showError(error.message || 'Failed to request transcription');
    } finally {
      setRequestingTranscription(null);
    }
  };

  const handleViewRecording = async (session: TelemedicineSession) => {
    const token = getAuthToken();
    if (!token) {
      showError('Please sign in to view the recording.');
      return;
    }
    setLoadingRecording(session.id);
    try {
      const url = getTelemedicineRecordingUrl(session.id);
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to load recording');
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, '_blank', 'noopener');
      showSuccess('Recording opened in new tab.');
    } catch (error: any) {
      showError(error.message || 'Could not load recording. It may still be processing.');
    } finally {
      setLoadingRecording(null);
    }
  };

  const handleLeaveCall = async () => {
    if (activeSession) {
      try {
        await leaveTelemedicineSession(activeSession.id);
      } catch (error) {
        console.error('Failed to leave session:', error);
      }
    }
    setActiveSession(null);
    setAccessToken(null);
    loadSessions();
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'IN_PROGRESS':
        return styles.statusInProgress;
      case 'COMPLETED':
        return styles.statusCompleted;
      case 'CANCELLED':
        return styles.statusCancelled;
      case 'FAILED':
        return styles.statusFailed;
      default:
        return styles.statusScheduled;
    }
  };

  const pendingInvites = sessions.filter((s) => s.my_invite_status === 'PENDING');

  // If in active call, show video component
  if (activeSession && accessToken) {
    const canInviteInCall =
      user?.role === 'DOCTOR' && activeSession.doctor === user.id;
    return (
      <div className={styles.telemedicinePage}>
        <VideoCall
          key={`${activeSession.id}-${accessToken}`}
          token={accessToken}
          roomName={activeSession.twilio_room_name}
          sessionId={activeSession.id}
          videoProvider={videoProvider}
          livekitUrl={livekitUrl}
          liveTranscription={activeSession.recording_enabled !== false}
          onLeave={handleLeaveCall}
          onError={(error) => {
            showError(error.message);
            handleLeaveCall();
          }}
          inviteSlot={
            canInviteInCall ? (
              <StaffInvitePanel
                session={activeSession}
                canInvite
                compact
                onUpdated={(participants) =>
                  setActiveSession((prev) => (prev ? { ...prev, participants } : prev))
                }
              />
            ) : null
          }
        />
      </div>
    );
  }

  return (
    <div className={styles.telemedicinePage}>
      <BackToDashboard />

      <div className={clinicStyles.clinicHero}>
        <div>
          <h1>Virtual Clinic</h1>
          <p>
            {isDoctorHost
              ? 'Run video visits like an in-person clinic — invite nurses or specialists into the room when you need them.'
              : canEditPricing
                ? 'Set the telemedicine consultation fee and review virtual clinic sessions.'
                : 'Join live telemedicine visits you have been invited to as clinical staff.'}
          </p>
        </div>
        {user?.role === 'DOCTOR' && (
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className={styles.createButton}
            type="button"
          >
            {showCreateForm ? 'Cancel' : '+ New clinic session'}
          </button>
        )}
      </div>

      {canEditPricing && <TelemedicinePricingPanel />}

      {pendingInvites.map((session) => (
        <div key={`invite-${session.id}`} className={clinicStyles.inviteBanner}>
          <div>
            <strong>Clinic invite · Session #{session.id}</strong>
            <span>
              Dr. {session.doctor_name} invited you for {session.patient_name}
              {session.my_clinic_role ? ` as ${session.my_clinic_role.toLowerCase()}` : ''}.
            </span>
          </div>
          <div className={clinicStyles.inviteBannerActions}>
            <button
              type="button"
              className={clinicStyles.acceptBtn}
              disabled={respondingInviteId === session.id}
              onClick={() => handleRespondInvite(session, true)}
            >
              Accept & join
            </button>
            <button
              type="button"
              className={clinicStyles.declineBtn}
              disabled={respondingInviteId === session.id}
              onClick={() => handleRespondInvite(session, false)}
            >
              Decline
            </button>
          </div>
        </div>
      ))}

      <div className={styles.header}>
        <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Sessions</h2>
      </div>

      {showCreateForm && user?.role === 'DOCTOR' && (
        <div className={styles.createForm}>
          <h2>Create Telemedicine Session</h2>
          <form onSubmit={handleCreateSession}>
            {!visitId && (
              <div className={styles.formGroup}>
                <label>Select Visit *</label>
                {loadingVisits ? (
                  <p>Loading visits...</p>
                ) : availableVisits.length === 0 ? (
                  <div>
                    <p style={{ color: '#d32f2f', marginBottom: '10px' }}>
                      No open visits with cleared payment available. 
                      Visits must be OPEN and payment must be PAID, SETTLED, or PARTIALLY_PAID to create telemedicine sessions.
                    </p>
                    <button
                      type="button"
                      onClick={() => navigate('/visits/new')}
                      className={styles.submitButton}
                    >
                      Create New Visit
                    </button>
                  </div>
                ) : (
                  <select
                    value={selectedVisitId || ''}
                    onChange={(e) => setSelectedVisitId(e.target.value)}
                    required
                    className={styles.selectInput}
                  >
                    <option value="">-- Select a Visit --</option>
                    {availableVisits.map((visit: Visit) => (
                      <option key={visit.id} value={visit.id.toString()}>
                        Visit #{visit.id} - {visit.patient_name || 'Unknown Patient'} ({new Date(visit.created_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
            
            <div className={styles.formGroup}>
              <label>Scheduled Start Time</label>
              <input
                type="datetime-local"
                value={formData.scheduled_start}
                onChange={(e) => setFormData({ ...formData, scheduled_start: e.target.value })}
                required
              />
            </div>
            
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={formData.recording_enabled}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      recording_enabled: e.target.checked,
                      recording_consent_acknowledged: e.target.checked
                        ? formData.recording_consent_acknowledged
                        : false,
                    })
                  }
                />
                Enable Recording (recommended — enables automatic transcription)
              </label>
            </div>

            {formData.recording_enabled && (
              <div className={styles.formGroup}>
                <label>
                  <input
                    type="checkbox"
                    checked={formData.recording_consent_acknowledged}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        recording_consent_acknowledged: e.target.checked,
                      })
                    }
                    required
                  />
                  I confirm the patient has consented to audio/video recording for this consultation
                </label>
              </div>
            )}
            
            <div className={styles.formGroup}>
              <label>Notes (Optional)</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
              />
            </div>
            
            <div className={styles.formActions}>
              <button 
                type="submit" 
                disabled={creating || (!visitId && !selectedVisitId)} 
                className={styles.submitButton}
              >
                {creating ? 'Creating...' : 'Create Session'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  setSelectedVisitId(null);
                }}
                className={styles.cancelButton}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton />
      ) : !Array.isArray(sessions) || sessions.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No telemedicine sessions found.</p>
          {user?.role === 'DOCTOR' && (
            <div style={{ marginTop: '1rem' }}>
              <p style={{ marginBottom: '1rem', color: '#666' }}>
                {visitId 
                  ? `No sessions have been created for this visit yet. Create a session to start a video consultation.`
                  : `You haven't created any telemedicine sessions yet. Click the button above to create your first session.`}
              </p>
              <button
                onClick={() => setShowCreateForm(true)}
                className={styles.createButton}
              >
                {visitId ? 'Create Session for This Visit' : '+ Create Session'}
              </button>
            </div>
          )}
          {user?.role !== 'DOCTOR' && (
            <p style={{ color: '#666', marginTop: '0.5rem' }}>
              When a doctor invites you to a virtual clinic, it will appear here.
            </p>
          )}
        </div>
      ) : (
        <div className={styles.sessionsList}>
          {sessions.map((session) => {
            const isHost = user?.role === 'DOCTOR' && session.doctor === user.id;
            const canJoin =
              session.status === 'IN_PROGRESS' ||
              (session.status === 'SCHEDULED' &&
                (isHost || session.my_invite_status === 'ACCEPTED' || session.my_invite_status === 'PENDING'));
            return (
            <div key={session.id} className={styles.sessionCard}>
              <div className={styles.sessionHeader}>
                <div>
                  <h3>Session #{session.id}</h3>
                  <span className={`${styles.statusBadge} ${getStatusBadgeClass(session.status)}`}>
                    {session.status}
                  </span>
                  {session.my_clinic_role && session.my_clinic_role !== 'HOST' && (
                    <span className={styles.recordingBadge} style={{ marginLeft: 8 }}>
                      {session.my_clinic_role}
                    </span>
                  )}
                </div>
                {session.recording_enabled && (
                  <span className={styles.recordingBadge}>Recording on</span>
                )}
              </div>
              
              <div className={styles.sessionDetails}>
                <p><strong>Patient:</strong> {session.patient_name}</p>
                <p><strong>Doctor:</strong> {session.doctor_display_name || session.doctor_name}</p>
                <p><strong>Scheduled:</strong> {formatDateTime(session.scheduled_start)}</p>
                {session.actual_start && (
                  <p><strong>Started:</strong> {formatDateTime(session.actual_start)}</p>
                )}
                {session.duration_minutes && (
                  <p><strong>Duration:</strong> {session.duration_minutes.toFixed(1)} minutes</p>
                )}
                {session.notes && (
                  <p><strong>Notes:</strong> {session.notes}</p>
                )}
                {Array.isArray(session.participants) && session.participants.length > 0 && (
                  <p>
                    <strong>Team:</strong>{' '}
                    {session.participants
                      .filter((p) => p.invite_status !== 'REVOKED' && p.clinic_role !== 'PATIENT')
                      .map((p) => `${p.user_name}${p.clinic_role ? ` (${p.clinic_role})` : ''}`)
                      .join(', ') || 'Host only'}
                  </p>
                )}
              </div>
              
              <div className={styles.sessionActions}>
                {session.status === 'SCHEDULED' && isHost && (
                  <button
                    onClick={() => handleStartSession(session)}
                    className={styles.actionButton}
                  >
                    Start Session
                  </button>
                )}
                
                {canJoin && session.my_invite_status !== 'PENDING' && (
                  <button
                    onClick={() => handleJoinSession(session)}
                    className={styles.joinButton}
                  >
                    {isHost ? 'Join clinic' : 'Join as staff'}
                  </button>
                )}

                {isHost && (session.status === 'SCHEDULED' || session.status === 'IN_PROGRESS') && (
                  <button
                    type="button"
                    className={styles.actionButton}
                    onClick={() =>
                      setInvitePanelSessionId((id) => (id === session.id ? null : session.id))
                    }
                  >
                    {invitePanelSessionId === session.id ? 'Hide team' : 'Invite staff'}
                  </button>
                )}
                
                {session.status === 'IN_PROGRESS' && isHost && (
                  <button
                    onClick={() => handleEndSessionClick(session)}
                    className={styles.endButton}
                  >
                    End Session
                  </button>
                )}
                
                {session.status === 'COMPLETED' && session.recording_enabled && isHost && (
                  <>
                    {(session.transcription_status === 'PENDING' ||
                      session.transcription_status === 'PROCESSING') && (
                      <span className={styles.transcriptionStatus}>
                        Auto-transcription: {session.transcription_status.toLowerCase()}…
                      </span>
                    )}
                    {(!session.transcription_status || session.transcription_status === 'FAILED') &&
                      (session.recording_url || session.recording_sid) && (
                      <button
                        onClick={() => handleRequestTranscription(session)}
                        disabled={requestingTranscription === session.id}
                        className={styles.actionButton}
                      >
                        {requestingTranscription === session.id ? 'Retrying…' : 'Retry transcription'}
                      </button>
                    )}
                  </>
                )}
                
                {(session.recording_url || session.recording_sid) && (
                  <button
                    type="button"
                    onClick={() => handleViewRecording(session)}
                    disabled={loadingRecording === session.id}
                    className={styles.recordingLink}
                  >
                    {loadingRecording === session.id ? 'Loading…' : 'View Recording'}
                  </button>
                )}
              </div>

              {invitePanelSessionId === session.id && isHost && (
                <div style={{ marginTop: '1rem' }}>
                  <StaffInvitePanel
                    session={session}
                    canInvite
                    onUpdated={(participants) => {
                      setSessions((prev) =>
                        prev.map((s) =>
                          s.id === session.id ? { ...s, participants } : s,
                        ),
                      );
                    }}
                  />
                </div>
              )}
              
              {session.transcription_status === 'COMPLETED' && (
                <div className={styles.transcriptionBlock}>
                  <strong>Transcription:</strong>
                  <p className={styles.transcriptionText}>{session.transcription_text || '(Empty)'}</p>
                  {isHost && session.transcription_text && (
                    <button
                      type="button"
                      className={styles.actionButton}
                      onClick={() =>
                        navigate(`/visits/${session.visit}/consultation`, {
                          state: { telemedicineTranscript: session.transcription_text },
                        })
                      }
                    >
                      Use in Clinical Scribe
                    </button>
                  )}
                </div>
              )}
            </div>
            );
          })}
        </div>
      )}

      {endSessionModal && (
        <div className={styles.modalOverlay} onClick={() => !endingSession && setEndSessionModal(null)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>End telemedicine session?</h3>
            <p>This will end the video call for all participants.</p>
            {endSessionModal.session.recording_enabled && (
              <p className={styles.autoTranscriptHint}>
                Recording is enabled — transcription will start automatically when the session ends
                (live captions are saved when you leave the call).
              </p>
            )}
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={endSessionModal.addBilling}
                onChange={(e) => setEndSessionModal({ ...endSessionModal, addBilling: e.target.checked })}
              />
              Add telemedicine consultation to visit bill
            </label>
            <div className={styles.modalActions}>
              <button
                type="button"
                onClick={() => setEndSessionModal(null)}
                className={styles.cancelButton}
                disabled={endingSession}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEndSessionConfirm}
                className={styles.endButton}
                disabled={endingSession}
              >
                {endingSession ? 'Ending…' : 'End session'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
