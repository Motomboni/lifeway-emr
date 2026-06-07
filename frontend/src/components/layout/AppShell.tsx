/**
 * App shell — fixed admin role-testing bar + content offset.
 */
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import RoleViewBanner from '../admin/RoleViewBanner';
import styles from '../../styles/AppShell.module.css';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, isViewingAsRole } = useAuth();
  const showBanner = isAuthenticated && (isAdmin || isViewingAsRole);

  return (
    <div className={showBanner ? styles.shellWithBanner : styles.shell}>
      {showBanner && <RoleViewBanner />}
      <div className={styles.content}>{children}</div>
    </div>
  );
}
