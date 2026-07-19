/**
 * Landing Page
 *
 * Full-bleed geometric hero with capability cards (left) and headline content (right).
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiActivity,
  FiMic,
  FiShield,
  FiVideo,
} from 'react-icons/fi';
import HeroGeometric from '../components/landing/HeroGeometric';
import Logo from '../components/common/Logo';
import styles from '../styles/Landing.module.css';

const CAPABILITIES = [
  {
    icon: FiMic,
    title: 'AI Consultation Scribe',
    description: 'Voice-to-note documentation that flows straight into the chart.',
  },
  {
    icon: FiShield,
    title: 'NHIA-Ready Billing',
    description: 'Validated tariffs, claim packs, and compliance dashboards built in.',
  },
  {
    icon: FiVideo,
    title: 'Telemedicine',
    description: 'Secure video visits with live transcription and scribe handoff.',
  },
  {
    icon: FiActivity,
    title: 'Clinical Intelligence',
    description: 'Labs, radiology, antenatal schedules, and audit trails in one place.',
  },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <section className={styles.heroSplit} aria-label="Welcome">
        <HeroGeometric
          className={styles.heroGeometricFull}
          color1="#0D47A1"
          color2="#E8F4FC"
          speed={0.75}
        />

        <div className={styles.heroContentGrid}>
          <div className={styles.capabilitiesPane}>
            <section className={`${styles.capabilities} ${styles.reveal} ${styles.revealDelay1}`}>
              {CAPABILITIES.map((item) => (
                <article key={item.title} className={styles.capabilityCard}>
                  <div className={styles.capabilityIcon}>
                    {React.createElement(item.icon, { 'aria-hidden': true })}
                  </div>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                  </div>
                </article>
              ))}
            </section>
          </div>

          <div className={styles.heroOverlayPane}>
            <div className={styles.heroOverlay}>
              <header className={styles.topBar}>
                <div className={`${styles.reveal} ${styles.revealDelay1}`}>
                  <Logo size="medium" className={styles.navLogo} />
                </div>
                <button
                  type="button"
                  className={`${styles.navSignIn} ${styles.reveal} ${styles.revealDelay2}`}
                  onClick={() => navigate('/login')}
                >
                  Sign In
                </button>
              </header>

              <main className={styles.heroMain}>
                <div className={`${styles.eyebrow} ${styles.reveal} ${styles.revealDelay2}`}>
                  <span className={styles.eyebrowDot} />
                  Modern EMR for Lifeway Medical Centre
                </div>

                <h1 className={`${styles.heroTitle} ${styles.reveal} ${styles.revealDelay3}`}>
                  <span className={styles.titleLine}>Care that moves</span>
                  <span className={styles.titleAccent}>at the speed of life.</span>
                </h1>

                <p className={`${styles.heroSubtitle} ${styles.reveal} ${styles.revealDelay4}`}>
                  A premium clinical platform — secure records, intelligent workflows,
                  and NHIA-ready billing — designed for teams who refuse to compromise on care.
                </p>

                <div className={`${styles.heroActions} ${styles.reveal} ${styles.revealDelay5}`}>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    onClick={() => navigate('/login')}
                  >
                    Get Started
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => navigate('/register')}
                  >
                    Create Account
                  </button>
                </div>

                <div className={`${styles.statsRow} ${styles.reveal} ${styles.revealDelay6}`}>
                  <div className={styles.stat}>
                    <strong>HIPAA</strong>
                    <span>Compliant architecture</span>
                  </div>
                  <div className={styles.statDivider} />
                  <div className={styles.stat}>
                    <strong>24/7</strong>
                    <span>Secure cloud access</span>
                  </div>
                  <div className={styles.statDivider} />
                  <div className={styles.stat}>
                    <strong>GH</strong>
                    <span>NHIA &amp; local workflows</span>
                  </div>
                </div>
              </main>
            </div>
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>© 2026 Lifeway Medical Centre Ltd. All rights reserved.</p>
      </footer>
    </div>
  );
}
