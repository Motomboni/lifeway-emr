/**
 * Documents API Client
 * 
 * Endpoints:
 * - GET /api/v1/visits/{visit_id}/documents/ - List documents
 * - POST /api/v1/visits/{visit_id}/documents/ - Upload document
 * - DELETE /api/v1/visits/{visit_id}/documents/{id}/ - Delete document
 * - GET /api/v1/visits/{visit_id}/documents/{id}/download/ - Download document
 */
import { apiRequest } from '../utils/apiClient';
import { MedicalDocument, MedicalDocumentCreate } from '../types/documents';

/**
 * Fetch documents for a visit
 */
export async function fetchDocuments(visitId: number): Promise<MedicalDocument[]> {
  return apiRequest<MedicalDocument[]>(`/visits/${visitId}/documents/`);
}

/**
 * Upload a document
 */
export async function uploadDocument(
  visitId: number,
  data: MedicalDocumentCreate
): Promise<MedicalDocument> {
  const formData = new FormData();
  formData.append('document_type', data.document_type);
  formData.append('title', data.title);
  if (data.description) {
    formData.append('description', data.description);
  }
  formData.append('file', data.file);

  const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/visits/${visitId}/documents/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_tokens') ? JSON.parse(localStorage.getItem('auth_tokens')!).access : ''}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || 'Failed to upload document');
  }

  return response.json();
}

/**
 * Delete a document (soft delete)
 */
export async function deleteDocument(
  visitId: number,
  documentId: number
): Promise<void> {
  return apiRequest<void>(`/visits/${visitId}/documents/${documentId}/`, {
    method: 'DELETE',
  });
}

/**
 * Download a document
 */
export async function downloadDocument(
  visitId: number,
  documentId: number
): Promise<Blob> {
  const token = localStorage.getItem('auth_tokens') ? JSON.parse(localStorage.getItem('auth_tokens')!).access : '';
  
  const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/visits/${visitId}/documents/${documentId}/download/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || 'Failed to download document');
  }

  return response.blob();
}
