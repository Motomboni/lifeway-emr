/**
 * Per-clinic branding in app header (SaaS differentiator).
 */
import React from 'react';
import { useOrganization } from '../../contexts/OrganizationContext';
import Logo from './Logo';
import styles from '../../styles/ClinicBranding.module.css';

interface ClinicBrandingProps {
  size?: 'small' | 'medium' | 'large';
}

export default function ClinicBranding({ size = 'medium' }: ClinicBrandingProps) {
  const { organization, loading } = useOrganization();

  if (loading) {
    return <Logo size={size} />;
  }

  if (!organization) {
    return <Logo size={size} />;
  }

  return (
    <div className={styles.branding}>
      {organization.logo_url ? (
        <img
          src={organization.logo_url}
          alt={organization.name}
          className={styles.logoImg}
        />
      ) : (
        <span className={styles.logoMark}>{organization.name.charAt(0)}</span>
      )}
      <div className={styles.text}>
        <span className={styles.clinicName}>{organization.name}</span>
        <span className={styles.poweredBy}>Damianix EMR</span>
      </div>
    </div>
  );
}
