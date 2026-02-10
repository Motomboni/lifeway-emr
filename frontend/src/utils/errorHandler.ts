/**
 * Centralized Error Handling Utilities
 * 
 * Provides consistent error handling across the application.
 */

export interface AppError {
  message: string;
  code?: string;
  statusCode?: number;
  details?: any;
}

/**
 * Parse API error response into a user-friendly message
 */
export function parseApiError(error: any): string {
  if (typeof error === 'string') {
    return error;
  }

  // Check if error has a response property (from API calls)
  if (error && typeof error === 'object' && 'response' in error) {
    const response = error.response;
    
    // Handle different error formats
    if (response.data) {
      // Handle array of error messages (DRF sometimes returns arrays)
      if (Array.isArray(response.data) && response.data.length > 0) {
        return response.data.join('; ');
      }
      
      if (typeof response.data === 'string') {
        return response.data;
      }
      
      if (response.data.detail !== undefined && response.data.detail !== null) {
        const d = response.data.detail;
        if (Array.isArray(d) && d.length > 0) {
          return d.map((x: any) => typeof x === 'string' ? x : (x?.message || String(x))).join('; ');
        }
        if (typeof d === 'string') return d;
        return String(d);
      }
      
      if (response.data.message) {
        return response.data.message;
      }
      
      if (response.data.error) {
        return response.data.error;
      }
      
      // Handle field-specific errors (DRF format)
      if (typeof response.data === 'object' && !Array.isArray(response.data)) {
        const fieldErrors = Object.entries(response.data)
          .filter(([key]) => key !== 'detail' && key !== 'message' && key !== 'error')
          .map(([field, errors]) => {
            const errorList = Array.isArray(errors) ? errors : [errors];
            return `${field}: ${errorList.join(', ')}`;
          });
        
        if (fieldErrors.length > 0) {
          return fieldErrors.join('; ');
        }
      }
    }
    
    // Handle HTTP status codes
    if (response.status) {
      switch (response.status) {
        case 400:
          return 'Invalid request. Please check your input.';
        case 401:
          return 'Authentication required. Please log in.';
        case 403:
          return 'You do not have permission to perform this action.';
        case 404:
          return 'The requested resource was not found.';
        case 409:
          return 'This action conflicts with the current state.';
        case 422:
          return 'Validation error. Please check your input.';
        case 503:
          // Check if this is a service worker offline error
          if (response.data?.error === 'Offline' || response.data?.message?.includes('offline')) {
            return navigator.onLine 
              ? 'Service temporarily unavailable. Please refresh the page.'
              : 'You are currently offline. Please check your internet connection.';
          }
          return 'Service temporarily unavailable. Please try again later.';
        case 500:
          return 'Server error. Please try again later.';
        default:
          return `Error ${response.status}: An error occurred`;
      }
    }
  }

  if (error instanceof Error) {
    return error.message || 'An unexpected error occurred';
  }

  if (error && typeof error === 'object') {
    if (error.message) {
      return error.message;
    }
    if (error.error) {
      return error.error;
    }
  }

  return 'An unexpected error occurred';
}

/**
 * Get user-friendly error message based on error code
 */
export function getErrorMessage(code: string): string {
  const errorMessages: Record<string, string> = {
    'PAYMENT_REQUIRED': 'Payment must be cleared before performing this action.',
    'VISIT_CLOSED': 'This visit is closed and cannot be modified.',
    'ROLE_FORBIDDEN': 'You do not have permission to perform this action.',
    'CONSULTATION_REQUIRED': 'A consultation is required before performing this action.',
    'VISIT_NOT_FOUND': 'The visit was not found.',
    'PATIENT_NOT_FOUND': 'The patient was not found.',
    'NETWORK_ERROR': 'Network error. Please check your connection.',
    'TIMEOUT': 'Request timed out. Please try again.',
  };

  return errorMessages[code] || 'An error occurred';
}

/**
 * Check if error is a network error
 */
export function isNetworkError(error: any): boolean {
  if (error instanceof Error) {
    return error.message.includes('Network') || 
           error.message.includes('network') ||
           error.message.includes('Failed to fetch') ||
           error.message.includes('fetch');
  }
  return false;
}

/**
 * Check if error is a timeout
 */
export function isTimeoutError(error: any): boolean {
  if (error instanceof Error) {
    return error.message.includes('timeout') || 
           error.message.includes('Timeout');
  }
  return false;
}

/**
 * Format error for display
 */
export function formatError(error: any): AppError {
  const message = parseApiError(error);
  const code = error?.code || error?.response?.data?.code;
  const statusCode = error?.response?.status;
  const details = error?.response?.data;

  return {
    message,
    code,
    statusCode,
    details,
  };
}
