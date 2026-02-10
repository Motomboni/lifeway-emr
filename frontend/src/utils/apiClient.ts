/**
 * Centralized API Client
 * 
 * Handles authentication token injection and error handling.
 * Per EMR Rules: All API calls must include JWT Bearer token.
 */
import { parseApiError, isNetworkError, isTimeoutError } from './errorHandler';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

/**
 * Get authentication token from localStorage
 */
export function getAuthToken(): string | null {
  // Try new format first
  const tokens = localStorage.getItem('auth_tokens');
  if (tokens) {
    try {
      const parsed = JSON.parse(tokens);
      return parsed.access || null;
    } catch {
      // Invalid JSON
    }
  }
  
  // Fallback to legacy format
  return localStorage.getItem('auth_token');
}

/**
 * Get refresh token from localStorage
 */
function getRefreshToken(): string | null {
  const tokens = localStorage.getItem('auth_tokens');
  if (tokens) {
    try {
      const parsed = JSON.parse(tokens);
      return parsed.refresh || null;
    } catch {
      // Invalid JSON
    }
  }
  return null;
}

// Track if we're currently refreshing to prevent concurrent refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

/**
 * Refresh access token using refresh token
 * Uses a singleton pattern to prevent concurrent refresh attempts
 */
async function refreshAccessToken(): Promise<string | null> {
  // If already refreshing, wait for the existing refresh to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  // Mark as refreshing and create the promise
  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) {
        // If refresh fails, clear tokens
        localStorage.removeItem('auth_tokens');
        localStorage.removeItem('auth_user');
        localStorage.removeItem('auth_token');
        return null;
      }

      const data = await response.json();
      const newTokens = {
        access: data.access,
        refresh: data.refresh || refreshToken, // Use new refresh token if provided, otherwise keep old one
      };

      // Update localStorage
      localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
      localStorage.setItem('auth_token', data.access); // Legacy support

      return data.access;
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Clear tokens on error
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_token');
      return null;
    } finally {
      // Reset refreshing state
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  
  if (!token) {
    // Redirect to login if no token
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('No authentication token found');
  }
  
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    });
  } catch (error) {
    // Handle network errors
    if (isNetworkError(error)) {
      throw new Error('Network error. Please check your connection and try again.');
    }
    if (isTimeoutError(error)) {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  }

  if (!response.ok) {
    let errorData: any = {};
    try {
      // Try to parse as JSON first
      errorData = await response.json();
    } catch (jsonError) {
      // If JSON parsing fails, try to get text
      try {
        const text = await response.text();
        errorData = { detail: text || 'Unknown error occurred' };
      } catch (textError) {
        // If both fail, create a basic error object
        errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
      }
    }
    
    // Check if this is a 503 from a service worker or network unreachable
    const msg = (errorData.message ?? errorData.detail ?? '').toString().toLowerCase();
    const isServiceWorker503 = response.status === 503 && 
                               (errorData.error === 'Offline' || 
                                msg.includes('offline') ||
                                msg.includes('not available offline') ||
                                msg.includes('network request failed') ||
                                msg.includes('network error') ||
                                (errorData.error && String(errorData.error).toLowerCase().includes('network')));
    
    // If it's a service worker 503 but we're actually online, retry the request
    // This handles cases where service workers incorrectly cache offline state
    if (isServiceWorker503 && navigator.onLine) {
      try {
        const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...options,
          cache: 'no-store',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'Cache-Control': 'no-cache',
            ...options.headers,
          },
        });
        
        if (retryResponse.ok) {
          if (retryResponse.status === 204) {
            return {} as T;
          }
          return retryResponse.json();
        }
      } catch {
        // Retry failed, continue with normal error handling
      }
    }
    
    // Check if this is an expected 404 for list endpoints (empty results)
    // These are handled gracefully by hooks, so we suppress console noise
    const isExpected404 = response.status === 404 && (
      endpoint.includes('/results/') || 
      endpoint.endsWith('/results') ||
      endpoint.includes('/insurance/')  // Insurance endpoints may not exist for all visits
    );
    
    // Check if this is a 401 that will be handled by token refresh
    // Suppress console errors for 401s that will be auto-refreshed
    const is401WithRefresh = response.status === 401 && 
                             !endpoint.includes('/auth/refresh/') && 
                             !endpoint.includes('/auth/login/') &&
                             getRefreshToken() !== null; // Only suppress if we have a refresh token to try
    
    // Also suppress 401s and 504s from background polling (notifications, locks, pending verifications, clinical alerts)
    const isBackgroundPolling = endpoint.includes('/visits/?status=') || 
                                endpoint.includes('/locks/') ||
                                endpoint.includes('/notifications/') ||
                                endpoint.includes('/patients/pending-verification/') ||
                                endpoint.includes('/clinical/alerts/');
    const is401FromPolling = response.status === 401 && isBackgroundPolling;
    const is504FromPolling = response.status === 504 && isBackgroundPolling;
    
    // Suppress all service worker 503 logs (we retry when online; when offline it's expected)
    const isExpected503 = isServiceWorker503;
    
    // Suppress 403 errors for payment-related restrictions (expected business logic)
    // These are not bugs - they indicate the visit needs payment before clinical access
    const isPaymentRequired403 = response.status === 403 && 
                                  (errorData.detail?.includes('Payment') || 
                                   errorData.message?.includes('Payment') ||
                                   errorData.detail?.includes('payment'));

    // Suppress 400 "billing line item already exists" - expected when adding same service twice
    // Backend may return { detail: [...] } or a raw array as the response body
    const addItemDetailStr = Array.isArray(errorData)
      ? errorData.map((x: any) => String(x)).join(' ')
      : (errorData?.detail != null
          ? (Array.isArray(errorData.detail)
              ? errorData.detail.map((x: any) => String(x)).join(' ')
              : String(errorData.detail))
          : '');
    const isBillingAlreadyExists = response.status === 400 &&
      endpoint.includes('/billing/add-item') &&
      (addItemDetailStr.includes('already exists') || addItemDetailStr.includes('one billing line item per visit'));
    
    // Log error details for debugging (suppress expected errors)
    const shouldSuppressLog = isExpected404 || is401WithRefresh || is401FromPolling || 
                              is504FromPolling || isExpected503 || isPaymentRequired403 || isBillingAlreadyExists;
    
    if (!shouldSuppressLog) {
      console.error('API Error Response:', {
        status: response.status,
        statusText: response.statusText,
        data: errorData,
      });
      console.error('Full error data:', JSON.stringify(errorData, null, 2));
    }
    // Log billing add-item 400 only when not "already exists" (expected)
    if (response.status === 400 && endpoint.includes('/billing/add-item') && !isBillingAlreadyExists) {
      console.warn('[Billing add-item 400]', addItemDetailStr || errorData);
    }
    
    const errorMessage = parseApiError({ response: { status: response.status, data: errorData } });
    
    // Create error object with both message and raw data for field-specific error parsing
    const error = new Error(errorMessage) as any;
    error.responseData = errorData; // Attach raw error data for field-specific parsing
    error.status = response.status;
    
    // Handle specific error codes
    if (response.status === 401) {
      // Unauthorized - try to refresh token first
      // Only attempt refresh if this is not already a refresh token request
      if (!endpoint.includes('/auth/refresh/') && !endpoint.includes('/auth/login/')) {
        try {
          const newAccessToken = await refreshAccessToken();
          
          if (newAccessToken) {
            // Token refreshed successfully, retry the original request
            try {
              const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...options,
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${newAccessToken}`,
                  ...options.headers,
                },
              });

              if (retryResponse.ok) {
                if (retryResponse.status === 204) {
                  return {} as T;
                }
                return retryResponse.json();
              } else {
                // Retry still failed, check if it's still 401
                if (retryResponse.status === 401) {
                  // Refresh token might be expired too, or user doesn't have permission
                  // Don't log this as it's expected in some cases
                }
                // Parse retry error for better error message
                let retryErrorData: any = {};
                try {
                  retryErrorData = await retryResponse.json();
                } catch {
                  retryErrorData = { detail: `HTTP ${retryResponse.status}: ${retryResponse.statusText}` };
                }
                const retryErrorMessage = parseApiError({ response: { status: retryResponse.status, data: retryErrorData } });
                const retryError = new Error(retryErrorMessage) as any;
                retryError.responseData = retryErrorData;
                retryError.status = retryResponse.status;
                throw retryError;
              }
            } catch (retryError: any) {
              // Retry failed - if it's still 401, we'll handle it below
              if (retryError && retryError.status === 401) {
                // Token refresh didn't help, likely refresh token expired
                // Continue to logout flow below
              } else {
                // Different error, throw it
                throw retryError;
              }
            }
          }
        } catch (refreshError) {
          // Refresh failed - likely refresh token expired
          // Continue to logout flow below
        }
      }
      
      // Refresh failed or not applicable - clear auth and redirect to login
      // Suppress console errors for expected token expiration
      const isTokenExpired = errorData.code === 'token_not_valid' && 
                            errorData.messages?.some((m: any) => m.message === 'Token is expired');
      
      if (!isTokenExpired) {
        // Only log if it's not a simple token expiration
        console.error('API Error Response:', {
          status: response.status,
          statusText: response.statusText,
          data: errorData,
        });
      }
      
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new Error('Unauthorized');
    }
    
    throw error;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * Make an unauthenticated API request (for public endpoints like health checks)
 */
export async function unauthenticatedRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (error) {
    // Handle network errors
    if (isNetworkError(error)) {
      throw new Error('Network error. Please check your connection and try again.');
    }
    if (isTimeoutError(error)) {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  }

  if (!response.ok) {
    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      // If JSON parsing fails, create basic error
      errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }
    const errorMessage = parseApiError({ response: { status: response.status, data: errorData } });
    const error = new Error(errorMessage) as any;
    error.responseData = errorData;
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
