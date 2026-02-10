/**
 * Logo Component for Lifeway Medical Centre Ltd
 *
 * Displays the official Lifeway Medical Centre Ltd logo across the application.
 * Title uses var(--text-primary) so it contrasts in both light and dark mode.
 */
import React from 'react';
import styles from '../../styles/Logo.module.css';

interface LogoProps {
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
  className?: string;
}

export default function Logo({ size = 'medium', showText = true, className }: LogoProps) {
  return (
    <div className={`${styles.logo} ${styles[size]} ${className || ''}`}>
      <img
        src="/LMC logo1.png"
        alt="Lifeway Medical Centre Ltd Logo"
        className={styles.logoImage}
        onError={(e) => {
          const target = e.target as HTMLImageElement;
          target.style.display = 'none';
          if (target.nextElementSibling) {
            (target.nextElementSibling as HTMLElement).style.display = 'block';
          }
        }}
      />
      <div className={styles.logoFallback} style={{ display: 'none' }}>
        <span className={styles.logoIcon}>🏥</span>
      </div>
      {showText && (
        <h1 className={styles.logoText}>Lifeway Medical Centre Ltd</h1>
      )}
    </div>
  );
}
