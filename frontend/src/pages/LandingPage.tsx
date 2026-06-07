/**
 * Landing Page – Damianix EMR
 *
 * Modern, distinctive landing for the EMR product.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import styles from '../styles/Landing.module.css';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.landing}>
      <div className={styles.bg}>
        <div className={styles.bgGradient} />
        <div className={styles.bgGrid} />
      </div>

      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandIcon}>◇</span>
          <span className={styles.brandName}>Damianix EMR</span>
        </div>
        <nav className={styles.nav}>
          <button
            type="button"
            className={styles.navBtn}
            onClick={() => navigate('/login')}
          >
            Sign in
          </button>
          <button
            type="button"
            className={styles.navBtnPrimary}
            onClick={() => navigate('/register')}
          >
            Get started
          </button>
        </nav>
      </header>

      <main className={styles.hero}>
        <p className={styles.heroLabel}>Electronic Medical Records</p>
        <h1 className={styles.heroTitle}>
          One platform for
          <br />
          <span className={styles.heroHighlight}>modern healthcare</span>
        </h1>
        <p className={styles.heroSub}>
          Secure, compliant, and built for clinics. Patient records, billing, labs, and workflows in one place.
        </p>
        <div className={styles.heroCta}>
          <button
            type="button"
            className={styles.ctaPrimary}
            onClick={() => navigate('/login')}
          >
            Sign in
          </button>
          <button
            type="button"
            className={styles.ctaSecondary}
            onClick={() => navigate('/register')}
          >
            Create account
          </button>
        </div>
      </main>

      <section className={styles.features}>
        <div className={styles.featureCard}>
          <div className={styles.featureIconWrap}>
            <span className={styles.featureIcon} aria-hidden>🔒</span>
          </div>
          <h3>Secure and compliant</h3>
          <p>Role-based access, audit trails, and standards-aligned security.</p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIconWrap}>
            <span className={styles.featureIcon} aria-hidden>⚡</span>
          </div>
          <h3>Built for speed</h3>
          <p>Streamlined workflows for reception, clinical, and billing teams.</p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIconWrap}>
            <span className={styles.featureIcon} aria-hidden>📊</span>
          </div>
          <h3>Full picture</h3>
          <p>Unified patient records, labs, imaging, and reporting.</p>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} Damianix EMR. All rights reserved.</p>
      </footer>
    </div>
  );
}
