/**
 * Study/Series Browser Component
 * 
 * Displays radiology studies grouped by series with image thumbnails.
 * Allows navigation to OHIF viewer.
 */
import React, { useState, useEffect } from 'react';
import { getStudy, getStudyImages, RadiologyStudy, RadiologySeries, RadiologyImage } from '../../api/radiology';
import OHIFViewer from './OHIFViewer';
import styles from './StudySeriesBrowser.module.css';

interface StudySeriesBrowserProps {
  studyId: number;
  radiologyOrderId?: number;
  onImageClick?: (image: RadiologyImage) => void;
}

const StudySeriesBrowser: React.FC<StudySeriesBrowserProps> = ({
  studyId,
  radiologyOrderId,
  onImageClick,
}) => {
  const [study, setStudy] = useState<RadiologyStudy | null>(null);
  const [series, setSeries] = useState<RadiologySeries[]>([]);
  const [images, setImages] = useState<Record<number, RadiologyImage[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<number | null>(null);
  const [showViewer, setShowViewer] = useState(false);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);

  useEffect(() => {
    loadStudyData();
  }, [studyId]);

  const loadStudyData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load study details
      const studyData = await getStudy(studyId);
      setStudy(studyData);

      // Load study images grouped by series
      const imagesData = await getStudyImages(studyId);
      
      // Group images by series
      const seriesMap: Record<number, RadiologySeries> = {};
      const imagesBySeries: Record<number, RadiologyImage[]> = {};

      imagesData.series.forEach((seriesItem: any) => {
        // Create full series object from API response
        const fullSeries: RadiologySeries = {
          id: seriesItem.id,
          series_uid: seriesItem.series_uid,
          series_number: seriesItem.series_number,
          modality: seriesItem.modality,
          body_part: seriesItem.body_part || '',
          description: seriesItem.description || '',
          study: studyId,
          created_at: seriesItem.created_at || new Date().toISOString(),
          updated_at: seriesItem.updated_at || new Date().toISOString(),
        };
        seriesMap[seriesItem.id] = fullSeries;
        imagesBySeries[seriesItem.id] = seriesItem.images || [];
      });

      setSeries(Object.values(seriesMap));
      setImages(imagesBySeries);
    } catch (err: any) {
      setError(err.message || 'Failed to load study data');
      console.error('Error loading study:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewInOHIF = async () => {
    try {
      // Fetch viewer URL
      const response = await fetch(`/api/v1/radiology/studies/${studyId}/viewer-url/`);
      if (!response.ok) {
        throw new Error('Failed to fetch viewer URL');
      }
      const data = await response.json();
      setViewerUrl(data.viewer_url);
      setShowViewer(true);
    } catch (err: any) {
      setError(err.message || 'Failed to open viewer');
    }
  };

  if (loading) {
    return (
      <div className={styles.browserContainer}>
        <div className={styles.loading}>Loading study data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.browserContainer}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  if (!study) {
    return (
      <div className={styles.browserContainer}>
        <div className={styles.error}>Study not found</div>
      </div>
    );
  }

  if (showViewer && viewerUrl) {
    return (
      <div className={styles.viewerWrapper}>
        <div className={styles.viewerHeader}>
          <button onClick={() => setShowViewer(false)} className={styles.backButton}>
            ← Back to Study
          </button>
          <h3>{study.description || `Study ${study.id}`}</h3>
        </div>
        <OHIFViewer
          studyId={studyId}
          radiologyOrderId={radiologyOrderId}
          viewerUrl={viewerUrl}
        />
      </div>
    );
  }

  return (
    <div className={styles.browserContainer}>
      <div className={styles.studyHeader}>
        <div className={styles.studyInfo}>
          <h2>{study.description || `Study ${study.id}`}</h2>
          <p className={styles.studyDate}>
            {new Date(study.study_date).toLocaleDateString()}
          </p>
        </div>
        <button onClick={handleViewInOHIF} className={styles.viewerButton}>
          Open in OHIF Viewer
        </button>
      </div>

      <div className={styles.seriesList}>
        {series.length === 0 ? (
          <div className={styles.emptyState}>No series found in this study</div>
        ) : (
          series.map((seriesItem) => (
            <div key={seriesItem.id} className={styles.seriesCard}>
              <div className={styles.seriesHeader}>
                <h3>
                  Series {seriesItem.series_number}: {seriesItem.description || 'Untitled'}
                </h3>
                <span className={styles.seriesInfo}>
                  {seriesItem.modality} • {images[seriesItem.id]?.length || 0} images
                </span>
              </div>
              {images[seriesItem.id] && images[seriesItem.id].length > 0 && (
                <div className={styles.imagesGrid}>
                  {images[seriesItem.id].slice(0, 6).map((image) => (
                    <div
                      key={image.id}
                      className={styles.imageThumbnail}
                      onClick={() => onImageClick?.(image)}
                    >
                      <img
                        src={image.image_url || '/placeholder-image.png'}
                        alt={image.filename}
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = '/placeholder-image.png';
                        }}
                      />
                      <div className={styles.imageOverlay}>
                        <span>{image.filename}</span>
                      </div>
                    </div>
                  ))}
                  {images[seriesItem.id].length > 6 && (
                    <div className={styles.moreImages}>
                      +{images[seriesItem.id].length - 6} more
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default StudySeriesBrowser;

