/**
 * Landing Page
 * 
 * Modern split-screen landing page for visitors.
 * Features hero section, key benefits, and call-to-action.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import Logo from '../components/common/Logo';
import styles from '../styles/Landing.module.css';

export default function LandingPage() {
  const navigate = useNavigate();

  const services = [
    "SINGLE/FAMILY REGISTRATION",
    "OUTPATIENT CONSULTATIONS (GENERAL & SPECIALIST)",
    "INPATIENT CARE AND MANAGEMENT",
    "ACCIDENT AND EMERGENCY",
    "FULLY AUTOMATED LABORATORY",
    "3D/4D ULTRASOUND SCANS",
    "RADIOLOGICAL INVESTIGATIONS (XRAYS)",
    "PHARMACY",
    "DENTAL CLINIC",
    "PAEDIATRIC CLINIC/IMMUNIZATIONS",
    "ANTENATAL CARE & DELIVERIES",
    "OBSTETRICS & GYNAECOLOGY",
    "FAMILY PLANNING CLINICS",
    "CERVICAL CANCER SCREENING, PAP SMEAR & HPV SCREENING",
    "INFERTILITY TREATMENT",
    "IUI, IVF, SURROGACY",
    "CLINICAL HAEMATOLOGY & HAEMATO-ONCOLOGY",
    "SICKLE CELL DISEASE & CANCER MANAGEMENT",
    "ENT, UROLOGY, NEUROLOGY, ENDOCRINOLOGY",
    "INTERNAL MEDICINE",
    "ADOLESCENT HEALTH",
    "COSMETIC SURGERY",
    "MINIMAL ACCESS/GENERAL SURGERIES",
    "FAMILY/INDIVIDUAL RETAINERSHIPS",
    "COMPANY/CORPORATE RETAINERSHIPS",
    "HEALTH INSURANCE",
  ];

  return (
    <div className={styles.landing}>
      {/* Left Side - Content */}
      <div className={styles.contentSide}>
        <div className={styles.content}>
          <Logo size="large" />
          
          <h2 className={styles.headline}>
            Quality Healthcare, Compassionate Care
          </h2>
          
          <p className={styles.subheadline}>
            Lifeway Medical Centre Ltd's comprehensive Electronic Medical Record system.
            Secure, efficient, and compliant with industry standards.
          </p>

          <div className={styles.features}>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>🔒</span>
              <div>
                <h3>Secure & Compliant</h3>
                <p>HIPAA-compliant with role-based access control</p>
              </div>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>⚡</span>
              <div>
                <h3>Fast & Efficient</h3>
                <p>Streamlined workflows for all medical staff</p>
              </div>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}>📊</span>
              <div>
                <h3>Comprehensive</h3>
                <p>Complete patient records and audit trails</p>
              </div>
            </div>
          </div>

          <section className={styles.servicesSection}>
            <h2 className={styles.servicesTitle}>OUR SERVICES</h2>
            <ul className={styles.servicesGrid}>
              {services.map((service) => (
                <li key={service} className={styles.servicesItem}>
                  {service}
                </li>
              ))}
            </ul>
          </section>

          <div className={styles.ctaButtons}>
            <button
              className={styles.primaryButton}
              onClick={() => navigate('/login')}
            >
              Sign In
            </button>
            <button
              className={styles.secondaryButton}
              onClick={() => navigate('/register')}
            >
              Create Account
            </button>
          </div>

          <div className={styles.footer}>
            <p>© 2026 Lifeway Medical Centre Ltd. All rights reserved.</p>
          </div>
        </div>
      </div>

      {/* Right Side - Visual */}
      <div className={styles.visualSide}>
        <div className={styles.visualContent}>
          <div className={styles.visualCard}>
            <div className={styles.cardHeader}>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.cardIcon}>📋</div>
              <h3>Patient Management</h3>
              <p>Complete patient records at your fingertips</p>
            </div>
          </div>

          <div className={styles.visualCard}>
            <div className={styles.cardHeader}>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.cardIcon}>💊</div>
              <h3>Clinical Workflow</h3>
              <p>Seamless consultation to prescription flow</p>
            </div>
          </div>

          <div className={styles.visualCard}>
            <div className={styles.cardHeader}>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
              <div className={styles.cardDot}></div>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.cardIcon}>🔍</div>
              <h3>Lab & Radiology</h3>
              <p>Integrated test ordering and results</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
