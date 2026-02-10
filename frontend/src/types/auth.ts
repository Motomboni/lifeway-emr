/**
 * TypeScript types for Authentication
 */

export type UserRole = 'ADMIN' | 'DOCTOR' | 'NURSE' | 'LAB_TECH' | 'RADIOLOGY_TECH' | 'PHARMACIST' | 'RECEPTIONIST' | 'PATIENT' | 'MANAGEMENT' | 'IVF_SPECIALIST' | 'EMBRYOLOGIST';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  is_superuser?: boolean;
  date_joined: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
