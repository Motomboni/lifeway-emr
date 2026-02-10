/**
 * Logger Utility
 * 
 * Centralized logging utility that respects environment settings.
 * Logs are only shown in development mode.
 */

const isDevelopment = process.env.NODE_ENV === 'development';

export const logger = {
  /**
   * Log debug information (only in development)
   */
  debug: (...args: unknown[]) => {
    if (isDevelopment) {
      console.log('[DEBUG]', ...args);
    }
  },

  /**
   * Log information (only in development)
   */
  info: (...args: unknown[]) => {
    if (isDevelopment) {
      console.info('[INFO]', ...args);
    }
  },

  /**
   * Log warnings (always logged, but can be filtered)
   */
  warn: (...args: unknown[]) => {
    if (isDevelopment) {
      console.warn('[WARN]', ...args);
    }
  },

  /**
   * Log errors (always logged)
   */
  error: (...args: unknown[]) => {
    console.error('[ERROR]', ...args);
    // In production, you might want to send to error tracking service
    // Example: errorTrackingService.captureException(...args);
  },

  /**
   * Log API errors with context
   */
  apiError: (endpoint: string, error: unknown) => {
    if (isDevelopment) {
      console.error(`[API ERROR] ${endpoint}:`, error);
    }
    // Always log API errors, but format them appropriately
    logger.error(`API call failed: ${endpoint}`, error);
  },
};
