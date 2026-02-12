/**
 * Authentication API Client
 */
import { apiRequest, unauthenticatedRequest } from '../utils/apiClient';
import { User, UserRole } from '../types/auth';

/**
 * Check if a JWT access token is expired (or will expire in the next 60s).
 * Avoids calling /auth/me/ with an expired token on app load (prevents 401 in console).
 */
export function isAccessTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    const payload = parts[1];
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), '=');
    const decoded = JSON.parse(atob(padded)) as { exp?: number };
    const exp = decoded.exp;
    if (typeof exp !== 'number') return true;
    // Consider expired if past exp or within 60s of exp
    return Date.now() / 1000 >= exp - 60;
  } catch {
    return true;
  }
}

export type { UserRole };
export type { User };

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  role: UserRole;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

/**
 * Register a new user
 */
export async function registerUser(data: RegisterData): Promise<User> {
  return unauthenticatedRequest<User>('/auth/register/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Login user
 */
export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  return unauthenticatedRequest<LoginResponse>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

/**
 * Refresh access token
 */
export async function refreshAccessToken(refreshToken: string): Promise<{ access: string; refresh: string }> {
  return unauthenticatedRequest<{ access: string; refresh: string }>('/auth/refresh/', {
    method: 'POST',
    body: JSON.stringify({ refresh: refreshToken }),
  });
}

/**
 * Get current user
 */
export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>('/auth/me/');
}

/**
 * List pending staff (awaiting approval) - Admin/Superuser only
 */
export async function fetchPendingStaff(): Promise<User[]> {
  return apiRequest<User[]>('/auth/pending-staff/');
}

/**
 * Approve a pending staff user - Admin/Superuser only
 */
export async function approveStaffUser(userId: number): Promise<User> {
  return apiRequest<User>(`/auth/pending-staff/${userId}/approve/`, {
    method: 'POST',
  });
}

/**
 * Logout user (blacklist refresh token)
 * Note: This requires authentication, but we handle failures gracefully
 */
export async function logoutUser(refreshToken: string): Promise<void> {
  try {
    return await apiRequest<void>('/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh: refreshToken }),
    });
  } catch (error) {
    // If logout fails (e.g., token expired), we still want to clear local state
    // So we don't throw - the caller will clear state anyway
    return;
  }
}
