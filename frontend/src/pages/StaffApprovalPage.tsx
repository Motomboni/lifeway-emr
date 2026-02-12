/**
 * Staff Approval Page
 *
 * Admin/Superuser page to approve staff registrations before they can log in.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchPendingStaff, approveStaffUser } from '../api/auth';
import { User } from '../types/auth';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/StaffApproval.module.css';

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Administrator',
  DOCTOR: 'Doctor',
  NURSE: 'Nurse',
  LAB_TECH: 'Lab Technician',
  RADIOLOGY_TECH: 'Radiology Technician',
  PHARMACIST: 'Pharmacist',
  RECEPTIONIST: 'Receptionist',
  IVF_SPECIALIST: 'IVF Specialist',
  EMBRYOLOGIST: 'Embryologist',
};

export default function StaffApprovalPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [pendingStaff, setPendingStaff] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  const isAdmin = user?.is_superuser === true || user?.role === 'ADMIN';

  useEffect(() => {
    if (!isAdmin) {
      showError('Access denied. Only administrators can approve staff.');
      navigate('/dashboard');
      return;
    }
    loadPendingStaff();
  }, [isAdmin, navigate, showError]);

  const loadPendingStaff = async () => {
    try {
      setLoading(true);
      const staff = await fetchPendingStaff();
      setPendingStaff(staff);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load pending staff';
      showError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (staffUser: User) => {
    try {
      setApprovingId(staffUser.id);
      await approveStaffUser(staffUser.id);
      showSuccess(`${staffUser.first_name} ${staffUser.last_name} has been approved and can now log in.`);
      setPendingStaff((prev) => prev.filter((u) => u.id !== staffUser.id));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to approve staff';
      showError(msg);
    } finally {
      setApprovingId(null);
    }
  };

  if (!isAdmin) return null;

  return (
    <div className={styles.container}>
      <BackToDashboard />

      <div className={styles.header}>
        <h1>Staff Approval</h1>
        <p className={styles.subtitle}>
          Approve staff registrations before they can access the system.
        </p>
      </div>

      {loading ? (
        <LoadingSkeleton count={3} />
      ) : pendingStaff.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No staff awaiting approval.</p>
          <p className={styles.emptyHint}>
            Staff who register will appear here until an administrator approves their account.
          </p>
        </div>
      ) : (
        <div className={styles.staffList}>
          {pendingStaff.map((staff) => (
            <div key={staff.id} className={styles.staffCard}>
              <div className={styles.staffInfo}>
                <h3>
                  {staff.first_name} {staff.last_name}
                </h3>
                <p className={styles.role}>{ROLE_LABELS[staff.role] || staff.role}</p>
                <p className={styles.details}>
                  {staff.username} · {staff.email}
                </p>
                <p className={styles.registered}>
                  Registered: {staff.date_joined ? new Date(staff.date_joined).toLocaleDateString() : '—'}
                </p>
              </div>
              <button
                className={styles.approveButton}
                onClick={() => handleApprove(staff)}
                disabled={approvingId === staff.id}
              >
                {approvingId === staff.id ? 'Approving...' : 'Approve'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
