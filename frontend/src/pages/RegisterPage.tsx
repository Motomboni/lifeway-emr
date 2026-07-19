/**
 * Registration Page
 * 
 * Multi-role user registration page.
 * Supports registration for all EMR roles.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import { validateEmail, validateRequired, validatePassword } from '../utils/validation';
import { registerUser, UserRole } from '../api/auth';
import AuthShell from '../components/auth/AuthShell';
import { APP_NAME } from '../config/branding';
import styles from '../styles/Register.module.css';

interface RoleOption {
  value: UserRole;
  label: string;
  description: string;
  icon: string;
}

const ROLE_OPTIONS: RoleOption[] = [
  {
    value: 'DOCTOR',
    label: 'Doctor',
    description: 'Consult, order tests, and prescribe treatment',
    icon: '👨‍⚕️',
  },
  {
    value: 'NURSE',
    label: 'Nurse',
    description: 'Record vitals, triage, and prepare visits',
    icon: '👩‍⚕️',
  },
  {
    value: 'IVF_SPECIALIST',
    label: 'IVF Specialist',
    description: 'Plan and track IVF cycles through outcomes',
    icon: '🧬',
  },
  {
    value: 'EMBRYOLOGIST',
    label: 'Embryologist',
    description: 'Culture, grade, and document embryos',
    icon: '🔬',
  },
  {
    value: 'LAB_TECH',
    label: 'Lab Scientist',
    description: 'Run diagnostics and release lab results',
    icon: '🧪',
  },
  {
    value: 'RADIOLOGY_TECH',
    label: 'Radiology Technician',
    description: 'Perform imaging and finalize radiology reports',
    icon: '📷',
  },
  {
    value: 'PHARMACIST',
    label: 'Pharmacist',
    description: 'Verify prescriptions and dispense medications',
    icon: '💊',
  },
  {
    value: 'RECEPTIONIST',
    label: 'Receptionist',
    description: 'Register patients, check in visits, collect payment',
    icon: '📋',
  },
  {
    value: 'PATIENT',
    label: 'Patient',
    description: 'Access records, results, and appointments',
    icon: '👤',
  },
];

const isProductionBuild = import.meta.env.PROD;
const AVAILABLE_ROLE_OPTIONS = isProductionBuild
  ? ROLE_OPTIONS.filter((role) => role.value === 'PATIENT')
  : ROLE_OPTIONS;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    role: '' as UserRole | '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState<UserRole | ''>('');
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  useEffect(() => {
    if (isProductionBuild && !selectedRole) {
      setSelectedRole('PATIENT');
      setFormData((prev) => ({ ...prev, role: 'PATIENT' }));
    }
  }, [selectedRole]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear error for this field
    if (submissionError) setSubmissionError(null);
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleRoleSelect = (role: UserRole) => {
    setSelectedRole(role);
    setFormData(prev => ({ ...prev, role }));
    if (submissionError) setSubmissionError(null);
    if (errors.role) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.role;
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Username validation
    const usernameError = validateRequired(formData.username, 'Username');
    if (usernameError) newErrors.username = usernameError;
    else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    // Email validation
    const emailError = validateRequired(formData.email, 'Email');
    if (emailError) {
      newErrors.email = emailError;
    } else {
      const emailFormatError = validateEmail(formData.email);
      if (emailFormatError) newErrors.email = emailFormatError;
    }

    // Password validation
    const passwordError = validatePassword(formData.password);
    if (passwordError) newErrors.password = passwordError;

    // Confirm password validation
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // Name validation
    const firstNameError = validateRequired(formData.first_name, 'First name');
    if (firstNameError) newErrors.first_name = firstNameError;

    const lastNameError = validateRequired(formData.last_name, 'Last name');
    if (lastNameError) newErrors.last_name = lastNameError;

    // Role validation
    if (!formData.role) {
      newErrors.role = 'Please select a role';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmissionError(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      await registerUser({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        password_confirm: formData.confirmPassword,
        first_name: formData.first_name,
        last_name: formData.last_name,
        role: formData.role as UserRole,
      });
      showSuccess(
        formData.role === 'PATIENT'
          ? 'Account created! Your clinic will verify your account before portal access is enabled.'
          : 'Account created! A clinic administrator must approve your account before you can sign in.'
      );

      navigate('/login');
    } catch (error) {
      const err = error as Error & { responseData?: Record<string, string | string[]> };
      const errorMessage = err.message || 'Registration failed';
      showError(errorMessage);
      setSubmissionError(errorMessage);

      // Parse backend field errors
      const data = err.responseData;
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const fieldErrors: Record<string, string> = {};
        for (const [field, value] of Object.entries(data)) {
          if (field === 'detail' || field === 'message' || field === 'error') continue;
          const msg = Array.isArray(value) ? value[0] : value;
          if (typeof msg === 'string') {
            let formField = field;
            if (field === 'password_confirm') formField = 'confirmPassword';
            if (field === 'slug') formField = 'orgSlug';
            if (field === 'name') formField = 'orgName';
            fieldErrors[formField] = msg;
          }
        }
        if (Object.keys(fieldErrors).length > 0) {
          setErrors(prev => ({ ...prev, ...fieldErrors }));
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell
      wide
      title={isProductionBuild ? 'Create patient account' : 'Create staff account'}
      subtitle={
        isProductionBuild
          ? `Patient registration for ${APP_NAME}`
          : `Registration for ${APP_NAME}`
      }
    >
      {submissionError && (
        <div className={styles.errorBanner} role="alert" aria-live="assertive">
          {submissionError}
        </div>
      )}

      <form onSubmit={handleSubmit} className={styles.registerForm}>

          <div className={styles.formSection}>
            <label className={styles.sectionLabel}>Select Your Role *</label>
              <div className={styles.roleGrid}>
                {AVAILABLE_ROLE_OPTIONS.map((role) => (
                  <button
                    key={role.value}
                    type="button"
                    data-register-role
                    data-selected={selectedRole === role.value ? 'true' : 'false'}
                    aria-pressed={selectedRole === role.value}
                    className={`${styles.roleOption} ${selectedRole === role.value ? styles.roleOptionSelected : ''}`}
                    onClick={() => handleRoleSelect(role.value)}
                  >
                    <span className={styles.roleIcon}>{role.icon}</span>
                    <span className={styles.roleLabel}>{role.label}</span>
                    <span className={styles.roleDescription}>{role.description}</span>
                  </button>
                ))}
              </div>
              {errors.role && <span className={styles.errorText}>{errors.role}</span>}
          </div>

          {/* Personal Information */}
          <div className={styles.formSection}>
            <label className={styles.sectionLabel}>Personal Information</label>
            <div className={styles.nameRow}>
              <div className={styles.formGroup}>
                <label htmlFor="first_name">First Name *</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={handleInputChange}
                  required
                  disabled={isLoading}
                  className={errors.first_name ? styles.inputError : ''}
                />
                {errors.first_name && <span className={styles.errorText}>{errors.first_name}</span>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="last_name">Last Name *</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={handleInputChange}
                  required
                  disabled={isLoading}
                  className={errors.last_name ? styles.inputError : ''}
                />
                {errors.last_name && <span className={styles.errorText}>{errors.last_name}</span>}
              </div>
            </div>
          </div>

          {/* Account Information */}
          <div className={styles.formSection}>
            <label className={styles.sectionLabel}>Account Information</label>

            <div className={styles.formGroup}>
              <label htmlFor="username">Username *</label>
              <input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleInputChange}
                required
                disabled={isLoading}
                className={errors.username ? styles.inputError : ''}
              />
              {errors.username && <span className={styles.errorText}>{errors.username}</span>}
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="email">Email *</label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                disabled={isLoading}
                className={errors.email ? styles.inputError : ''}
              />
              {errors.email && <span className={styles.errorText}>{errors.email}</span>}
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="password">Password *</label>
              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                disabled={isLoading}
                className={errors.password ? styles.inputError : ''}
              />
              {errors.password && <span className={styles.errorText}>{errors.password}</span>}
              <span className={styles.helpText}>
                At least 12 characters, with uppercase, lowercase, a number, and a special character (!@#$%^&* etc.)
              </span>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="confirmPassword">Confirm Password *</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
                disabled={isLoading}
                className={errors.confirmPassword ? styles.inputError : ''}
              />
              {errors.confirmPassword && <span className={styles.errorText}>{errors.confirmPassword}</span>}
            </div>
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>

        <div className={styles.footer}>
          <p>
            Already have an account?{' '}
            <Link to="/login" className={styles.link}>
              Sign In
            </Link>
          </p>
        </div>
      </form>
    </AuthShell>
  );
}
