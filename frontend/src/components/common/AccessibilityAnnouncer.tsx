/**
 * Accessibility Announcer Component
 * 
 * Provides screen reader announcements for dynamic content changes.
 */
import React, { useEffect, useState } from 'react';
import styles from '../../styles/AccessibilityAnnouncer.module.css';

interface AccessibilityAnnouncerProps {
  message: string;
  priority?: 'polite' | 'assertive';
}

export default function AccessibilityAnnouncer({ 
  message, 
  priority = 'polite' 
}: AccessibilityAnnouncerProps) {
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    if (message) {
      setAnnouncement(message);
      // Clear after announcement is read
      const timer = setTimeout(() => setAnnouncement(''), 1000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  return (
    <div
      className={styles.announcer}
      role="status"
      aria-live={priority}
      aria-atomic="true"
    >
      {announcement}
    </div>
  );
}
