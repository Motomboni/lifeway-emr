/**
 * Offline-First Image Upload Component
 * 
 * Handles image uploads with offline support, retry logic, and data integrity.
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  createUploadSession,
  uploadMetadata,
  uploadBinary,
  acknowledgeUpload,
  getUploadSessionStatus,
  ImageUploadSession,
  CreateSessionData,
} from '../../api/uploadSession';
import {
  calculateChecksum,
  generateImageUuid,
  generateSessionUuid,
  getDeviceId,
  getDeviceInfo,
  storeImageLocally,
  deleteLocalImage,
} from '../../utils/imageUpload';
import LockIndicator from '../locks/LockIndicator';
import { useActionLock } from '../../hooks/useActionLock';
import styles from './OfflineImageUpload.module.css';

interface OfflineImageUploadProps {
  radiologyOrderId: number;
  onUploadComplete?: (session: ImageUploadSession) => void;
}

interface ImageFile {
  file: File;
  uuid: string;
  checksum: string;
  sequenceNumber: number;
  status: 'pending' | 'metadata_uploaded' | 'binary_uploaded' | 'ack_received' | 'failed';
  error?: string;
}

const OfflineImageUpload: React.FC<OfflineImageUploadProps> = ({
  radiologyOrderId,
  onUploadComplete,
}) => {
  const [session, setSession] = useState<ImageUploadSession | null>(null);
  const [images, setImages] = useState<ImageFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Create upload session
  const createSession = useCallback(async () => {
    try {
      const sessionData: CreateSessionData = {
        session_uuid: generateSessionUuid(),
        radiology_order: radiologyOrderId,
        device_id: getDeviceId(),
        device_info: getDeviceInfo(),
        total_images: images.length,
      };

      const newSession = await createUploadSession(sessionData);
      setSession(newSession);
      return newSession;
    } catch (err: any) {
      setError(err.message || 'Failed to create upload session');
      throw err;
    }
  }, [radiologyOrderId, images.length]);

  // Handle file selection
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const newImages: ImageFile[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const uuid = generateImageUuid();
      
      try {
        // Calculate checksum
        const checksum = await calculateChecksum(file);
        
        newImages.push({
          file,
          uuid,
          checksum,
          sequenceNumber: images.length + i,
          status: 'pending',
        });
      } catch (err: any) {
        console.error(`Error processing file ${file.name}:`, err);
      }
    }

    setImages([...images, ...newImages]);
    
    // Store images locally
    for (const image of newImages) {
      try {
        await storeImageLocally(image.uuid, image.file, {
          radiologyOrderId,
          filename: image.file.name,
          checksum: image.checksum,
          mimeType: image.file.type,
        });
      } catch (err) {
        console.error(`Error storing image locally:`, err);
      }
    }
  };

  // Upload metadata for an image
  const uploadImageMetadata = async (image: ImageFile, sessionId: number) => {
    try {
      await uploadMetadata(sessionId, {
        image_uuid: image.uuid,
        filename: image.file.name,
        file_size: image.file.size,
        mime_type: image.file.type || 'image/jpeg',
        checksum: image.checksum,
        sequence_number: image.sequenceNumber,
      });

      // Update image status
      setImages(prev => prev.map(img =>
        img.uuid === image.uuid
          ? { ...img, status: 'metadata_uploaded' }
          : img
      ));
    } catch (err: any) {
      throw new Error(`Metadata upload failed: ${err.message}`);
    }
  };

  // Upload binary for an image
  const uploadImageBinary = async (image: ImageFile, sessionId: number) => {
    try {
      await uploadBinary(sessionId, image.uuid, image.file);

      // Update image status
      setImages(prev => prev.map(img =>
        img.uuid === image.uuid
          ? { ...img, status: 'binary_uploaded' }
          : img
      ));
    } catch (err: any) {
      throw new Error(`Binary upload failed: ${err.message}`);
    }
  };

  // Acknowledge upload
  const acknowledgeImageUpload = async (image: ImageFile, sessionId: number) => {
    try {
      await acknowledgeUpload(sessionId, image.uuid);

      // Update image status
      setImages(prev => prev.map(img =>
        img.uuid === image.uuid
          ? { ...img, status: 'ack_received' }
          : img
      ));

      // Delete local copy after ACK
      try {
        await deleteLocalImage(image.uuid);
      } catch (err) {
        console.warn(`Failed to delete local image ${image.uuid}:`, err);
      }
    } catch (err: any) {
      throw new Error(`ACK failed: ${err.message}`);
    }
  };

  // Upload all images
  const startUpload = async () => {
    if (images.length === 0) {
      setError('No images selected');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      // Create or get session
      let currentSession = session;
      if (!currentSession) {
        currentSession = await createSession();
      }

      // Upload each image
      for (const image of images) {
        if (image.status === 'ack_received') continue;

        try {
          // Step 1: Upload metadata
          if (image.status === 'pending') {
            await uploadImageMetadata(image, currentSession.id);
          }

          // Step 2: Upload binary
          if (image.status === 'metadata_uploaded' || image.status === 'binary_uploaded') {
            await uploadImageBinary(image, currentSession.id);
          }

          // Step 3: Acknowledge
          if (image.status === 'binary_uploaded') {
            await acknowledgeImageUpload(image, currentSession.id);
          }
        } catch (err: any) {
          // Mark image as failed
          setImages(prev => prev.map(img =>
            img.uuid === image.uuid
              ? { ...img, status: 'failed', error: err.message }
              : img
          ));
        }
      }

      // Refresh session status
      const updatedSession = await getUploadSessionStatus(currentSession.id);
      setSession(updatedSession);

      if (updatedSession.is_complete && onUploadComplete) {
        onUploadComplete(updatedSession);
      }
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Retry failed uploads
  const retryFailed = async () => {
    const failedImages = images.filter(img => img.status === 'failed');
    if (failedImages.length === 0) return;

    // Reset failed images to pending
    setImages(prev => prev.map(img =>
      img.status === 'failed'
        ? { ...img, status: 'pending', error: undefined }
        : img
    ));

    // Start upload again
    await startUpload();
  };

  const uploadedCount = images.filter(img => img.status === 'ack_received').length;
  const failedCount = images.filter(img => img.status === 'failed').length;
  const progress = images.length > 0 ? (uploadedCount / images.length) * 100 : 0;

  return (
    <div className={styles.uploadContainer}>
      <h3>Offline Image Upload</h3>

      {/* File selection */}
      <div className={styles.fileSelection}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.dcm,.dicom"
          multiple
          onChange={handleFileSelect}
          disabled={uploading}
          className={styles.fileInput}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className={styles.selectButton}
        >
          Select Images
        </button>
      </div>

      {/* Image list */}
      {images.length > 0 && (
        <div className={styles.imageList}>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className={styles.progressText}>
            {uploadedCount} / {images.length} uploaded
            {failedCount > 0 && ` (${failedCount} failed)`}
          </div>

          {images.map((image) => (
            <div key={image.uuid} className={styles.imageItem}>
              <div className={styles.imageInfo}>
                <span className={styles.filename}>{image.file.name}</span>
                <span className={styles.fileSize}>
                  {(image.file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              </div>
              <div className={styles.imageStatus}>
                <span className={`${styles.statusBadge} ${styles[image.status]}`}>
                  {image.status.replace('_', ' ').toUpperCase()}
                </span>
                {image.error && (
                  <span className={styles.error}>{image.error}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className={styles.actions}>
        {images.length > 0 && (
          <>
            <button
              type="button"
              onClick={startUpload}
              disabled={uploading || uploadedCount === images.length}
              className={styles.uploadButton}
            >
              {uploading ? 'Uploading...' : 'Start Upload'}
            </button>
            {failedCount > 0 && (
              <button
                type="button"
                onClick={retryFailed}
                disabled={uploading}
                className={styles.retryButton}
              >
                Retry Failed ({failedCount})
              </button>
            )}
          </>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className={styles.errorMessage}>{error}</div>
      )}

      {/* Session info */}
      {session && (
        <div className={styles.sessionInfo}>
          <div>Session: {session.session_uuid}</div>
          <div>Status: {session.status}</div>
          <div>Progress: {session.progress_percentage.toFixed(1)}%</div>
        </div>
      )}
    </div>
  );
};

export default OfflineImageUpload;

