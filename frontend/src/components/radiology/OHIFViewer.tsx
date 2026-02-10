/**
 * OHIF Viewer Component
 * 
 * Integrates OHIF (Open Health Imaging Foundation) DICOM viewer
 * for displaying radiology studies and series.
 */
import React, { useEffect, useRef, useState } from 'react';
import LockIndicator from '../locks/LockIndicator';
import { useActionLock } from '../../hooks/useActionLock';
import styles from './OHIFViewer.module.css';

interface OHIFViewerProps {
  studyId: number;
  radiologyOrderId?: number;
  viewerUrl?: string;
  onError?: (error: Error) => void;
}

const OHIFViewer: React.FC<OHIFViewerProps> = ({
  studyId,
  radiologyOrderId,
  viewerUrl,
  onError,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actualViewerUrl, setActualViewerUrl] = useState<string | null>(null);

  // Check if radiology viewing is locked (if order ID provided)
  const viewLock = useActionLock({
    actionType: 'radiology_view',
    params: { radiology_request_id: radiologyOrderId || 0 },
    enabled: !!radiologyOrderId,
  });

  // Fetch viewer URL if not provided
  useEffect(() => {
    const fetchViewerUrl = async () => {
      if (viewerUrl) {
        setActualViewerUrl(viewerUrl);
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`/api/v1/radiology/studies/${studyId}/viewer-url/`);
        if (!response.ok) {
          throw new Error('Failed to fetch viewer URL');
        }
        const data = await response.json();
        setActualViewerUrl(data.viewer_url);
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to load viewer';
        setError(errorMessage);
        if (onError) {
          onError(new Error(errorMessage));
        }
      } finally {
        setLoading(false);
      }
    };

    fetchViewerUrl();
  }, [studyId, viewerUrl, onError]);

  // Handle iframe load
  const handleIframeLoad = () => {
    setLoading(false);
  };

  // Handle iframe error
  const handleIframeError = () => {
    const errorMessage = 'Failed to load OHIF viewer';
    setError(errorMessage);
    if (onError) {
      onError(new Error(errorMessage));
    }
    setLoading(false);
  };

  if (viewLock.isLocked && viewLock.lockResult) {
    return (
      <div className={styles.viewerContainer}>
        <LockIndicator
          lockResult={viewLock.lockResult}
          loading={viewLock.loading}
          variant="card"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.viewerContainer}>
        <div className={styles.errorContainer}>
          <h3>Viewer Error</h3>
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  if (loading || !actualViewerUrl) {
    return (
      <div className={styles.viewerContainer}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner} />
          <p>Loading OHIF viewer...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.viewerContainer}>
      <iframe
        ref={iframeRef}
        src={actualViewerUrl}
        className={styles.viewerIframe}
        title="OHIF DICOM Viewer"
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        allow="fullscreen"
      />
    </div>
  );
};

export default OHIFViewer;

