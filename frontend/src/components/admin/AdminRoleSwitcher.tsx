/**
 * Lets administrators switch into another staff role for end-to-end testing.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { fetchAssumableRoles } from '../../api/auth';
import { AssumableRoleOption, UserRole } from '../../types/auth';
import { formatRoleLabel } from '../../utils/roleContext';
import styles from '../../styles/RoleViewBanner.module.css';

export default function AdminRoleSwitcher({ compact = false }: { compact?: boolean }) {
  const { assumeRole, isViewingAsRole, user } = useAuth();
  const navigate = useNavigate();
  const [roles, setRoles] = useState<AssumableRoleOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchAssumableRoles();
        if (!cancelled) {
          setRoles(data.roles);
        }
      } catch {
        // Admin-only; ignore if unavailable
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleAssume = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    try {
      await assumeRole(selected as UserRole);
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  }, [assumeRole, navigate, selected]);

  if (isViewingAsRole) {
    return null;
  }

  return (
    <div className={compact ? styles.switcherCompact : styles.switcher} role="group">
      <label htmlFor="admin-role-select" className={styles.switcherLabel}>
        Test as role:
      </label>
      <select
        id="admin-role-select"
        className={styles.roleSelect}
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        disabled={loading}
      >
        <option value="">Choose role…</option>
        {roles.map((r) => (
          <option key={r.value} value={r.value}>
            {r.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={styles.assumeButton}
        onClick={handleAssume}
        disabled={!selected || loading}
      >
        {loading ? 'Switching…' : 'Switch'}
      </button>
      {!compact && user && (
        <span className={styles.hint}>
          Signed in as {formatRoleLabel(user.actual_role ?? user.role)}
        </span>
      )}
    </div>
  );
}

