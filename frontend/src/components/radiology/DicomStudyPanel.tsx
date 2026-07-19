/**
 * DICOM upload and study viewer for a radiology request.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  getStudyImages,
  getStudyViewerUrl,
  uploadDicomForRequest,
} from '../../api/radiology';
import { useToast } from '../../hooks/useToast';
import OHIFViewer from './OHIFViewer';
import styles from '../../styles/RadiologyOrders.module.css';

interface DicomStudyPanelProps {
  visitId: number;
  requestId: number;
  pacsStudyId?: number | null;
  imageCount?: number | null;
  onUploaded?: () => void;
}

export default function DicomStudyPanel({
  visitId,
  requestId,
  pacsStudyId,
  imageCount,
  onUploaded,
}: DicomStudyPanelProps) {
  const { showError, showSuccess } = useToast();
  const [uploading, setUploading] = useState(false);
  const [studyId, setStudyId] = useState<number | null>(pacsStudyId ?? null);
  const [count, setCount] = useState(imageCount ?? 0);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const [seriesSummary, setSeriesSummary] = useState<string>('');

  const loadStudy = useCallback(async (id: number) => {
    try {
      const data = await getStudyImages(id);
      setSeriesSummary(`${data.series?.length || 0} series loaded`);
    } catch {
      setSeriesSummary('');
    }
  }, []);

  useEffect(() => {
    if (pacsStudyId) {
      setStudyId(pacsStudyId);
      loadStudy(pacsStudyId);
    }
  }, [pacsStudyId, loadStudy]);

  useEffect(() => {
    setCount(imageCount ?? 0);
  }, [imageCount]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadDicomForRequest(visitId, requestId, file);
      setStudyId(result.study_id);
      setCount(result.image_count);
      showSuccess(`DICOM uploaded (${result.image_count} image(s) in study)`);
      if (result.study_id) {
        await loadStudy(result.study_id);
      }
      onUploaded?.();
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'DICOM upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleOpenViewer = async () => {
    if (!studyId) {
      showError('Upload a DICOM file first.');
      return;
    }
    try {
      const { viewer_url } = await getStudyViewerUrl(studyId);
      if (viewer_url.startsWith('http')) {
        window.open(viewer_url, '_blank', 'noopener,noreferrer');
      } else {
        setViewerUrl(viewer_url);
      }
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Could not open viewer');
    }
  };

  return (
    <div className={styles.dicomPanel}>
      <h4>DICOM Imaging</h4>
      <p className={styles.dicomMeta}>
        {count > 0
          ? `${count} image(s) in PACS storage${seriesSummary ? ` · ${seriesSummary}` : ''}`
          : 'No DICOM files uploaded yet.'}
      </p>
      <div className={styles.dicomActions}>
        <label className={styles.dicomUploadLabel}>
          <input
            type="file"
            accept=".dcm,.dicom,application/dicom"
            onChange={handleUpload}
            disabled={uploading}
            hidden
          />
          {uploading ? 'Uploading…' : 'Upload DICOM'}
        </label>
        {studyId && (
          <button type="button" className={styles.updateButton} onClick={handleOpenViewer}>
            Open Viewer
          </button>
        )}
      </div>
      {viewerUrl && studyId && (
        <div className={styles.dicomViewerWrap}>
          <OHIFViewer studyId={studyId} viewerUrl={viewerUrl} />
        </div>
      )}
    </div>
  );
}
