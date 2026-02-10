/**
 * Health Check API Client
 */
import { apiRequest, unauthenticatedRequest } from '../utils/apiClient';

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  checks?: {
    database: boolean;
    cache: boolean;
    application: boolean;
  };
  errors?: string[];
}

export interface HealthInfo {
  application: string;
  version: string;
  environment: string;
  timestamp: string;
  database: string;
  debug: boolean;
  allowed_hosts?: string[];
  cors_origins?: string[];
}

/**
 * Basic health check
 */
export async function checkHealth(): Promise<HealthStatus> {
  return unauthenticatedRequest<HealthStatus>('/api/v1/health/');
}

/**
 * Detailed health check
 */
export async function checkHealthDetailed(): Promise<HealthStatus> {
  return unauthenticatedRequest<HealthStatus>('/api/v1/health/detailed/');
}

/**
 * Get application information
 */
export async function getHealthInfo(): Promise<HealthInfo> {
  return unauthenticatedRequest<HealthInfo>('/api/v1/health/info/');
}
