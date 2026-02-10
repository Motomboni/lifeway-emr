/**
 * Client-side Form Validation Utilities
 * 
 * Provides reusable validation functions for forms.
 */

export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

/**
 * Validate required field
 */
export function validateRequired(value: any, fieldName: string): string | null {
  if (value === null || value === undefined || value === '') {
    return `${fieldName} is required`;
  }
  if (typeof value === 'string' && value.trim() === '') {
    return `${fieldName} cannot be empty`;
  }
  return null;
}

/**
 * Validate email format
 */
export function validateEmail(email: string): string | null {
  if (!email) return null; // Optional field
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'Invalid email format';
  }
  return null;
}

/** Min length and complexity to match backend (core.password_validators). */
const PASSWORD_MIN_LENGTH = 12;
const PASSWORD_SPECIAL = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/;

/**
 * Validate password for registration (matches backend: 12+ chars, upper, lower, digit, special).
 */
export function validatePassword(password: string): string | null {
  if (!password) return 'Password is required';
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters`;
  }
  if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter';
  if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter';
  if (!/\d/.test(password)) return 'Password must contain at least one digit';
  if (!PASSWORD_SPECIAL.test(password)) {
    return 'Password must contain at least one special character (!@#$%^&* etc.)';
  }
  return null;
}

/**
 * Validate phone number
 */
export function validatePhone(phone: string): string | null {
  if (!phone) return null; // Optional field
  
  // Basic phone validation (adjust regex as needed)
  const phoneRegex = /^[\d\s\-\+\(\)]+$/;
  if (!phoneRegex.test(phone)) {
    return 'Invalid phone number format';
  }
  if (phone.replace(/\D/g, '').length < 10) {
    return 'Phone number must be at least 10 digits';
  }
  return null;
}

/**
 * Validate date
 */
export function validateDate(date: string): string | null {
  if (!date) return null; // Optional field
  
  const dateObj = new Date(date);
  if (isNaN(dateObj.getTime())) {
    return 'Invalid date format';
  }
  
  // Check if date is not in the future
  if (dateObj > new Date()) {
    return 'Date cannot be in the future';
  }
  
  return null;
}

/**
 * Validate number range
 */
export function validateNumberRange(
  value: number,
  min?: number,
  max?: number,
  fieldName: string = 'Value'
): string | null {
  if (value === null || value === undefined) {
    return null; // Optional field
  }
  
  if (typeof value !== 'number' || isNaN(value)) {
    return `${fieldName} must be a valid number`;
  }
  
  if (min !== undefined && value < min) {
    return `${fieldName} must be at least ${min}`;
  }
  
  if (max !== undefined && value > max) {
    return `${fieldName} must be at most ${max}`;
  }
  
  return null;
}

/**
 * Validate string length
 */
export function validateLength(
  value: string,
  min?: number,
  max?: number,
  fieldName: string = 'Field'
): string | null {
  if (!value) return null; // Optional field
  
  if (min !== undefined && value.length < min) {
    return `${fieldName} must be at least ${min} characters`;
  }
  
  if (max !== undefined && value.length > max) {
    return `${fieldName} must be at most ${max} characters`;
  }
  
  return null;
}

/**
 * Validate payment amount
 */
export function validatePaymentAmount(amount: number): string | null {
  if (amount === null || amount === undefined) {
    return 'Payment amount is required';
  }
  
  if (typeof amount !== 'number' || isNaN(amount)) {
    return 'Payment amount must be a valid number';
  }
  
  if (amount <= 0) {
    return 'Payment amount must be greater than zero';
  }
  
  if (amount > 1000000) {
    return 'Payment amount is too large';
  }
  
  return null;
}

/**
 * Validate patient data
 */
export function validatePatientData(data: {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
}): ValidationResult {
  const errors: Record<string, string> = {};

  const firstNameError = validateRequired(data.first_name, 'First name');
  if (firstNameError) errors.first_name = firstNameError;

  const lastNameError = validateRequired(data.last_name, 'Last name');
  if (lastNameError) errors.last_name = lastNameError;

  if (data.email) {
    const emailError = validateEmail(data.email);
    if (emailError) errors.email = emailError;
  }

  if (data.phone) {
    const phoneError = validatePhone(data.phone);
    if (phoneError) errors.phone = phoneError;
  }

  if (data.date_of_birth) {
    const dateError = validateDate(data.date_of_birth);
    if (dateError) errors.date_of_birth = dateError;
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validate consultation data
 */
export function validateConsultationData(data: {
  history?: string;
  examination?: string;
  diagnosis?: string;
  clinical_notes?: string;
}): ValidationResult {
  const errors: Record<string, string> = {};

  // At least one field should be filled
  const hasContent = 
    (data.history && data.history.trim()) ||
    (data.examination && data.examination.trim()) ||
    (data.diagnosis && data.diagnosis.trim()) ||
    (data.clinical_notes && data.clinical_notes.trim());

  if (!hasContent) {
    errors.general = 'At least one field (history, examination, diagnosis, or clinical notes) must be filled';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validate lab order data
 */
export function validateLabOrderData(data: {
  tests_requested?: string[];
  clinical_indication?: string;
}): ValidationResult {
  const errors: Record<string, string> = {};

  if (!data.tests_requested || data.tests_requested.length === 0) {
    errors.tests_requested = 'At least one test must be selected';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validate prescription data
 */
export function validatePrescriptionData(data: {
  drug?: string;
  dosage?: string;
  frequency?: string;
  duration?: string;
  quantity?: number;
}): ValidationResult {
  const errors: Record<string, string> = {};

  const drugError = validateRequired(data.drug, 'Drug name');
  if (drugError) errors.drug = drugError;

  if (data.quantity !== undefined && data.quantity !== null) {
    const quantityError = validateNumberRange(data.quantity, 1, undefined, 'Quantity');
    if (quantityError) errors.quantity = quantityError;
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
