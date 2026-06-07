/**
 * Registration Page
 * 
 * Multi-role user registration page.
 * Supports registration for all EMR roles.
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import { validateEmail, validateRequired, validatePassword } from '../utils/validation';
import { registerUser, UserRole } from '../api/auth';
import { signupOrganization } from '../api/organizations';
import Logo from '../components/common/Logo';
import styles from '../styles/Register.module.css';

interface RoleOption {
  value: UserRole;
  label: string;
  description: string;
  icon: string;
}

const ROLE_OPTIONS: RoleOption[] = [
  {
    value: 'ADMIN',
    label: 'Administrator',
    description: 'Full system access and management',
    icon: '👤',
  },
  {
    value: 'DOCTOR',
    label: 'Doctor',
    description: 'Create consultations, orders, and prescriptions',
    icon: '👨‍⚕️',
  },
  {
    value: 'NURSE',
    label: 'Nurse',
    description: 'Assist with patient care and clinical tasks',
    icon: '👩‍⚕️',
  },
  {
    value: 'IVF_SPECIALIST',
    label: 'IVF Specialist',
    description: 'Manage IVF cycles, procedures, and outcomes',
    icon: '🧬',
  },
  {
    value: 'EMBRYOLOGIST',
    label: 'Embryologist',
    description: 'Handle embryo culture, grading, and lab procedures',
    icon: '🔬',
  },
  {
    value: 'LAB_TECH',
    label: 'Lab Technician',
    description: 'Process lab orders and enter results',
    icon: '🧪',
  },
  {
    value: 'RADIOLOGY_TECH',
    label: 'Radiology Technician',
    description: 'Process radiology orders and enter reports',
    icon: '📷',
  },
  {
    value: 'PHARMACIST',
    label: 'Pharmacist',
    description: 'Dispense prescriptions',
    icon: '💊',
  },
  {
    value: 'RECEPTIONIST',
    label: 'Receptionist',
    description: 'Register patients and process payments',
    icon: '📋',
  },
  {
    value: 'PATIENT',
    label: 'Patient',
    description: 'View your medical records and appointments',
    icon: '👤',
  },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [registrationType, setRegistrationType] = useState<'staff' | 'clinic'>('clinic');

  const [formData, setFormData] = useState({
    orgName: '',
    orgSlug: '',
    orgEmail: '',
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

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;

    // Auto-generate slug from clinic name
    if (name === 'orgName' && registrationType === 'clinic') {
      const autoSlug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, '');
      setFormData(prev => ({ ...prev, [name]: value, orgSlug: autoSlug }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }

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

    if (registrationType === 'clinic') {
      const orgNameError = validateRequired(formData.orgName, 'Clinic Name');
      if (orgNameError) newErrors.orgName = orgNameError;

      const orgSlugError = validateRequired(formData.orgSlug, 'Clinic URL Slug');
      if (orgSlugError) newErrors.orgSlug = orgSlugError;
    }

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
    if (registrationType === 'staff' && !formData.role) {
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
      if (registrationType === 'clinic') {
        const res = await signupOrganization({
          name: formData.orgName,
          slug: formData.orgSlug,
          email: formData.orgEmail || formData.email,
          username: formData.username,
          password: formData.password,
          first_name: formData.first_name,
          last_name: formData.last_name,
        });
        showSuccess(res.message || 'Clinic created successfully! Please sign in.');
      } else {
        await registerUser({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          password_confirm: formData.confirmPassword,
          first_name: formData.first_name,
          last_name: formData.last_name,
          role: formData.role as UserRole,
        });
        showSuccess('Account created! Please provide your Username / ID to your Clinic Admin.');
      }

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
    <div className={styles.registerContainer}>
      <div className={styles.registerCard}>
        <div className={styles.header}>
          <Logo size="large" className={styles.headerLogo} />
          <p className={styles.subtitle}>Get started with Damianix EMR</p>
        </div>
        {submissionError && (
          <div className={styles.errorBanner}>{submissionError}</div>
        )}

        <div className={styles.tabContainer} style={{ display: 'flex', gap: '10px', marginBottom: '20px', padding: '0 20px' }}>
          <button
            onClick={() => setRegistrationType('clinic')}
            style={{ flex: 1, padding: '12px', background: registrationType === 'clinic' ? 'var(--primary-color)' : '#f0f0f0', color: registrationType === 'clinic' ? '#fff' : '#333', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Create entirely new Clinic
          </button>
          <button
            onClick={() => setRegistrationType('staff')}
            style={{ flex: 1, padding: '12px', background: registrationType === 'staff' ? 'var(--primary-color)' : '#f0f0f0', color: registrationType === 'staff' ? '#fff' : '#333', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Join existing Clinic
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.registerForm}>

          {/* Clinic Information (SaaS) */}
          {registrationType === 'clinic' && (
            <div className={styles.formSection}>
              <label className={styles.sectionLabel}>Clinic Details</label>

              <div className={styles.formGroup}>
                <label htmlFor="orgName">Clinic Name *</label>
                <input
                  id="orgName"
                  name="orgName"
                  type="text"
                  value={formData.orgName}
                  onChange={handleInputChange}
                  required
                  placeholder="E.g., Abuja General Hospital"
                  disabled={isLoading}
                  className={errors.orgName ? styles.inputError : ''}
                />
                {errors.orgName && <span className={styles.errorText}>{errors.orgName}</span>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="orgSlug">Clinic URL Slug *</label>
                <input
                  id="orgSlug"
                  name="orgSlug"
                  type="text"
                  value={formData.orgSlug}
                  onChange={handleInputChange}
                  required
                  placeholder="abuja-general"
                  disabled={isLoading}
                  className={errors.orgSlug ? styles.inputError : ''}
                />
                <span className={styles.helpText}>This will be your dedicated SaaS login URL path.</span>
                {errors.orgSlug && <span className={styles.errorText}>{errors.orgSlug}</span>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="orgEmail">Clinic Billing Email</label>
                <input
                  id="orgEmail"
                  name="orgEmail"
                  type="email"
                  value={formData.orgEmail}
                  onChange={handleInputChange}
                  placeholder="(Optional) Auto-fills from Admin Email below"
                  disabled={isLoading}
                />
              </div>
            </div>
          )}

          {/* Role Selection (Staff Only) */}
          {registrationType === 'staff' && (
            <div className={styles.formSection}>
              <label className={styles.sectionLabel}>Select Your Role *</label>
              <div className={styles.roleGrid}>
                {ROLE_OPTIONS.map((role) => (
                  <button
                    key={role.value}
                    type="button"
                    className={`${styles.roleCard} ${selectedRole === role.value ? styles.roleCardSelected : ''}`}
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
          )}

          {/* Personal Information */}
          <div className={styles.formSection}>
            <label className={styles.sectionLabel}>{registrationType === 'clinic' ? 'Your Admin Profile' : 'Personal Information'}</label>
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
        </form>

        <div className={styles.footer}>
          <p>
            Already have an account?{' '}
            <Link to="/login" className={styles.link}>
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
