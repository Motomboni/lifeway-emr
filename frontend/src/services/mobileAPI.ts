/**
 * Mobile API Service Layer – offline-first.
 *
 * All list endpoints support ?updated_since=ISO8601.
 * Responses include last_updated. Use for SQLite sync: store last_updated, then request with updated_since.
 * Conflict strategy: server wins for medical data; client wins for profile updates.
 */

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token') ||
    (() => {
      try {
        const t = localStorage.getItem('auth_tokens');
        return t ? JSON.parse(t).access : null;
      } catch {
        return null;
      }
    })();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

const handleResponse = async (response: Response) => {
  if (response.status === 401) {
    // Token expired - redirect to login
    localStorage.clear();
    window.location.href = '/otp-login';
    throw new Error('Session expired');
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || error.message || 'Request failed');
  }
  
  return response.json();
};

// OTP Authentication
export const requestOTP = async (
  identifier: string,
  identifierType: 'email' | 'phone',
  channel: 'email' | 'sms' | 'whatsapp'
) => {
  const payload: any = { channel };
  
  if (identifierType === 'email') {
    payload.email = identifier;
  } else {
    payload.phone = identifier;
  }
  
  const response = await fetch('/api/v1/auth/request-otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  return handleResponse(response);
};

export const verifyOTP = async (
  identifier: string,
  identifierType: 'email' | 'phone',
  otpCode: string
) => {
  const payload: any = {
    otp_code: otpCode,
    device_type: /iPhone|iPad/.test(navigator.userAgent) ? 'ios' 
               : /Android/.test(navigator.userAgent) ? 'android' 
               : 'web'
  };
  
  if (identifierType === 'email') {
    payload.email = identifier;
  } else {
    payload.phone = identifier;
  }
  
  const response = await fetch('/api/v1/auth/verify-otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  return handleResponse(response);
};

// Mobile API Endpoints
export const getMobileProfile = async () => {
  const response = await fetch('/api/mobile/profile/', {
    headers: getAuthHeaders()
  });
  return handleResponse(response);
};

export interface MobileListResponse<T> {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: T[];
  last_updated?: string;
}

export const getMobileAppointments = async (page = 1, updatedSince?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (updatedSince) params.set('updated_since', updatedSince);
  const response = await fetch(`/api/mobile/appointments/?${params}`, {
    headers: getAuthHeaders()
  });
  return handleResponse(response) as Promise<MobileListResponse<unknown> & { last_updated?: string }>;
};

export const getMobilePrescriptions = async (page = 1, updatedSince?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (updatedSince) params.set('updated_since', updatedSince);
  const response = await fetch(`/api/mobile/prescriptions/?${params}`, {
    headers: getAuthHeaders()
  });
  return handleResponse(response);
};

export const getMobileLabResults = async (page = 1, updatedSince?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (updatedSince) params.set('updated_since', updatedSince);
  const response = await fetch(`/api/mobile/lab-results/?${params}`, {
    headers: getAuthHeaders()
  });
  return handleResponse(response);
};

export const getMobileBills = async (page = 1, updatedSince?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (updatedSince) params.set('updated_since', updatedSince);
  const response = await fetch(`/api/mobile/bills/?${params}`, {
    headers: getAuthHeaders()
  });
  return handleResponse(response);
};

export const getMobileDashboard = async () => {
  const response = await fetch('/api/mobile/dashboard/', {
    headers: getAuthHeaders()
  });
  return handleResponse(response);
};

/** Record sync and get last_sync_time. Call after successful sync. */
export const postMobileSync = async (deviceId: string) => {
  const response = await fetch('/api/mobile/sync/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ device_id: deviceId })
  });
  return handleResponse(response) as Promise<{ device_id: string; last_sync_time: string; last_updated: string }>;
};

/** Get last sync time for device (for incremental sync). */
export const getMobileSync = async (deviceId: string) => {
  const response = await fetch(`/api/mobile/sync/?device_id=${encodeURIComponent(deviceId)}`, {
    headers: getAuthHeaders()
  });
  return handleResponse(response) as Promise<{ device_id: string; last_sync_time: string | null; last_updated: string }>;
};

export const logout = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  if (refreshToken) {
    try {
      await fetch('/api/v1/auth/logout/', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ refresh: refreshToken })
      });
    } catch (err) {
      console.error('Logout error:', err);
    }
  }
  
  localStorage.clear();
};
