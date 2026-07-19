/**
 * Invite clinical staff (nurse, specialist, etc.) into a virtual clinic room.
 */
import React, { useEffect, useState } from 'react';
import {
  fetchInvitableStaff,
  inviteTelemedicineStaff,
  revokeTelemedicineInvite,
} from '../../api/telemedicine';
import {
  TelemedicineClinicRole,
  TelemedicineInvitableStaff,
  TelemedicineParticipant,
  TelemedicineSession,
} from '../../types/telemedicine';
import { useToast } from '../../hooks/useToast';
import {
  VOICE_OPEN_INVITE_EVENT,
  consumePendingClinicInvite,
} from '../../utils/voiceIntents';
import styles from '../../styles/VirtualClinic.module.css';

interface StaffInvitePanelProps {
  session: TelemedicineSession;
  canInvite: boolean;
  onUpdated?: (sessionParticipants: TelemedicineParticipant[]) => void;
  compact?: boolean;
}

const ROLE_LABELS: Record<string, string> = {
  HOST: 'Host',
  PATIENT: 'Patient',
  NURSE: 'Nurse',
  SPECIALIST: 'Specialist',
  OBSERVER: 'Observer',
  STAFF: 'Staff',
};

function staffDisplayName(s: TelemedicineInvitableStaff): string {
  const name = `${s.first_name || ''} ${s.last_name || ''}`.trim();
  return name || s.username || s.email;
}

export default function StaffInvitePanel({
  session,
  canInvite,
  onUpdated,
  compact = false,
}: StaffInvitePanelProps) {
  const { showSuccess, showError } = useToast();
  const [staff, setStaff] = useState<TelemedicineInvitableStaff[]>([]);
  const [loading, setLoading] = useState(false);
  const [invitingId, setInvitingId] = useState<number | null>(null);
  const [revokingId, setRevokingId] = useState<number | null>(null);
  const [roleFilter, setRoleFilter] = useState<string>('NURSE');
  const [message, setMessage] = useState('Please join this virtual clinic visit.');
  const [participants, setParticipants] = useState<TelemedicineParticipant[]>(
    session.participants || [],
  );

  useEffect(() => {
    setParticipants(session.participants || []);
  }, [session.participants]);

  // Voice: "invite nurse" queues a role filter and opens this panel's list
  useEffect(() => {
    if (!canInvite) return;
    const applyRole = (role: string) => {
      setRoleFilter(role);
    };
    const pending = consumePendingClinicInvite();
    if (pending) applyRole(pending);

    const onVoiceInvite = (ev: Event) => {
      const detail = (ev as CustomEvent<{ role?: string }>).detail;
      if (detail?.role) applyRole(detail.role);
    };
    window.addEventListener(VOICE_OPEN_INVITE_EVENT, onVoiceInvite);
    return () => window.removeEventListener(VOICE_OPEN_INVITE_EVENT, onVoiceInvite);
  }, [canInvite, session.id]);

  useEffect(() => {
    if (!canInvite) return;
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const list = await fetchInvitableStaff(session.id, roleFilter || undefined);
        if (!cancelled) setStaff(Array.isArray(list) ? list : []);
      } catch (err: unknown) {
        if (!cancelled) {
          showError(err instanceof Error ? err.message : 'Failed to load staff');
          setStaff([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [session.id, canInvite, roleFilter, showError]);

  const invitedStaff = participants.filter(
    (p) => p.clinic_role && !['HOST', 'PATIENT'].includes(p.clinic_role) && p.invite_status !== 'REVOKED',
  );

  const handleInvite = async (userId: number, clinicRole?: TelemedicineClinicRole) => {
    try {
      setInvitingId(userId);
      const role =
        clinicRole ||
        (roleFilter === 'NURSE'
          ? 'NURSE'
          : roleFilter === 'DOCTOR'
            ? 'SPECIALIST'
            : 'STAFF');
      const participant = await inviteTelemedicineStaff(session.id, {
        user_id: userId,
        clinic_role: role as 'NURSE' | 'SPECIALIST' | 'OBSERVER' | 'STAFF',
        message,
      });
      const next = [
        ...participants.filter((p) => p.user !== userId),
        participant,
      ];
      setParticipants(next);
      setStaff((prev) => prev.filter((s) => s.id !== userId));
      onUpdated?.(next);
      showSuccess('Staff invited to the virtual clinic');
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Failed to invite staff');
    } finally {
      setInvitingId(null);
    }
  };

  const handleRevoke = async (participantId: number) => {
    try {
      setRevokingId(participantId);
      const updated = await revokeTelemedicineInvite(session.id, participantId);
      const next = participants.map((p) => (p.id === participantId ? updated : p));
      setParticipants(next);
      onUpdated?.(next);
      showSuccess('Invite revoked');
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Failed to revoke invite');
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className={`${styles.invitePanel} ${compact ? styles.invitePanelCompact : ''}`}>
      <div className={styles.inviteHeader}>
        <h3>Virtual clinic team</h3>
        <p>Invite a nurse or specialist to join this visit live.</p>
      </div>

      <ul className={styles.roster}>
        <li className={styles.rosterItem}>
          <span className={styles.rosterName}>{session.doctor_name || 'Doctor'}</span>
          <span className={styles.roleChip}>Host</span>
        </li>
        <li className={styles.rosterItem}>
          <span className={styles.rosterName}>{session.patient_name || 'Patient'}</span>
          <span className={`${styles.roleChip} ${styles.rolePatient}`}>Patient</span>
        </li>
        {invitedStaff.map((p) => (
          <li key={p.id} className={styles.rosterItem}>
            <span className={styles.rosterName}>
              {p.user_name}
              {p.invite_status === 'PENDING' ? ' · invited' : p.joined_at && !p.left_at ? ' · in room' : ''}
            </span>
            <span className={styles.rosterActions}>
              <span className={styles.roleChip}>
                {ROLE_LABELS[p.clinic_role || 'STAFF'] || p.clinic_role}
              </span>
              {canInvite && p.invite_status !== 'REVOKED' && (
                <button
                  type="button"
                  className={styles.revokeBtn}
                  disabled={revokingId === p.id}
                  onClick={() => handleRevoke(p.id)}
                >
                  {revokingId === p.id ? '…' : 'Remove'}
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>

      {canInvite && (
        <div className={styles.inviteForm}>
          <div className={styles.inviteControls}>
            <label>
              Role
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="NURSE">Nurses</option>
                <option value="DOCTOR">Doctors / specialists</option>
                <option value="LAB_TECH">Lab tech</option>
                <option value="PHARMACIST">Pharmacist</option>
                <option value="RADIOLOGY_TECH">Radiology</option>
                <option value="">All clinical staff</option>
              </select>
            </label>
            <label className={styles.messageField}>
              Note
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={255}
                placeholder="Optional invite note"
              />
            </label>
          </div>

          {loading ? (
            <p className={styles.muted}>Loading staff…</p>
          ) : staff.length === 0 ? (
            <p className={styles.muted}>No available staff for this filter.</p>
          ) : (
            <ul className={styles.staffList}>
              {staff.map((s) => (
                <li key={s.id} className={styles.staffRow}>
                  <div>
                    <strong>{staffDisplayName(s)}</strong>
                    <span className={styles.muted}> · {s.role.replace(/_/g, ' ')}</span>
                  </div>
                  <button
                    type="button"
                    className={styles.inviteBtn}
                    disabled={invitingId === s.id}
                    onClick={() => handleInvite(s.id)}
                  >
                    {invitingId === s.id ? 'Inviting…' : 'Invite'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
