/**
 * Shared layout for staff auth pages (login, register, OTP).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../common/Logo';
import styles from '../../styles/AuthShell.module.css';

interface AuthShellProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}

export default function AuthShell({ title, subtitle, children, footer, wide }: AuthShellProps) {
  return (
    <div className={styles.shell}>
      <div className={`${styles.panel} ${wide ? styles.wide : ''}`}>
        <Link to="/" className={styles.homeLink}>
          ← Back to home
        </Link>
        <div className={styles.logoWrap}>
          <Logo size="medium" showText={false} />
        </div>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        {children}
        {footer}
      </div>
    </div>
  );
}
