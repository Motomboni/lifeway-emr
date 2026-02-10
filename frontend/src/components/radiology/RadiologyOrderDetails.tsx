/**
 * Radiology Order Details Component
 * 
 * Displays radiology order details with OHIF viewer integration.
 */
import React, { useState, useEffect } from 'react';
import { getRadiologyOrder } from '../../api/radiologyOrders';
import StudySeriesBrowser from './StudySeriesBrowser';
import OHIFViewer from './OHIFViewer';
import { useToast } from '../../hooks/useToast';
import LoadingSkeleton from '../common/LoadingSkeleton';
import styles from './RadiologyOrderDetails.module.css';

interface RadiologyOrderDetailsProps {
  orderId: number;
  visitId: number;
  onClose?: () => void;
}

const RadiologyOrderDetails: React.FC<RadiologyOrderDetailsProps> = ({
  orderId,
  visitId,
  onClose,
}) => {
  const { showError } = useToast();
  const [order, setOrder] = useState<any>(null);
  const [studyId, setStudyId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'browser' | 'viewer'>('browser');

  useEffect(() => {
    loadOrderDetails();
  }, [orderId, visitId]);

  const loadOrderDetails = async () => {
    try {
      setLoading(true);
      const orderData = await getRadiologyOrder(visitId, orderId);
      setOrder(orderData);
      
      // Try to get study ID from order
      if (orderData.study_id) {
        setStudyId(orderData.study_id);
      } else if (orderData.studies && orderData.studies.length > 0) {
        setStudyId(orderData.studies[0].id);
      }
    } catch (error: any) {
      showError('Failed to load radiology order details');
      console.error('Error loading order:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  if (!order) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Order not found</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h2>Radiology Order #{order.id}</h2>
          <p className={styles.orderInfo}>
            Patient: {order.patient_name || 'Unknown'} | 
            Study Type: {order.study_type || 'N/A'} |
            Status: {order.status}
          </p>
        </div>
        <div className={styles.headerActions}>
          {studyId && (
            <>
              <button
                onClick={() => setViewMode('browser')}
                className={viewMode === 'browser' ? styles.activeButton : styles.button}
              >
                Study Browser
              </button>
              <button
                onClick={() => setViewMode('viewer')}
                className={viewMode === 'viewer' ? styles.activeButton : styles.button}
              >
                OHIF Viewer
              </button>
            </>
          )}
          {onClose && (
            <button onClick={onClose} className={styles.closeButton}>
              Close
            </button>
          )}
        </div>
      </div>

      <div className={styles.content}>
        {studyId ? (
          viewMode === 'browser' ? (
            <StudySeriesBrowser
              studyId={studyId}
              radiologyOrderId={orderId}
            />
          ) : (
            <OHIFViewer
              studyId={studyId}
              radiologyOrderId={orderId}
            />
          )
        ) : (
          <div className={styles.emptyState}>
            <p>No study found for this order. Images may not have been uploaded yet.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RadiologyOrderDetails;

