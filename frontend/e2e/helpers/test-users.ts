/**
 * Shared E2E test user credentials (must match seed_e2e_users management command).
 */
export interface TestUser {
  email: string;
  password: string;
  role: string;
}

export const TEST_RECEPTIONIST: TestUser = {
  email: 'receptionist@clinic.com',
  password: 'Receptionist123!',
  role: 'RECEPTIONIST',
};

export const TEST_DOCTOR: TestUser = {
  email: 'doctor@clinic.com',
  password: 'Doctor123!',
  role: 'DOCTOR',
};

export const TEST_LAB_TECH: TestUser = {
  email: 'labtech@clinic.com',
  password: 'LabTech123!',
  role: 'LAB_TECH',
};

export const BACKEND_HEALTH_URL =
  process.env.PLAYWRIGHT_BACKEND_URL || 'http://127.0.0.1:8000/api/v1/health/';

export const AUTH_LOGIN_URL =
  process.env.PLAYWRIGHT_AUTH_LOGIN_URL || 'http://127.0.0.1:8000/api/v1/auth/login/';
