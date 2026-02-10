/**
 * Loading Skeleton Component
 * 
 * Displays skeleton loaders while data is being fetched.
 */
import React from 'react';
import styles from '../../styles/ConsultationWorkspace.module.css';

export function ConsultationSkeleton() {
  return (
    <div className={styles.consultationWorkspace}>
      {/* Header Skeleton */}
      <div className={styles.consultationHeader}>
        <div className={`${styles.skeleton} ${styles.skeletonHeader}`} />
      </div>

      {/* Form Sections Skeleton */}
      <div className={styles.consultationForm}>
        <div className={`${styles.skeleton} ${styles.skeletonSection}`} />
        <div className={`${styles.skeleton} ${styles.skeletonSection}`} />
        <div className={`${styles.skeleton} ${styles.skeletonSection}`} />
        <div className={`${styles.skeleton} ${styles.skeletonSection}`} />
      </div>

      {/* Actions Skeleton */}
      <div className={styles.consultationActions}>
        <div className={`${styles.skeleton}`} style={{ width: '100px', height: '40px' }} />
        <div className={`${styles.skeleton}`} style={{ width: '150px', height: '40px' }} />
      </div>
    </div>
  );
}

export function HeaderSkeleton() {
  return (
    <div className={styles.consultationHeader}>
      <div className={`${styles.skeleton} ${styles.skeletonHeader}`} />
    </div>
  );
}

/**
 * Generic Loading Skeleton Component
 * Displays a simple skeleton loader with specified count
 */
export default function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={styles.skeleton}
          style={{
            width: '100%',
            height: '60px',
            marginBottom: '1rem',
            borderRadius: '4px',
          }}
        />
      ))}
    </div>
  );
}
