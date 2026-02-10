/**
 * Operation Notes API
 * 
 * API functions for managing surgical operation notes.
 */
import { apiRequest } from '../utils/apiClient';
import { OperationNote, OperationNoteCreateData, OperationNoteUpdateData } from '../types/operation';

/**
 * Get all operation notes for a visit
 */
export async function getOperationNotes(visitId: number): Promise<OperationNote[]> {
  return apiRequest<OperationNote[]>(`/visits/${visitId}/clinical/operation-notes/`);
}

/**
 * Get a single operation note
 */
export async function getOperationNote(visitId: number, noteId: number): Promise<OperationNote> {
  return apiRequest<OperationNote>(`/visits/${visitId}/clinical/operation-notes/${noteId}/`);
}

/**
 * Create a new operation note
 */
export async function createOperationNote(
  visitId: number,
  data: OperationNoteCreateData
): Promise<OperationNote> {
  return apiRequest<OperationNote>(`/visits/${visitId}/clinical/operation-notes/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an operation note
 */
export async function updateOperationNote(
  visitId: number,
  noteId: number,
  data: OperationNoteUpdateData
): Promise<OperationNote> {
  return apiRequest<OperationNote>(`/visits/${visitId}/clinical/operation-notes/${noteId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an operation note
 */
export async function deleteOperationNote(visitId: number, noteId: number): Promise<void> {
  return apiRequest<void>(`/visits/${visitId}/clinical/operation-notes/${noteId}/`, {
    method: 'DELETE',
  });
}
