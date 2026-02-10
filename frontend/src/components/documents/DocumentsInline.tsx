/**
 * Documents Inline Component
 * 
 * Inline component for managing medical documents within consultation workspace.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { fetchDocuments, uploadDocument, deleteDocument, downloadDocument } from '../../api/documents';
import { MedicalDocument, MedicalDocumentCreate } from '../../types/documents';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface DocumentsInlineProps {
  visitId: string;
}

export default function DocumentsInline({ visitId }: DocumentsInlineProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [formData, setFormData] = useState<{
    document_type: MedicalDocumentCreate['document_type'];
    title: string;
    description: string;
    file: File | null;
  }>({
    document_type: 'OTHER',
    title: '',
    description: '',
    file: null,
  });

  useEffect(() => {
    loadDocuments();
  }, [visitId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await fetchDocuments(parseInt(visitId));
      setDocuments(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, file: e.target.files[0] });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.file) {
      showError('Please select a file to upload');
      return;
    }
    
    if (!formData.title.trim()) {
      showError('Please enter a document title');
      return;
    }
    
    try {
      setUploading(true);
      await uploadDocument(parseInt(visitId), {
        document_type: formData.document_type,
        title: formData.title,
        description: formData.description || undefined,
        file: formData.file,
      });
      showSuccess('Document uploaded successfully');
      setShowUploadForm(false);
      setFormData({
        document_type: 'OTHER',
        title: '',
        description: '',
        file: null,
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await loadDocuments();
    } catch (error: any) {
      showError(error.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId: number) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }
    
    try {
      await deleteDocument(parseInt(visitId), documentId);
      showSuccess('Document deleted successfully');
      await loadDocuments();
    } catch (error: any) {
      showError(error.message || 'Failed to delete document');
    }
  };

  const handleDownload = async (doc: MedicalDocument) => {
    try {
      const blob = await downloadDocument(parseInt(visitId), doc.id);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = doc.file_name || doc.title;
      window.document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(link);
      showSuccess('Document downloaded');
    } catch (error: any) {
      showError(error.message || 'Failed to download document');
    }
  };

  const formatFileSize = (bytes?: number | null) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const canManage = user?.role === 'DOCTOR' || user?.role === 'RECEPTIONIST';

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Documents</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Documents</h3>
        {canManage && !showUploadForm && (
          <button
            className={styles.addButton}
            onClick={() => setShowUploadForm(true)}
            type="button"
          >
            + Upload Document
          </button>
        )}
      </div>

      {showUploadForm && canManage && (
        <form onSubmit={handleSubmit} className={styles.createForm}>
          <h4>Upload Document</h4>
          
          <div className={styles.formGroup}>
            <label>Document Type</label>
            <select
              value={formData.document_type}
              onChange={(e) => setFormData({ ...formData, document_type: e.target.value as MedicalDocumentCreate['document_type'] })}
              required
            >
              <option value="LAB_REPORT">Lab Report</option>
              <option value="RADIOLOGY_REPORT">Radiology Report</option>
              <option value="CONSULTATION_NOTE">Consultation Note</option>
              <option value="PRESCRIPTION">Prescription</option>
              <option value="REFERRAL_LETTER">Referral Letter</option>
              <option value="DISCHARGE_SUMMARY">Discharge Summary</option>
              <option value="CONSENT_FORM">Consent Form</option>
              <option value="INSURANCE_CARD">Insurance Card</option>
              <option value="ID_DOCUMENT">ID Document</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          
          <div className={styles.formGroup}>
            <label>Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Document title"
            />
          </div>
          
          <div className={styles.formGroup}>
            <label>Description (Optional)</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
              placeholder="Document description"
            />
          </div>
          
          <div className={styles.formGroup}>
            <label>File</label>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff,.dcm"
              required
            />
            {formData.file && (
              <p className={styles.fileInfo}>
                Selected: {formData.file.name} ({(formData.file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
          
          <div className={styles.formActions}>
            <button type="submit" disabled={uploading || !formData.file} className={styles.saveButton}>
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowUploadForm(false);
                setFormData({
                  document_type: 'OTHER',
                  title: '',
                  description: '',
                  file: null,
                });
                if (fileInputRef.current) {
                  fileInputRef.current.value = '';
                }
              }}
              className={styles.cancelButton}
              disabled={uploading}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {documents.length === 0 && !showUploadForm && (
        <p className={styles.emptyState}>No documents uploaded for this visit.</p>
      )}

      {documents.map((doc) => (
        <div key={doc.id} className={styles.documentCard}>
          <div className={styles.documentHeader}>
            <div>
              <strong>{doc.title}</strong>
              <span className={styles.documentType}>{doc.document_type.replace('_', ' ')}</span>
            </div>
            <div className={styles.documentMeta}>
              <span>{formatFileSize(doc.file_size)}</span>
            </div>
          </div>
          
          {doc.description && (
            <div className={styles.documentDescription}>{doc.description}</div>
          )}
          
          <div className={styles.documentFooter}>
            <div className={styles.documentInfo}>
              <span>Uploaded by {doc.uploaded_by_name}</span>
              <span>•</span>
              <span>{formatDateTime(doc.created_at)}</span>
            </div>
            
            <div className={styles.documentActions}>
              {doc.file_url && (
                <a
                  href={doc.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.viewButton}
                >
                  View
                </a>
              )}
              <button
                className={styles.downloadButton}
                onClick={() => handleDownload(doc)}
                type="button"
              >
                Download
              </button>
              {canManage && (
                <button
                  className={styles.deleteButton}
                  onClick={() => handleDelete(doc.id)}
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
