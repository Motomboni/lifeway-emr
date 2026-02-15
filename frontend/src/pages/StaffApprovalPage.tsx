/**
 * Staff Management Page
 *
 * Admin/Superuser page to:
 * - Approve staff registrations before they can log in
 * - Deactivate staff (Superuser only)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchPendingStaff, approveStaffUser, fetchAllStaff, deactivateStaffUser } from '../api/auth';
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

  const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
  const [pendingStaff, setPendingStaff] = useState<User[]>([]);
  const [allStaff, setAllStaff] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [deactivatingId, setDeactivatingId] = useState<number | null>(null);

  const isAdmin = user?.is_superuser === true || user?.role === 'ADMIN';
  const isSuperuser = user?.is_superuser === true;

  useEffect(() => {
    if (!isAdmin) {
      showError('Access denied. Only administrators can manage staff.');
      navigate('/dashboard');
      return;
    }
    loadPendingStaff();
    if (isSuperuser) {
      loadAllStaff();
    }
  }, [isAdmin, isSuperuser, navigate, showError]);

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

  const loadAllStaff = async () => {
    try {
      const staff = await fetchAllStaff();
      setAllStaff(staff);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load staff';
      showError(msg);
    }
  };

  const handleApprove = async (staffUser: User) => {
    try {
      setApprovingId(staffUser.id);
      await approveStaffUser(staffUser.id);
      showSuccess(`${staffUser.first_name} ${staffUser.last_name} has been approved and can now log in.`);
      setPendingStaff((prev) => prev.filter((u) => u.id !== staffUser.id));
      if (isSuperuser) loadAllStaff();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to approve staff';
      showError(msg);
    } finally {
      setApprovingId(null);
    }
  };

  const handleDeactivate = async (staffUser: User) => {
    if (!window.confirm(`Deactivate ${staffUser.first_name} ${staffUser.last_name}? They will no longer be able to log in.`)) {
      return;
    }
    try {
      setDeactivatingId(staffUser.id);
      await deactivateStaffUser(staffUser.id);
      showSuccess(`${staffUser.first_name} ${staffUser.last_name} has been deactivated.`);
      setAllStaff((prev) => prev.map((u) => (u.id === staffUser.id ? { ...u, is_active: false } : u)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to deactivate staff';
      showError(msg);
    } finally {
      setDeactivatingId(null);
    }
  };

  if (!isAdmin) return null;

  return (
    <div className={styles.container}>
      <BackToDashboard />

      <div className={styles.header}>
        <h1>Staff Management</h1>
        <p className={styles.subtitle}>
          Approve new staff and manage existing staff accounts.
        </p>
      </div>

      {isSuperuser && (
        <div className={styles.tabs}>
          <button
            className={activeTab === 'pending' ? styles.tabActive : styles.tab}
            onClick={() => setActiveTab('pending')}
          >
            Pending Approval {pendingStaff.length > 0 && `(${pendingStaff.length})`}
          </button>
          <button
            className={activeTab === 'all' ? styles.tabActive : styles.tab}
            onClick={() => { setActiveTab('all'); loadAllStaff(); }}
          >
            All Staff
          </button>
        </div>
      )}

      {activeTab === 'pending' && (
        <>
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
                    <h3>{staff.first_name} {staff.last_name}</h3>
                    <p className={styles.role}>{ROLE_LABELS[staff.role] || staff.role}</p>
                    <p className={styles.details}>{staff.username} · {staff.email}</p>
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
        </>
      )}

      {activeTab === 'all' && isSuperuser && (
        <>
          {allStaff.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No staff found.</p>
            </div>
          ) : (
            <div className={styles.staffList}>
              {allStaff.map((staff) => (
                <div key={staff.id} className={styles.staffCard}>
                  <div className={styles.staffInfo}>
                    <h3>{staff.first_name} {staff.last_name}</h3>
                    <p className={styles.role}>
                      {ROLE_LABELS[staff.role] || staff.role}
                      {!staff.is_active && <span className={styles.inactiveBadge}> (Deactivated)</span>}
                    </p>
                    <p className={styles.details}>{staff.username} · {staff.email}</p>
                    <p className={styles.registered}>
                      Joined: {staff.date_joined ? new Date(staff.date_joined).toLocaleDateString() : '—'}
                    </p>
                  </div>
                  {staff.is_active && staff.id !== user?.id && (
                    <button
                      className={styles.deactivateButton}
                      onClick={() => handleDeactivate(staff)}
                      disabled={deactivatingId === staff.id}
                    >
                      {deactivatingId === staff.id ? 'Deactivating...' : 'Deactivate'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
