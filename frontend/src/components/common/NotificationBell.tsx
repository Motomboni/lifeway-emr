/**
 * Notification Bell Component
 * 
 * Displays notification count and dropdown with pending orders.
 */
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../../contexts/NotificationContext';
import styles from '../../styles/NotificationBell.module.css';

export default function NotificationBell() {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleNotificationClick = (notification: { id: string; type: string; visitId: number }) => {
    markAsRead(notification.id);
    setIsOpen(false);

    switch (notification.type) {
      case 'lab_order':
        navigate('/lab-orders');
        break;
      case 'radiology_order':
        navigate('/radiology-orders');
        break;
      case 'prescription':
        navigate('/prescriptions');
        break;
      case 'prescription_dispensed':
        // Navigate to visit details page for nurses to administer drugs
        if (notification.visitId > 0) {
          navigate(`/visits/${notification.visitId}#prescriptions-section`);
        } else {
          navigate('/visits');
        }
        break;
      case 'patient_discharged':
        // Navigate to visit details page to view discharge information
        if (notification.visitId > 0) {
          navigate(`/visits/${notification.visitId}#admission-section`);
        } else {
          navigate('/visits');
        }
        break;
      case 'payment':
        // Navigate to visit details page for visit-scoped billing
        if (notification.visitId > 0) {
          navigate(`/visits/${notification.visitId}#billing-section`);
        } else {
          navigate('/visits');
        }
        break;
      case 'patient_verification':
        navigate('/patients/verification');
        break;
      default:
        if (notification.visitId > 0) {
          navigate(`/visits/${notification.visitId}`);
        }
    }
  };

  return (
    <div className={styles.notificationBell} ref={dropdownRef}>
      <button
        className={styles.bellButton}
        onClick={() => setIsOpen(!isOpen)}
        title="Notifications"
      >
        🔔
        {unreadCount > 0 && (
          <span className={styles.badge}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownHeader}>
            <h3>Notifications</h3>
            {unreadCount > 0 && (
              <button
                className={styles.markAllReadButton}
                onClick={markAllAsRead}
              >
                Mark all read
              </button>
            )}
          </div>

          <div className={styles.notificationsList}>
            {notifications.length === 0 ? (
              <div className={styles.emptyNotifications}>
                <p>No new notifications</p>
              </div>
            ) : (
              notifications.map((notification) => {
                const isRead = unreadCount === 0 || !unreadCount; // Simplified
                return (
                  <div
                    key={notification.id}
                    className={`${styles.notificationItem} ${!isRead ? styles.unread : ''}`}
                    onClick={() => handleNotificationClick(notification)}
                  >
                    <div className={styles.notificationContent}>
                      <p className={styles.notificationMessage}>{notification.message}</p>
                      <span className={styles.notificationTime}>
                        {notification.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    {notification.count > 1 && (
                      <span className={styles.countBadge}>{notification.count}</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
