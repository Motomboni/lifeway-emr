/**
 * Basic utility tests
 * 
 * Tests for error handling and validation utilities.
 */
import { parseApiError, isNetworkError, isTimeoutError, formatError } from '../utils/errorHandler';
import {
  validateRequired,
  validateEmail,
  validatePhone,
  validateDate,
  validateNumberRange,
  validatePaymentAmount,
  validatePatientData,
  validateConsultationData,
} from '../utils/validation';

describe('Error Handler', () => {
  describe('parseApiError', () => {
    it('should parse string errors', () => {
      expect(parseApiError('Simple error')).toBe('Simple error');
    });

    it('should parse Error objects', () => {
      const error = new Error('Test error');
      expect(parseApiError(error)).toBe('Test error');
    });

    it('should parse API response errors', () => {
      const error = {
        response: {
          status: 400,
          data: { detail: 'Bad request' }
        }
      };
      expect(parseApiError(error)).toBe('Bad request');
    });

    it('should handle 401 errors', () => {
      const error = {
        response: {
          status: 401,
          data: {}
        }
      };
      expect(parseApiError(error)).toBe('Authentication required. Please log in.');
    });

    it('should handle 403 errors', () => {
      const error = {
        response: {
          status: 403,
          data: {}
        }
      };
      expect(parseApiError(error)).toBe('You do not have permission to perform this action.');
    });
  });

  describe('isNetworkError', () => {
    it('should detect network errors', () => {
      expect(isNetworkError(new Error('Network error'))).toBe(true);
      expect(isNetworkError(new Error('Failed to fetch'))).toBe(true);
      expect(isNetworkError(new Error('Regular error'))).toBe(false);
    });
  });

  describe('isTimeoutError', () => {
    it('should detect timeout errors', () => {
      expect(isTimeoutError(new Error('Request timeout'))).toBe(true);
      expect(isTimeoutError(new Error('Timeout error'))).toBe(true);
      expect(isTimeoutError(new Error('Regular error'))).toBe(false);
    });
  });
});

describe('Validation', () => {
  describe('validateRequired', () => {
    it('should validate required fields', () => {
      expect(validateRequired('', 'Name')).toBe('Name is required');
      expect(validateRequired(null, 'Name')).toBe('Name is required');
      expect(validateRequired(undefined, 'Name')).toBe('Name is required');
      expect(validateRequired('   ', 'Name')).toBe('Name cannot be empty');
      expect(validateRequired('Valid', 'Name')).toBeNull();
    });
  });

  describe('validateEmail', () => {
    it('should validate email format', () => {
      expect(validateEmail('invalid')).toBe('Invalid email format');
      expect(validateEmail('test@example')).toBe('Invalid email format');
      expect(validateEmail('test@example.com')).toBeNull();
      expect(validateEmail('')).toBeNull(); // Optional
    });
  });

  describe('validatePhone', () => {
    it('should validate phone numbers', () => {
      expect(validatePhone('123')).toBe('Phone number must be at least 10 digits');
      expect(validatePhone('1234567890')).toBeNull();
      expect(validatePhone('+1-234-567-8900')).toBeNull();
      expect(validatePhone('')).toBeNull(); // Optional
    });
  });

  describe('validateDate', () => {
    it('should validate dates', () => {
      expect(validateDate('invalid')).toBe('Invalid date format');
      expect(validateDate('2025-12-31')).toBe('Date cannot be in the future');
      expect(validateDate('2020-01-01')).toBeNull();
      expect(validateDate('')).toBeNull(); // Optional
    });
  });

  describe('validateNumberRange', () => {
    it('should validate number ranges', () => {
      expect(validateNumberRange(5, 10, 20, 'Value')).toBe('Value must be at least 10');
      expect(validateNumberRange(25, 10, 20, 'Value')).toBe('Value must be at most 20');
      expect(validateNumberRange(15, 10, 20, 'Value')).toBeNull();
    });
  });

  describe('validatePaymentAmount', () => {
    it('should validate payment amounts', () => {
      expect(validatePaymentAmount(0)).toBe('Payment amount must be greater than zero');
      expect(validatePaymentAmount(-10)).toBe('Payment amount must be greater than zero');
      expect(validatePaymentAmount(100)).toBeNull();
    });
  });

  describe('validatePatientData', () => {
    it('should validate patient data', () => {
      const result = validatePatientData({
        first_name: '',
        last_name: 'Doe',
      });
      expect(result.isValid).toBe(false);
      expect(result.errors.first_name).toBeDefined();
    });

    it('should pass valid patient data', () => {
      const result = validatePatientData({
        first_name: 'John',
        last_name: 'Doe',
        email: 'john@example.com',
      });
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateConsultationData', () => {
    it('should require at least one field', () => {
      const result = validateConsultationData({});
      expect(result.isValid).toBe(false);
      expect(result.errors.general).toBeDefined();
    });

    it('should pass if at least one field is filled', () => {
      const result = validateConsultationData({
        history: 'Patient history',
      });
      expect(result.isValid).toBe(true);
    });
  });
});
