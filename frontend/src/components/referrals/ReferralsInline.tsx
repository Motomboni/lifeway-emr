/**
 * Referrals Inline Component
 * 
 * Inline component for managing patient referrals within consultation workspace.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import {
  fetchReferrals,
  createReferral,
  updateReferral,
  acceptReferral,
  completeReferral,
} from '../../api/referrals';
import { Referral, ReferralCreate, ReferralSpecialty, ReferralUrgency } from '../../types/referrals';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ReferralsInlineProps {
  visitId: string;
  consultationId?: number;
}

export default function ReferralsInline({ visitId, consultationId }: ReferralsInlineProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState<ReferralCreate>({
    consultation: consultationId || 0,
    specialty: 'OTHER',
    specialist_name: '',
    specialist_contact: '',
    reason: '',
    clinical_summary: '',
    urgency: 'ROUTINE',
  });

  useEffect(() => {
    loadReferrals();
  }, [visitId]);

  useEffect(() => {
    if (consultationId) {
      setFormData(prev => ({ ...prev, consultation: consultationId }));
    }
  }, [consultationId]);

  const loadReferrals = async () => {
    try {
      setLoading(true);
      const data = await fetchReferrals(parseInt(visitId));
      setReferrals(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load referrals');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!consultationId) {
      showError('Consultation must be created before making referrals');
      return;
    }
    
    try {
      setSaving(true);
      await createReferral(parseInt(visitId), {
        ...formData,
        consultation: consultationId,
      });
      showSuccess('Referral created successfully');
      setShowForm(false);
      setFormData({
        consultation: consultationId,
        specialty: 'OTHER',
        specialist_name: '',
        specialist_contact: '',
        reason: '',
        clinical_summary: '',
        urgency: 'ROUTINE',
      });
      await loadReferrals();
    } catch (error: any) {
      showError(error.message || 'Failed to create referral');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusUpdate = async (referral: Referral, newStatus: string) => {
    try {
      if (newStatus === 'ACCEPTED' && referral.status === 'PENDING') {
        await acceptReferral(parseInt(visitId), referral.id);
      } else if (newStatus === 'COMPLETED' && referral.status === 'ACCEPTED') {
        await completeReferral(parseInt(visitId), referral.id);
      } else {
        await updateReferral(parseInt(visitId), referral.id, {
          status: newStatus as any,
        });
      }
      showSuccess('Referral status updated');
      await loadReferrals();
    } catch (error: any) {
      showError(error.message || 'Failed to update referral status');
    }
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'PENDING':
        return styles.statusPending;
      case 'ACCEPTED':
        return styles.statusAccepted;
      case 'REJECTED':
        return styles.statusRejected;
      case 'COMPLETED':
        return styles.statusCompleted;
      case 'CANCELLED':
        return styles.statusCancelled;
      default:
        return '';
    }
  };

  const getUrgencyBadgeClass = (urgency: string) => {
    switch (urgency) {
      case 'ROUTINE':
        return styles.urgencyRoutine;
      case 'URGENT':
        return styles.urgencyUrgent;
      case 'EMERGENCY':
        return styles.urgencyEmergency;
      default:
        return '';
    }
  };

  const isDoctor = user?.role === 'DOCTOR';
  const canCreate = isDoctor && consultationId;

  if (loading) {
    return (
      <div className={styles.inlineCard}>
        <div className={styles.cardHeader}>
          <h3>Referrals</h3>
        </div>
        <p>Loading referrals...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineCard}>
      <div className={styles.cardHeader}>
        <h3>Referrals</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ Create Referral'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.referralForm}>
          <div className={styles.formRow}>
            <label>
              Specialty <span className={styles.required}>*</span>
              <select
                value={formData.specialty}
                onChange={(e) =>
                  setFormData({ ...formData, specialty: e.target.value as ReferralSpecialty })
                }
                required
              >
                <option value="CARDIOLOGY">Cardiology</option>
                <option value="DERMATOLOGY">Dermatology</option>
                <option value="ENDOCRINOLOGY">Endocrinology</option>
                <option value="GASTROENTEROLOGY">Gastroenterology</option>
                <option value="HEMATOLOGY">Hematology</option>
                <option value="INFECTIOUS_DISEASE">Infectious Disease</option>
                <option value="NEPHROLOGY">Nephrology</option>
                <option value="NEUROLOGY">Neurology</option>
                <option value="ONCOLOGY">Oncology</option>
                <option value="OPHTHALMOLOGY">Ophthalmology</option>
                <option value="ORTHOPEDICS">Orthopedics</option>
                <option value="OTOLARYNGOLOGY">Otolaryngology</option>
                <option value="PEDIATRICS">Pediatrics</option>
                <option value="PSYCHIATRY">Psychiatry</option>
                <option value="PULMONOLOGY">Pulmonology</option>
                <option value="RHEUMATOLOGY">Rheumatology</option>
                <option value="UROLOGY">Urology</option>
                <option value="OTHER">Other</option>
              </select>
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Specialist Name <span className={styles.required}>*</span>
              <input
                type="text"
                value={formData.specialist_name}
                onChange={(e) =>
                  setFormData({ ...formData, specialist_name: e.target.value })
                }
                required
                placeholder="Name of specialist or clinic"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Specialist Contact
              <input
                type="text"
                value={formData.specialist_contact}
                onChange={(e) =>
                  setFormData({ ...formData, specialist_contact: e.target.value })
                }
                placeholder="Phone, email, or address"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Reason for Referral <span className={styles.required}>*</span>
              <textarea
                value={formData.reason}
                onChange={(e) =>
                  setFormData({ ...formData, reason: e.target.value })
                }
                required
                rows={3}
                placeholder="Reason for referral"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Clinical Summary
              <textarea
                value={formData.clinical_summary}
                onChange={(e) =>
                  setFormData({ ...formData, clinical_summary: e.target.value })
                }
                rows={4}
                placeholder="Clinical summary for the specialist"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Urgency
              <select
                value={formData.urgency}
                onChange={(e) =>
                  setFormData({ ...formData, urgency: e.target.value as ReferralUrgency })
                }
              >
                <option value="ROUTINE">Routine</option>
                <option value="URGENT">Urgent</option>
                <option value="EMERGENCY">Emergency</option>
              </select>
            </label>
          </div>

          <div className={styles.formActions}>
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={saving}
            >
              {saving ? 'Creating...' : 'Create Referral'}
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {!consultationId && (
        <p className={styles.infoText}>
          Consultation must be created before making referrals.
        </p>
      )}

      {referrals.length === 0 ? (
        <p className={styles.emptyText}>No referrals for this visit</p>
      ) : (
        <div className={styles.referralsList}>
          {referrals.map((referral) => (
            <div key={referral.id} className={styles.referralCard}>
              <div className={styles.referralHeader}>
                <div>
                  <strong>{referral.specialty.replace('_', ' ')}</strong>
                  <span className={getUrgencyBadgeClass(referral.urgency)}>
                    {referral.urgency}
                  </span>
                  <span className={getStatusBadgeClass(referral.status)}>
                    {referral.status}
                  </span>
                </div>
              </div>
              
              <div className={styles.referralDetails}>
                <p><strong>Specialist:</strong> {referral.specialist_name}</p>
                {referral.specialist_contact && (
                  <p><strong>Contact:</strong> {referral.specialist_contact}</p>
                )}
                <p><strong>Reason:</strong> {referral.reason}</p>
                {referral.clinical_summary && (
                  <p><strong>Clinical Summary:</strong> {referral.clinical_summary}</p>
                )}
                {referral.specialist_notes && (
                  <p><strong>Specialist Notes:</strong> {referral.specialist_notes}</p>
                )}
                <div className={styles.referralMeta}>
                  <span>Referred by: {referral.referred_by_name}</span>
                  <span>Created: {formatDateTime(referral.created_at)}</span>
                  {referral.accepted_at && (
                    <span>Accepted: {formatDateTime(referral.accepted_at)}</span>
                  )}
                  {referral.completed_at && (
                    <span>Completed: {formatDateTime(referral.completed_at)}</span>
                  )}
                </div>
              </div>

              {(user?.role === 'DOCTOR' || user?.role === 'RECEPTIONIST') && (
                <div className={styles.referralActions}>
                  {referral.status === 'PENDING' && (
                    <>
                      <button
                        type="button"
                        className={styles.acceptButton}
                        onClick={() => handleStatusUpdate(referral, 'ACCEPTED')}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        className={styles.cancelButton}
                        onClick={() => handleStatusUpdate(referral, 'CANCELLED')}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                  {referral.status === 'ACCEPTED' && (
                    <button
                      type="button"
                      className={styles.completeButton}
                      onClick={() => handleStatusUpdate(referral, 'COMPLETED')}
                    >
                      Mark Complete
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
