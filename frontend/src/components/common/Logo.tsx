/**
 * Logo Component for Damianix EMR
 *
 * Landing-style brand: ◇ icon + "Damianix EMR" text.
 * Uses emerald accent for consistency across the app.
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
      <span className={styles.logoIcon}>◇</span>
      {showText && (
        <span className={styles.logoText}>Damianix EMR</span>
      )}
    </div>
  );
}
