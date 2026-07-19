/**
 * Patient Registration Page
 * 
 * Per EMR Rules:
 * - Receptionist and Admin access
 * - All patient data is PHI
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import { useOffline } from '../hooks/useOffline';
import { createPatient, verifyNationalHealthId } from '../api/patient';
import { queueOfflineAction } from '../utils/offlineQueue';
import { PatientCreateData } from '../types/patient';
import { fetchInsuranceProviders, InsuranceProvider } from '../api/insurance';
import BackToDashboard from '../components/common/BackToDashboard';
import { extractApiFieldErrors } from '../utils/errorHandler';
import styles from '../styles/PatientRegistration.module.css';

export default function PatientRegistrationPage() {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const isOffline = useOffline();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState<PatientCreateData>({
    first_name: '',
    last_name: '',
    middle_name: '',
    date_of_birth: '',
    gender: '' as any, // Use empty string to avoid controlled/uncontrolled warning
    phone: '',
    email: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relationship: '',
    national_id: '',
    national_health_id: '',
  });
  
  const [isSaving, setIsSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [registeredPatient, setRegisteredPatient] = useState<{ id: number; name: string } | null>(null);
  
  // Insurance and retainership state
  const [hasInsurance, setHasInsurance] = useState(false);
  const [insuranceProviders, setInsuranceProviders] = useState<InsuranceProvider[]>([]);
  const [insuranceData, setInsuranceData] = useState({
    provider_id: '',
    policy_number: '',
    coverage_type: 'FULL' as 'FULL' | 'PARTIAL',
    coverage_percentage: 100,
    valid_from: '',
    valid_to: '',
  });
  
  const [hasRetainership, setHasRetainership] = useState(false);
  const [retainershipData, setRetainershipData] = useState({
    type: '',
    start_date: '',
    end_date: '',
    amount: '',
  });
  
  // Patient Portal state
  const [createPortalAccount, setCreatePortalAccount] = useState(false);
  const [portalData, setPortalData] = useState({
    email: '',
    phone: '',
  });
  const [portalFieldsTouched, setPortalFieldsTouched] = useState({
    email: false,
    phone: false,
  });

  // Keep portal login fields aligned with Contact Information until manually edited
  useEffect(() => {
    if (!createPortalAccount) return;
    setPortalData((prev) => ({
      email: portalFieldsTouched.email ? prev.email : (formData.email ?? ''),
      phone: portalFieldsTouched.phone ? prev.phone : (formData.phone ?? ''),
    }));
  }, [
    createPortalAccount,
    formData.email,
    formData.phone,
    portalFieldsTouched.email,
    portalFieldsTouched.phone,
  ]);
  useEffect(() => {
    const loadProviders = async () => {
      try {
        const providers = await fetchInsuranceProviders();
        setInsuranceProviders(providers);
      } catch (error) {
        console.error('Failed to load insurance providers:', error);
      }
    };
    loadProviders();
  }, []);

  // Check if user is Receptionist or Admin
  if (user?.role !== 'RECEPTIONIST' && user?.role !== 'ADMIN') {
    return (
      <div className={styles.errorContainer}>
        <h2>Access Denied</h2>
        <p>Only Receptionists and Administrators can register patients.</p>
      </div>
    );
  }

  const handleFieldChange = (field: keyof PatientCreateData, value: string | undefined) => {
    setFormData(prev => ({
      ...prev,
      // Ensure string fields always have string values (not undefined) to avoid controlled/uncontrolled warning
      [field]: value ?? (field === 'date_of_birth' ? '' : '')
    }));
    
    // Clear field error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Validate required fields
    if (!formData.first_name.trim() || !formData.last_name.trim()) {
      showError('First name and last name are required');
      return;
    }
    
    // Validate portal account requirements
    if (createPortalAccount) {
      if (!portalData.email || !portalData.email.trim()) {
        showError('Email is required when creating a patient portal account');
        setFieldErrors(prev => ({ ...prev, portal_email: 'Email is required for portal access' }));
        return;
      }
      
      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(portalData.email)) {
        showError('Please enter a valid email address');
        setFieldErrors(prev => ({ ...prev, portal_email: 'Invalid email format' }));
        return;
      }
    }

    // Prevent double submission
    if (isSaving) {
      return;
    }

    setIsSaving(true);

    try {
      // Clean up form data - remove empty strings and undefined values
      const cleanedData: any = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
      };
      
      // Only include optional fields if they have values
      if (formData.middle_name?.trim()) {
        cleanedData.middle_name = formData.middle_name.trim();
      }
      if (formData.date_of_birth) {
        cleanedData.date_of_birth = formData.date_of_birth;
      }
      if (formData.gender && formData.gender.trim()) {
        cleanedData.gender = formData.gender.trim();
      }
      if (formData.phone?.trim()) {
        cleanedData.phone = formData.phone.trim();
      }
      if (formData.email?.trim()) {
        cleanedData.email = formData.email.trim();
      }
      if (formData.address?.trim()) {
        cleanedData.address = formData.address.trim();
      }
      if (formData.emergency_contact_name?.trim()) {
        cleanedData.emergency_contact_name = formData.emergency_contact_name.trim();
      }
      if (formData.emergency_contact_phone?.trim()) {
        cleanedData.emergency_contact_phone = formData.emergency_contact_phone.trim();
      }
      if (formData.emergency_contact_relationship?.trim()) {
        cleanedData.emergency_contact_relationship = formData.emergency_contact_relationship.trim();
      }
      if (formData.national_id?.trim()) {
        cleanedData.national_id = formData.national_id.trim();
      }
      if (formData.national_health_id?.trim()) {
        cleanedData.national_health_id = formData.national_health_id.trim();
      }
      
      // Add insurance data if patient has insurance
      if (hasInsurance) {
        cleanedData.has_insurance = true;
        if (insuranceData.provider_id) {
          cleanedData.insurance_provider_id = parseInt(insuranceData.provider_id);
        }
        if (insuranceData.policy_number?.trim()) {
          cleanedData.insurance_policy_number = insuranceData.policy_number.trim();
        }
        cleanedData.insurance_coverage_type = insuranceData.coverage_type;
        cleanedData.insurance_coverage_percentage = insuranceData.coverage_percentage;
        if (insuranceData.valid_from) {
          cleanedData.insurance_valid_from = insuranceData.valid_from;
        }
        if (insuranceData.valid_to) {
          cleanedData.insurance_valid_to = insuranceData.valid_to;
        }
      }
      
      // Add retainership data if patient has retainership
      if (hasRetainership) {
        cleanedData.has_retainership = true;
        if (retainershipData.type?.trim()) {
          cleanedData.retainership_type = retainershipData.type.trim();
        }
        if (retainershipData.start_date) {
          cleanedData.retainership_start_date = retainershipData.start_date;
        }
        if (retainershipData.end_date) {
          cleanedData.retainership_end_date = retainershipData.end_date;
        }
        if (retainershipData.amount) {
          cleanedData.retainership_amount = parseFloat(retainershipData.amount);
        }
      }
      
      // Add patient portal data if portal account requested
      if (createPortalAccount) {
        cleanedData.create_portal_account = true;
        cleanedData.portal_enabled = true;
        if (portalData.email?.trim()) {
          cleanedData.portal_email = portalData.email.trim();
        }
        if (portalData.phone?.trim()) {
          cleanedData.portal_phone = portalData.phone.trim();
        }
      }

      if (isOffline) {
        if (createPortalAccount) {
          showError('Portal accounts require connectivity. Save basic registration offline only.');
          setIsSaving(false);
          return;
        }
        await queueOfflineAction('REGISTER_PATIENT', cleanedData);
        showSuccess('Patient queued — sync from Offline Clinic Queue when online');
        setIsSaving(false);
        navigate('/offline-queue');
        return;
      }

      const patient = await createPatient(cleanedData);

      if (formData.national_health_id?.trim() && formData.date_of_birth) {
        try {
          const verifyResult = await verifyNationalHealthId({
            patient_id: patient.id,
            id_number: formData.national_health_id.trim(),
            name: `${patient.first_name} ${patient.last_name}`.trim(),
            dob: formData.date_of_birth,
          });
          if (verifyResult.id_verified) {
            showSuccess('Patient registered and NHID verified');
          } else {
            showSuccess('Patient registered (NHID verification pending)');
          }
        } catch {
          showSuccess('Patient registered (NHID verification failed — verify later in Patients)');
        }
      } else {
        showSuccess('Patient registered successfully');
      }
      
      // Store registered patient info and show success dialog
      const patientPk = patient.id;
      if (!patientPk) {
        showError('Patient was created but the server did not return an ID. Find them under Patients.');
        return;
      }
      setRegisteredPatient({
        id: patientPk,
        name: `${patient.first_name} ${patient.last_name}`.trim()
      });
    } catch (err) {
      // Log full error details for debugging
      console.error('Patient registration error:', err);
      if (err instanceof Error) {
        console.error('Error message:', err.message);
        console.error('Error stack:', err.stack);
      }
      
      const errorWithData = err as Error & { responseData?: unknown };
      const newFieldErrors: Record<string, string> = {
        ...extractApiFieldErrors(errorWithData.responseData),
      };
      let generalErrorMessage = errorWithData.message || 'Failed to register patient';

      if (Object.keys(newFieldErrors).length === 0) {
        const fieldErrorPattern = /(\w+):\s*([^;]+)/g;
        let match: RegExpExecArray | null;
        while ((match = fieldErrorPattern.exec(generalErrorMessage)) !== null) {
          newFieldErrors[match[1]] = match[2].trim();
        }
      }

      if (Object.keys(newFieldErrors).length === 0) {
        if (
          generalErrorMessage === 'An unexpected error occurred' ||
          generalErrorMessage.includes('unexpected')
        ) {
          generalErrorMessage =
            'Validation failed. Please check all required fields are filled correctly.';
        }
      } else {
        generalErrorMessage = 'Please correct the errors below';
      }
      
      // Update field errors state
      setFieldErrors(newFieldErrors);
      
      // Show general error message
      if (Object.keys(newFieldErrors).length > 0) {
        showError('Please correct the errors below');
      } else {
        showError(generalErrorMessage);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={styles.registrationContainer}>
      <BackToDashboard />
      <div className={styles.registrationCard}>
        <h1>Patient Registration</h1>
        
        <form 
          onSubmit={handleSubmit} 
          className={styles.registrationForm}
          noValidate
        >
          <div className={styles.formSection}>
            <h2>Personal Information</h2>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>First Name *</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => handleFieldChange('first_name', e.target.value)}
                  required
                />
              </div>
              <div className={styles.formGroup}>
                <label>Last Name *</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => handleFieldChange('last_name', e.target.value)}
                  required
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Middle Name</label>
              <input
                type="text"
                value={formData.middle_name}
                onChange={(e) => handleFieldChange('middle_name', e.target.value)}
              />
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Date of Birth</label>
                <input
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => handleFieldChange('date_of_birth', e.target.value)}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Gender</label>
                <select
                  value={formData.gender ?? ''}
                  onChange={(e) => handleFieldChange('gender', e.target.value || undefined)}
                >
                  <option value="">Select...</option>
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                  <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
                </select>
              </div>
            </div>
          </div>

          <div className={styles.formSection}>
            <h2>Contact Information</h2>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Phone</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleFieldChange('phone', e.target.value)}
                />
              </div>
              <div className={styles.formGroup}>
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleFieldChange('email', e.target.value)}
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label>Address</label>
              <textarea
                value={formData.address}
                onChange={(e) => handleFieldChange('address', e.target.value)}
                rows={3}
              />
            </div>
          </div>

          {/* Patient Portal — theme-aware (readable in dark mode) */}
          <div className={styles.portalSection}>
            <div className={styles.portalSectionRow}>
              <input
                type="checkbox"
                id="createPortalAccount"
                checked={createPortalAccount}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setCreatePortalAccount(checked);
                  if (checked) {
                    setPortalFieldsTouched({ email: false, phone: false });
                    setPortalData({
                      email: formData.email ?? '',
                      phone: formData.phone ?? '',
                    });
                  }
                  // Clear portal field errors when unchecking
                  if (!checked) {
                    setFieldErrors(prev => {
                      const newErrors = { ...prev };
                      delete newErrors.portal_email;
                      delete newErrors.portal_phone;
                      return newErrors;
                    });
                  }
                }}
                className={styles.portalCheckbox}
              />
              <div className={styles.portalSectionTextWrap}>
                <label htmlFor="createPortalAccount" className={styles.portalSectionLabel}>
                  Create Patient Portal Login
                </label>
                <p className={styles.portalSectionHint}>
                  Allows patient to log in to view appointments, records and bills.
                </p>
              </div>
            </div>

            {createPortalAccount && (
              <div className={styles.portalFields}>
                <div className={styles.portalFieldGrid}>
                  <div>
                    <label htmlFor="portalEmail" className={styles.portalFieldLabel}>
                      Email <span className={styles.portalRequired}>*</span>
                    </label>
                    <input
                      type="email"
                      id="portalEmail"
                      value={portalData.email}
                      onChange={(e) => {
                        setPortalFieldsTouched((prev) => ({ ...prev, email: true }));
                        setPortalData(prev => ({ ...prev, email: e.target.value }));
                        // Clear error when typing
                        if (fieldErrors.portal_email) {
                          setFieldErrors(prev => {
                            const newErrors = { ...prev };
                            delete newErrors.portal_email;
                            return newErrors;
                          });
                        }
                      }}
                      placeholder="patient@example.com"
                      className={`${styles.portalFieldInput} ${fieldErrors.portal_email ? styles.portalFieldInputError : ''}`}
                      required={createPortalAccount}
                      aria-invalid={!!fieldErrors.portal_email}
                      aria-describedby={fieldErrors.portal_email ? 'portal-email-error' : undefined}
                    />
                    {fieldErrors.portal_email && (
                      <p id="portal-email-error" className={styles.portalFieldError}>
                        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        {fieldErrors.portal_email}
                      </p>
                    )}
                    <p className={styles.portalFieldHelper}>
                      Used for login and notifications
                    </p>
                  </div>

                  <div>
                    <label htmlFor="portalPhone" className={styles.portalFieldLabel}>
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      id="portalPhone"
                      value={portalData.phone}
                      onChange={(e) => {
                        setPortalFieldsTouched((prev) => ({ ...prev, phone: true }));
                        setPortalData(prev => ({ ...prev, phone: e.target.value }));
                        // Clear error when typing
                        if (fieldErrors.portal_phone) {
                          setFieldErrors(prev => {
                            const newErrors = { ...prev };
                            delete newErrors.portal_phone;
                            return newErrors;
                          });
                        }
                      }}
                      placeholder="0712345678"
                      className={`${styles.portalFieldInput} ${fieldErrors.portal_phone ? styles.portalFieldInputError : ''}`}
                      aria-invalid={!!fieldErrors.portal_phone}
                      aria-describedby={fieldErrors.portal_phone ? 'portal-phone-error' : undefined}
                    />
                    {fieldErrors.portal_phone && (
                      <p id="portal-phone-error" className={styles.portalFieldError}>
                        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        {fieldErrors.portal_phone}
                      </p>
                    )}
                    <p className={styles.portalFieldHelper}>
                      Optional: For SMS notifications
                    </p>
                  </div>
                </div>

                <div className={styles.portalInfoBox}>
                  <div className={styles.portalInfoRow}>
                    <svg className={styles.portalInfoIcon} fill="currentColor" viewBox="0 0 20 20" aria-hidden>
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div className={styles.portalInfoText}>
                      <p className={styles.portalInfoTitle}>Portal Access Information</p>
                      <p className="mt-1">
                        A temporary password will be generated and sent to the patient's email. 
                        They will be required to change it on first login.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className={styles.formSection}>
            <h2>Emergency Contact</h2>
            <div className={styles.formGroup}>
              <label>Contact Name</label>
              <input
                type="text"
                value={formData.emergency_contact_name}
                onChange={(e) => handleFieldChange('emergency_contact_name', e.target.value)}
                placeholder="Full name of emergency contact"
              />
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label>Contact Phone</label>
                <input
                  type="tel"
                  value={formData.emergency_contact_phone}
                  onChange={(e) => handleFieldChange('emergency_contact_phone', e.target.value)}
                  placeholder="Phone number"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Relationship</label>
                <input
                  type="text"
                  value={formData.emergency_contact_relationship}
                  onChange={(e) => handleFieldChange('emergency_contact_relationship', e.target.value)}
                  placeholder="e.g., Spouse, Parent, Sibling, Friend"
                />
              </div>
            </div>
          </div>

          <div className={styles.formSection}>
            <h2>Identification</h2>
            <div className={styles.formGroup}>
              <label>National ID</label>
              <input
                type="text"
                value={formData.national_id}
                onChange={(e) => handleFieldChange('national_id', e.target.value)}
                className={fieldErrors.national_id ? styles.inputError : ''}
                aria-invalid={!!fieldErrors.national_id}
                aria-describedby={fieldErrors.national_id ? 'national_id-error' : undefined}
              />
              {fieldErrors.national_id && (
                <span id="national_id-error" className={styles.fieldError}>
                  {fieldErrors.national_id}
                </span>
              )}
            </div>
            <div className={styles.formGroup}>
              <label>National Health ID (NHID / NIN)</label>
              <input
                type="text"
                value={formData.national_health_id || ''}
                onChange={(e) => handleFieldChange('national_health_id', e.target.value)}
                placeholder="For NHIA claims — verified after registration if DOB is set"
              />
            </div>
          </div>

          <div className={styles.formSection}>
            <h2>Insurance Information</h2>
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={hasInsurance}
                  onChange={(e) => setHasInsurance(e.target.checked)}
                />
                Patient has insurance
              </label>
            </div>
            
            {hasInsurance && (
              <>
                <div className={styles.formGroup}>
                  <label>Insurance Provider *</label>
                  <select
                    value={insuranceData.provider_id}
                    onChange={(e) => setInsuranceData(prev => ({ ...prev, provider_id: e.target.value }))}
                    required={hasInsurance}
                  >
                    <option value="">Select Insurance Provider...</option>
                    {insuranceProviders.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} {provider.code ? `(${provider.code})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className={styles.formGroup}>
                  <label>Policy Number *</label>
                  <input
                    type="text"
                    value={insuranceData.policy_number}
                    onChange={(e) => setInsuranceData(prev => ({ ...prev, policy_number: e.target.value }))}
                    placeholder="Enter insurance policy number"
                    required={hasInsurance}
                  />
                </div>
                
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label>Coverage Type</label>
                    <select
                      value={insuranceData.coverage_type}
                      onChange={(e) => setInsuranceData(prev => ({ 
                        ...prev, 
                        coverage_type: e.target.value as 'FULL' | 'PARTIAL' 
                      }))}
                    >
                      <option value="FULL">Full Coverage</option>
                      <option value="PARTIAL">Partial Coverage</option>
                    </select>
                  </div>
                  
                  {insuranceData.coverage_type === 'PARTIAL' && (
                    <div className={styles.formGroup}>
                      <label>Coverage Percentage (%)</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={insuranceData.coverage_percentage}
                        onChange={(e) => setInsuranceData(prev => ({ 
                          ...prev, 
                          coverage_percentage: parseFloat(e.target.value) || 100 
                        }))}
                      />
                    </div>
                  )}
                </div>
                
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label>Valid From *</label>
                    <input
                      type="date"
                      value={insuranceData.valid_from}
                      onChange={(e) => setInsuranceData(prev => ({ ...prev, valid_from: e.target.value }))}
                      required={hasInsurance}
                    />
                  </div>
                  
                  <div className={styles.formGroup}>
                    <label>Valid To (Optional)</label>
                    <input
                      type="date"
                      value={insuranceData.valid_to}
                      onChange={(e) => setInsuranceData(prev => ({ ...prev, valid_to: e.target.value }))}
                    />
                  </div>
                </div>
              </>
            )}
          </div>

          <div className={styles.formSection}>
            <h2>Retainership Information</h2>
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={hasRetainership}
                  onChange={(e) => setHasRetainership(e.target.checked)}
                />
                Patient has retainership
              </label>
            </div>
            
            {hasRetainership && (
              <>
                <div className={styles.formGroup}>
                  <label>Retainership Type *</label>
                  <input
                    type="text"
                    value={retainershipData.type}
                    onChange={(e) => setRetainershipData(prev => ({ ...prev, type: e.target.value }))}
                    placeholder="e.g., Monthly, Quarterly, Annual, Corporate"
                    required={hasRetainership}
                  />
                </div>
                
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label>Start Date *</label>
                    <input
                      type="date"
                      value={retainershipData.start_date}
                      onChange={(e) => setRetainershipData(prev => ({ ...prev, start_date: e.target.value }))}
                      required={hasRetainership}
                    />
                  </div>
                  
                  <div className={styles.formGroup}>
                    <label>End Date (Optional)</label>
                    <input
                      type="date"
                      value={retainershipData.end_date}
                      onChange={(e) => setRetainershipData(prev => ({ ...prev, end_date: e.target.value }))}
                    />
                  </div>
                </div>
                
                <div className={styles.formGroup}>
                  <label>Retainership Amount (₦) *</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={retainershipData.amount}
                    onChange={(e) => setRetainershipData(prev => ({ ...prev, amount: e.target.value }))}
                    placeholder="0.00"
                    required={hasRetainership}
                  />
                </div>
              </>
            )}
          </div>

          <div className={styles.formActions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={() => navigate('/dashboard')}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={isSaving || !formData.first_name.trim() || !formData.last_name.trim()}
            >
              {isSaving ? 'Registering...' : 'Register Patient'}
            </button>
          </div>
        </form>
      </div>

      {/* Success Dialog */}
      {registeredPatient && (
        <div className={styles.successDialogOverlay} onClick={() => setRegisteredPatient(null)}>
          <div className={styles.successDialog} onClick={(e) => e.stopPropagation()}>
            <div className={styles.successIcon}>✓</div>
            <h2>Patient Registered Successfully!</h2>
            <p>Patient: <strong>{registeredPatient.name}</strong></p>
            <p className={styles.successMessage}>What would you like to do next?</p>
            
            <div className={styles.successActions}>
              <button
                className={styles.actionButton}
                onClick={() => {
                  setRegisteredPatient(null);
                  navigate(`/visits/new?patient=${registeredPatient.id}`);
                }}
              >
                Create Visit
              </button>
              <button
                className={styles.actionButton}
                onClick={() => {
                  setRegisteredPatient(null);
                  navigate(`/patients`);
                }}
              >
                View All Patients
              </button>
              <button
                className={styles.actionButton}
                onClick={() => {
                  setRegisteredPatient(null);
                  // Reset form for another registration
                  setFormData({
                    first_name: '',
                    last_name: '',
                    middle_name: '',
                    date_of_birth: '',
                    gender: '' as any,
                    phone: '',
                    email: '',
                    address: '',
                    emergency_contact_name: '',
                    emergency_contact_phone: '',
                    emergency_contact_relationship: '',
                    national_id: '',
                  });
                  setFieldErrors({});
                  setHasInsurance(false);
                  setInsuranceData({
                    provider_id: '',
                    policy_number: '',
                    coverage_type: 'FULL',
                    coverage_percentage: 100,
                    valid_from: '',
                    valid_to: '',
                  });
                  setHasRetainership(false);
                  setRetainershipData({
                    type: '',
                    start_date: '',
                    end_date: '',
                    amount: '',
                  });
                  setCreatePortalAccount(false);
                  setPortalData({
                    email: '',
                    phone: '',
                  });
                  setPortalFieldsTouched({ email: false, phone: false });
                }}
              >
                Register Another Patient
              </button>
              <button
                className={styles.actionButtonSecondary}
                onClick={() => {
                  setRegisteredPatient(null);
                  navigate('/dashboard');
                }}
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
