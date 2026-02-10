/**
 * TypeScript types for Users
 */

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'DOCTOR' | 'NURSE' | 'LAB_TECH' | 'RADIOLOGY_TECH' | 'PHARMACIST' | 'RECEPTIONIST' | 'PATIENT' | 'ADMIN' | 'MANAGEMENT';
  is_active: boolean;
  is_superuser?: boolean;
  date_joined: string;
}
