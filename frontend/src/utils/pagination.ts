/**
 * Pagination Utilities
 * 
 * Provides utilities for handling paginated API responses.
 * DRF (Django REST Framework) returns paginated responses in the format:
 * { count, next, previous, results: T[] }
 */

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Extract results from a paginated API response.
 * Handles both paginated (PaginatedResponse) and array responses.
 * 
 * @param response - API response (can be array or PaginatedResponse)
 * @returns Array of results
 */
export function extractPaginatedResults<T>(response: T[] | PaginatedResponse<T> | null | undefined): T[] {
  if (!response) {
    return [];
  }
  
  // If it's already an array, return it
  if (Array.isArray(response)) {
    return response;
  }
  
  // If it's a paginated response, extract results
  if (typeof response === 'object' && 'results' in response && Array.isArray(response.results)) {
    return response.results;
  }
  
  // Fallback: return empty array
  return [];
}

/**
 * Check if a response is paginated.
 */
export function isPaginatedResponse<T>(response: unknown): response is PaginatedResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'results' in response &&
    'count' in response &&
    Array.isArray((response as PaginatedResponse<T>).results)
  );
}
