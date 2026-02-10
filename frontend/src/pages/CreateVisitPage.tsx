/**
 * Create Visit Page
 * 
 * Per EMR Rules:
 * - Receptionist can create visits
 * - Visit must be associated with a patient
 * - Visit starts with status=OPEN, payment_status=UNPAID (CASH) or INSURANCE_PENDING (INSURANCE)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import { searchPatients, getPatient } from '../api/patient';
import { createVisit } from '../api/visits';
import { fetchAppointments } from '../api/appointment';
import { Patient } from '../types/patient';
import { Appointment } from '../types/appointment';
import { VisitCreateData } from '../types/visit';
import BackToDashboard from '../components/common/BackToDashboard';
import { logger } from '../utils/logger';
import styles from '../styles/CreateVisit.module.css';

export default function CreateVisitPage() {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [paymentType, setPaymentType] = useState<'CASH' | 'INSURANCE'>('CASH');
  
  // Visit form fields
  const [visitType, setVisitType] = useState<'CONSULTATION' | 'FOLLOW_UP' | 'EMERGENCY' | 'ROUTINE' | 'SPECIALIST' | ''>('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [selectedAppointment, setSelectedAppointment] = useState<number | null>(null);
  const [availableAppointments, setAvailableAppointments] = useState<Appointment[]>([]);
  const [loadingAppointments, setLoadingAppointments] = useState(false);

  // Check if patient ID is in URL params
  useEffect(() => {
    const patientId = searchParams.get('patient');
    if (patientId) {
      loadPatient(parseInt(patientId));
    }
  }, [searchParams]);

  const loadPatient = async (patientId: number) => {
    try {
      const patient = await getPatient(patientId);
      setSelectedPatient(patient);
      // Auto-set payment type to INSURANCE if patient has active insurance
      // (Backend will also auto-detect, but this improves UX)
      if (patient.has_active_insurance) {
        setPaymentType('INSURANCE');
      } else {
        setPaymentType('CASH');
      }
      // Load available appointments for this patient
      await loadPatientAppointments(patientId);
    } catch (err) {
      showError('Failed to load patient');
    }
  };
  
  const loadPatientAppointments = async (patientId: number) => {
    try {
      setLoadingAppointments(true);
      // Fetch appointments - we'll filter for SCHEDULED and CONFIRMED on the frontend
      const appointments = await fetchAppointments({ 
        patient: patientId
      });
      const appointmentsArray = Array.isArray(appointments) 
        ? appointments 
        : (appointments as any).results || [];
      // Filter for scheduled or confirmed appointments only
      const available = appointmentsArray.filter((apt: Appointment) => 
        apt.status === 'SCHEDULED' || apt.status === 'CONFIRMED'
      );
      setAvailableAppointments(available);
    } catch (err) {
      // Silently fail - appointments are optional
      setAvailableAppointments([]);
    } finally {
      setLoadingAppointments(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const results = await searchPatients(searchQuery);
      setSearchResults(results);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setSearchResults([]);
    setSearchQuery('');
    // Auto-set payment type to INSURANCE if patient has active insurance
    // (Backend will also auto-detect, but this improves UX)
    if (patient.has_active_insurance) {
      setPaymentType('INSURANCE');
    } else {
      setPaymentType('CASH');
    }
    // Load appointments for selected patient
    loadPatientAppointments(patient.id);
  };

  const handleCreateVisit = async () => {
    if (!selectedPatient) {
      showError('Please select a patient');
      return;
    }

    setIsCreating(true);
    try {
      const visitData: VisitCreateData = {
        patient: selectedPatient.id,
        payment_type: paymentType,
        // payment_status will be set by backend based on payment_type (UNPAID for CASH, INSURANCE_PENDING for INSURANCE)
      };
      
      // Add optional fields if provided
      if (visitType) {
        visitData.visit_type = visitType as any;
      }
      if (chiefComplaint.trim()) {
        visitData.chief_complaint = chiefComplaint.trim();
      }
      if (selectedAppointment) {
        visitData.appointment = selectedAppointment;
      }
      
      const visit = await createVisit(visitData);
      logger.debug('Visit created:', visit);
      
      if (!visit || !visit.id) {
        showError('Visit was created but ID is missing. Please check the visits list.');
        navigate('/visits');
        return;
      }
      
      showSuccess('Visit created successfully');
      
      // Ensure visit is fully committed to database before redirect
      // Use a longer delay and ensure the visit ID is valid
      if (!visit.id) {
        showError('Visit was created but ID is missing. Please check the visits list.');
        navigate('/visits');
        return;
      }
      
      // Wait a bit longer to ensure database transaction is committed
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Redirect based on payment type and user role
      // Per EMR Rules: Consultation requires payment to be PAID or SETTLED
      // Pass visit data in state to avoid immediate refetch
      // Note: New visits start with UNPAID or INSURANCE_PENDING, so doctors won't be redirected to consultation immediately
      if (user?.role === 'DOCTOR' && (visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED')) {
        // If payment is cleared and user is a doctor, go to consultation
        navigate(`/visits/${visit.id}/consultation`, { 
          replace: true,
          state: { visit } // Pass visit data to avoid refetch
        });
      } else {
        // Otherwise, go to visit details page
        // For Receptionist, this allows them to see the visit and process payment
        navigate(`/visits/${visit.id}`, { 
          replace: true,
          state: { visit } // Pass visit data to avoid refetch
        });
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create visit');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className={styles.createVisitContainer}>
      <BackToDashboard />
      <div className={styles.createVisitCard}>
        <h1>Create New Visit</h1>

        {/* Patient Search Section */}
        {!selectedPatient && (
          <div className={styles.searchSection}>
            <h2>Select Patient</h2>
            <div className={styles.searchBox}>
              <input
                type="text"
                placeholder="Search by name, patient ID, national ID, or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                type="button"
                onClick={handleSearch}
                disabled={isSearching || !searchQuery.trim()}
                className={styles.searchButton}
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className={styles.searchResults}>
                {searchResults.map(patient => (
                  <div
                    key={patient.id}
                    className={styles.patientCard}
                    onClick={() => handleSelectPatient(patient)}
                  >
                    <div className={styles.patientInfo}>
                      <strong>{patient.full_name}</strong>
                      <div className={styles.patientMeta}>
                        <span>ID: {patient.patient_id}</span>
                        {patient.phone && <span>Phone: {patient.phone}</span>}
                        {patient.national_id && <span>NID: {patient.national_id}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Selected Patient and Visit Details */}
        {selectedPatient && (
          <div className={styles.visitDetailsSection}>
            <div className={styles.selectedPatient}>
              <h2>Selected Patient</h2>
              <div className={styles.patientCard}>
                <div className={styles.patientInfo}>
                  <strong>{selectedPatient.full_name}</strong>
                  <div className={styles.patientMeta}>
                    <span>ID: {selectedPatient.patient_id}</span>
                    {selectedPatient.phone && <span>Phone: {selectedPatient.phone}</span>}
                    {selectedPatient.age && <span>Age: {selectedPatient.age}</span>}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedPatient(null)}
                  className={styles.changeButton}
                >
                  Change
                </button>
              </div>
            </div>

            <div className={styles.visitOptions}>
              <h2>Visit Details</h2>
              
              <div className={styles.formGroup}>
                <label>Visit Type</label>
                <select
                  value={visitType}
                  onChange={(e) => setVisitType(e.target.value as any)}
                >
                  <option value="">Select visit type...</option>
                  <option value="CONSULTATION">Consultation</option>
                  <option value="FOLLOW_UP">Follow-up</option>
                  <option value="EMERGENCY">Emergency</option>
                  <option value="ROUTINE">Routine</option>
                  <option value="SPECIALIST">Specialist</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Chief Complaint</label>
                <textarea
                  value={chiefComplaint}
                  onChange={(e) => setChiefComplaint(e.target.value)}
                  placeholder="Enter reason for visit (e.g., Headache, Fever, Routine checkup...)"
                  rows={3}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Link to Appointment (Optional)</label>
                {loadingAppointments ? (
                  <p className={styles.helpText}>Loading appointments...</p>
                ) : availableAppointments.length > 0 ? (
                  <select
                    value={selectedAppointment || ''}
                    onChange={(e) => setSelectedAppointment(e.target.value ? parseInt(e.target.value) : null)}
                  >
                    <option value="">No appointment</option>
                    {availableAppointments.map((apt: Appointment) => (
                      <option key={apt.id} value={apt.id}>
                        {new Date(apt.appointment_date).toLocaleString()} - {apt.reason || 'No reason'}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className={styles.helpText}>No scheduled appointments found for this patient</p>
                )}
              </div>

              <div className={styles.formGroup}>
                <label>Payment Type</label>
                <select
                  value={paymentType}
                  onChange={(e) => setPaymentType(e.target.value as 'CASH' | 'INSURANCE')}
                >
                  <option value="CASH">Cash Payment</option>
                  <option value="INSURANCE">Insurance/HMO</option>
                </select>
                {selectedPatient.has_active_insurance && paymentType === 'INSURANCE' && (
                  <p className={styles.helpText} style={{ color: '#059669', fontWeight: 500 }}>
                    ✓ Insurance auto-detected: Patient has active insurance. Payment type automatically set to Insurance.
                  </p>
                )}
                {selectedPatient.has_active_insurance && paymentType === 'CASH' && (
                  <p className={styles.helpText} style={{ color: '#dc2626' }}>
                    ⚠ Patient has active insurance, but payment type is set to Cash. You can change it to Insurance if needed.
                  </p>
                )}
                {!selectedPatient.has_active_insurance && (
                  <p className={styles.helpText}>
                    Note: Cash visits start as UNPAID. Insurance visits start as INSURANCE_PENDING. 
                    Payment must be PAID or SETTLED before clinical actions (consultation, lab orders, etc.)
                  </p>
                )}
              </div>
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
                type="button"
                className={styles.createButton}
                onClick={handleCreateVisit}
                disabled={isCreating}
              >
                {isCreating ? 'Creating...' : 'Create Visit'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
