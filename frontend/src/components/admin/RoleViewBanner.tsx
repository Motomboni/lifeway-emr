/**
 * Global banner for admin role testing — switch roles or exit view-as mode.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { fetchAssumableRoles } from '../../api/auth';
import { formatRoleLabel, isAdminUser } from '../../utils/roleContext';
import AdminRoleSwitcher from './AdminRoleSwitcher';
import styles from '../../styles/RoleViewBanner.module.css';

export default function RoleViewBanner() {
  const { user, isAuthenticated, isAdmin, isViewingAsRole, clearAssumedRole } = useAuth();
  const navigate = useNavigate();
  const [exiting, setExiting] = useState(false);
  const [canAssumeRoles, setCanAssumeRoles] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !user) {
      setCanAssumeRoles(null);
      return;
    }

    if (isAdmin || isViewingAsRole) {
      setCanAssumeRoles(true);
      return;
    }

    let cancelled = false;
    fetchAssumableRoles()
      .then(() => {
        if (!cancelled) setCanAssumeRoles(true);
      })
      .catch(() => {
        if (!cancelled) setCanAssumeRoles(isAdminUser(user));
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isAdmin, isViewingAsRole, user]);

  const handleExit = useCallback(async () => {
    setExiting(true);
    try {
      await clearAssumedRole();
      navigate('/dashboard');
    } finally {
      setExiting(false);
    }
  }, [clearAssumedRole, navigate]);

  if (!isAuthenticated || canAssumeRoles === false) {
    return null;
  }

  if (canAssumeRoles === null) {
    return null;
  }

  return (
    <div
      className={isViewingAsRole ? styles.bannerViewing : styles.bannerAdmin}
      role="region"
      aria-label="Administrator role testing"
    >
      {isViewingAsRole ? (
        <>
          <span className={styles.bannerText}>
            <strong>Viewing as {formatRoleLabel(user?.role)}</strong>
            <span className={styles.bannerSub}>
              Admin: {user?.first_name} {user?.last_name}
            </span>
          </span>
          <button
            type="button"
            className={styles.exitButton}
            onClick={handleExit}
            disabled={exiting}
          >
            {exiting ? 'Returning…' : 'Exit test mode'}
          </button>
        </>
      ) : (
        <AdminRoleSwitcher compact />
      )}
    </div>
  );
}
