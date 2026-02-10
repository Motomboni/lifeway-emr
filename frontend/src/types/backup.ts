/**
 * TypeScript types for Backup & Restore
 */

export interface Backup {
  id: number;
  backup_type: 'FULL' | 'INCREMENTAL' | 'DIFFERENTIAL';
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  file_path?: string;
  file_size?: number;
  is_encrypted: boolean;
  encryption_key_id?: string;
  includes_patients: boolean;
  includes_visits: boolean;
  includes_consultations: boolean;
  includes_lab_data: boolean;
  includes_radiology_data: boolean;
  includes_prescriptions: boolean;
  includes_audit_logs: boolean;
  description?: string;
  error_message?: string;
  created_by: number;
  created_by_name?: string;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  expires_at?: string | null;
  duration_seconds?: number | null;
  is_expired?: boolean;
}

export interface BackupCreateData {
  backup_type?: 'FULL' | 'INCREMENTAL' | 'DIFFERENTIAL';
  includes_patients?: boolean;
  includes_visits?: boolean;
  includes_consultations?: boolean;
  includes_lab_data?: boolean;
  includes_radiology_data?: boolean;
  includes_prescriptions?: boolean;
  includes_audit_logs?: boolean;
  description?: string;
  expires_at?: string;
}

export interface Restore {
  id: number;
  backup: number;
  backup_info?: {
    id: number;
    backup_type: string;
    created_at: string;
    file_size?: number;
  };
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  restore_patients: boolean;
  restore_visits: boolean;
  restore_consultations: boolean;
  restore_lab_data: boolean;
  restore_radiology_data: boolean;
  restore_prescriptions: boolean;
  restore_audit_logs: boolean;
  description?: string;
  error_message?: string;
  created_by: number;
  created_by_name?: string;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  duration_seconds?: number | null;
}

export interface RestoreCreateData {
  backup: number;
  restore_patients?: boolean;
  restore_visits?: boolean;
  restore_consultations?: boolean;
  restore_lab_data?: boolean;
  restore_radiology_data?: boolean;
  restore_prescriptions?: boolean;
  restore_audit_logs?: boolean;
  description?: string;
}
