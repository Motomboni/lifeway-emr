/**
 * Backup & Restore API Client
 * 
 * Endpoints:
 * - GET    /api/v1/backups/          - List backups
 * - POST   /api/v1/backups/          - Create backup (Superuser)
 * - GET    /api/v1/backups/{id}/     - Get backup
 * - DELETE /api/v1/backups/{id}/     - Delete backup
 * - POST   /api/v1/backups/{id}/download/ - Download backup file
 * - GET    /api/v1/backups/restores/ - List restores
 * - POST   /api/v1/backups/restores/ - Create restore (Superuser)
 */
import { apiRequest } from '../utils/apiClient';
import {
  Backup,
  BackupCreateData,
  Restore,
  RestoreCreateData,
} from '../types/backup';

// Re-export types for convenience
export type {
  Backup,
  BackupCreateData,
  Restore,
  RestoreCreateData,
} from '../types/backup';

export interface PaginatedBackupResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Backup[];
}

export interface PaginatedRestoreResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Restore[];
}

/**
 * Fetch backups
 */
export async function fetchBackups(filters?: {
  status?: string;
  backup_type?: string;
  page?: number;
  page_size?: number;
}): Promise<Backup[] | PaginatedBackupResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.backup_type) params.append('backup_type', filters.backup_type);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/backups/?${queryString}` : '/backups/';
  return apiRequest<Backup[] | PaginatedBackupResponse>(endpoint);
}

/**
 * Get backup by ID
 */
export async function getBackup(backupId: number): Promise<Backup> {
  return apiRequest<Backup>(`/backups/${backupId}/`);
}

/**
 * Create a new backup (Superuser only)
 */
export async function createBackup(backupData: BackupCreateData): Promise<Backup> {
  return apiRequest<Backup>('/backups/', {
    method: 'POST',
    body: JSON.stringify(backupData),
  });
}

/**
 * Delete a backup
 */
export async function deleteBackup(backupId: number): Promise<void> {
  return apiRequest<void>(`/backups/${backupId}/`, {
    method: 'DELETE',
  });
}

/**
 * Download backup file
 */
export async function downloadBackup(backupId: number): Promise<Blob> {
  const response = await fetch(`/api/v1/backups/${backupId}/download/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to download backup');
  }
  
  return response.blob();
}

/**
 * Fetch restores
 */
export async function fetchRestores(filters?: {
  status?: string;
  backup?: number;
  page?: number;
  page_size?: number;
}): Promise<Restore[] | PaginatedRestoreResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.backup) params.append('backup', filters.backup.toString());
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/backups/restores/?${queryString}` : '/backups/restores/';
  return apiRequest<Restore[] | PaginatedRestoreResponse>(endpoint);
}

/**
 * Get restore by ID
 */
export async function getRestore(restoreId: number): Promise<Restore> {
  return apiRequest<Restore>(`/backups/restores/${restoreId}/`);
}

/**
 * Create a new restore operation (Superuser only)
 */
export async function createRestore(restoreData: RestoreCreateData): Promise<Restore> {
  return apiRequest<Restore>('/backups/restores/', {
    method: 'POST',
    body: JSON.stringify(restoreData),
  });
}
