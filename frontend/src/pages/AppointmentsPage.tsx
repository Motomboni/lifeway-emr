/**
 * Appointments Page
 * 
 * For scheduling and managing patient appointments.
 * Per EMR Rules: Receptionist and Doctor can create/manage appointments, Doctors can view their own.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchAppointments,
  fetchUpcomingAppointments,
  fetchTodayAppointments,
  createAppointment,
  updateAppointment,
  cancelAppointment,
  confirmAppointment,
  completeAppointment,
  AppointmentFilters,
  PaginatedAppointmentResponse,
} from '../api/appointment';
import { fetchPatients, searchPatients } from '../api/patient';
import { Appointment, AppointmentCreateData } from '../types/appointment';
import { Patient } from '../types/patient';
import { User } from '../types/user';
import { apiRequest } from '../utils/apiClient';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Appointments.module.css';

export default function AppointmentsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null);
  
  // Filters
  const [filters, setFilters] = useState<AppointmentFilters>({
    status: undefined,
    date_from: undefined,
    date_to: undefined,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'all' | 'upcoming' | 'today'>('all');
  
  // Form data
  const [formData, setFormData] = useState<AppointmentCreateData>({
    patient: 0,
    doctor: 0,
    appointment_date: '',
    duration_minutes: 30,
    reason: '',
    notes: '',
  });
  
  // Patient and doctor selection
  const [patientSearchQuery, setPatientSearchQuery] = useState('');
  const [patientSearchResults, setPatientSearchResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [doctors, setDoctors] = useState<User[]>([]);
  const [loadingDoctors, setLoadingDoctors] = useState(false);
  const [isSearchingPatients, setIsSearchingPatients] = useState(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadAppointments();
  }, [viewMode, filters.status, filters.date_from, filters.date_to]);

  // Load doctors when form is shown
  useEffect(() => {
    if (showCreateForm && canManage && doctors.length === 0) {
      loadDoctors();
    }
  }, [showCreateForm]);

  // Auto-select current doctor when doctor opens create form
  useEffect(() => {
    if (showCreateForm && user?.role === 'DOCTOR' && !editingAppointment && doctors.length > 0 && formData.doctor === 0) {
      // Find current user in doctors list and auto-select
      const currentDoctor = doctors.find(d => d.id === user.id);
      if (currentDoctor) {
        setFormData({ ...formData, doctor: currentDoctor.id });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCreateForm, doctors, user]);

  // Load initial patients when form is shown
  useEffect(() => {
    if (showCreateForm && (user?.role === 'RECEPTIONIST' || user?.role === 'DOCTOR')) {
      loadInitialPatients();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCreateForm]);

  const loadInitialPatients = async () => {
    try {
      // Load recent patients to populate dropdown initially
      const patients = await fetchPatients();
      setPatientSearchResults(patients.slice(0, 10)); // Show first 10 patients
    } catch (error) {
      console.error('Error loading patients:', error);
      // Don't show error, just leave empty - user can search
    }
  };

  const loadAppointments = async () => {
    try {
      setLoading(true);
      let response;
      
      if (viewMode === 'upcoming') {
        response = await fetchUpcomingAppointments();
      } else if (viewMode === 'today') {
        response = await fetchTodayAppointments();
      } else {
        response = await fetchAppointments(filters);
      }
      
      const appointmentsArray = Array.isArray(response)
        ? response
        : (response as PaginatedAppointmentResponse)?.results || [];
      setAppointments(appointmentsArray);
    } catch (error) {
      console.error('Error loading appointments:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load appointments';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadDoctors = async () => {
    try {
      setLoadingDoctors(true);
      // Use the dedicated doctors endpoint
      const response = await apiRequest<User[]>('/auth/doctors/');
      if (Array.isArray(response)) {
        setDoctors(response);
      } else {
        setDoctors([]);
      }
    } catch (error) {
      console.error('Error loading doctors:', error);
      // If endpoint doesn't exist, we'll handle it gracefully
      setDoctors([]);
    } finally {
      setLoadingDoctors(false);
    }
  };

  const handlePatientSearch = async (query?: string) => {
    const searchTerm = query !== undefined ? query : patientSearchQuery;
    
    if (!searchTerm.trim()) {
      // If no search term, show initial list of patients
      await loadInitialPatients();
      return;
    }

    try {
      setIsSearchingPatients(true);
      const results = await searchPatients(searchTerm);
      setPatientSearchResults(results);
    } catch (error) {
      console.error('Error searching patients:', error);
      showError('Failed to search patients');
      setPatientSearchResults([]);
    } finally {
      setIsSearchingPatients(false);
    }
  };

  const handleSelectPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setFormData({ ...formData, patient: patient.id });
    setPatientSearchQuery('');
    setPatientSearchResults([]);
  };

  const handleCreate = async () => {
    if (!formData.patient || !formData.doctor || !formData.appointment_date) {
      showError('Please fill in all required fields');
      return;
    }

    try {
      setIsSaving(true);
      await createAppointment(formData);
      showSuccess('Appointment created successfully');
      setShowCreateForm(false);
      resetForm();
      loadAppointments();
    } catch (error) {
      console.error('Error creating appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create appointment';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingAppointment) return;

    try {
      setIsSaving(true);
      await updateAppointment(editingAppointment.id, {
        appointment_date: formData.appointment_date,
        duration_minutes: formData.duration_minutes,
        reason: formData.reason,
        notes: formData.notes,
      });
      showSuccess('Appointment updated successfully');
      setEditingAppointment(null);
      resetForm();
      loadAppointments();
    } catch (error) {
      console.error('Error updating appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to update appointment';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = async (appointmentId: number) => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) {
      return;
    }

    try {
      await cancelAppointment(appointmentId);
      showSuccess('Appointment cancelled successfully');
      loadAppointments();
    } catch (error) {
      console.error('Error cancelling appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to cancel appointment';
      showError(errorMessage);
    }
  };

  const handleConfirm = async (appointmentId: number) => {
    try {
      await confirmAppointment(appointmentId);
      showSuccess('Appointment confirmed');
      loadAppointments();
    } catch (error) {
      console.error('Error confirming appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to confirm appointment';
      showError(errorMessage);
    }
  };

  const handleComplete = async (appointmentId: number) => {
    try {
      await completeAppointment(appointmentId);
      showSuccess('Appointment marked as completed');
      loadAppointments();
    } catch (error) {
      console.error('Error completing appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to complete appointment';
      showError(errorMessage);
    }
  };

  const handleEdit = (appointment: Appointment) => {
    setEditingAppointment(appointment);
    setFormData({
      patient: appointment.patient,
      doctor: appointment.doctor,
      appointment_date: new Date(appointment.appointment_date).toISOString().slice(0, 16),
      duration_minutes: appointment.duration_minutes,
      reason: appointment.reason || '',
      notes: appointment.notes || '',
    });
    setShowCreateForm(true);
  };

  const resetForm = () => {
    setFormData({
      patient: 0,
      doctor: 0,
      appointment_date: '',
      duration_minutes: 30,
      reason: '',
      notes: '',
    });
    setSelectedPatient(null);
    setPatientSearchQuery('');
    setPatientSearchResults([]);
    // Clear search timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
      searchTimeoutRef.current = null;
    }
    // Reload initial patients when form is reset
    if (user?.role === 'RECEPTIONIST' || user?.role === 'DOCTOR') {
      loadInitialPatients();
    }
  };

  const handleCancelForm = () => {
    setShowCreateForm(false);
    setEditingAppointment(null);
    resetForm();
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'SCHEDULED':
        return styles.statusScheduled;
      case 'CONFIRMED':
        return styles.statusConfirmed;
      case 'COMPLETED':
        return styles.statusCompleted;
      case 'CANCELLED':
        return styles.statusCancelled;
      case 'NO_SHOW':
        return styles.statusNoShow;
      default:
        return styles.statusScheduled;
    }
  };

  const isAdmin = user?.is_superuser === true || user?.role === 'ADMIN';
  const canManage = isAdmin || user?.role === 'RECEPTIONIST' || user?.role === 'DOCTOR';
  const canViewOwn = user?.role === 'DOCTOR';

  // Load doctors when form is shown (only once, avoid infinite loops)
  useEffect(() => {
    if (
      showCreateForm &&
      (isAdmin || user?.role === 'RECEPTIONIST' || user?.role === 'DOCTOR') &&
      doctors.length === 0 &&
      !loadingDoctors
    ) {
      loadDoctors();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCreateForm, isAdmin, user?.role, doctors.length, loadingDoctors]);

  if (!canManage && !canViewOwn) {
    return (
      <div className={styles.appointmentsPage}>
        <BackToDashboard />
        <div className={styles.accessDenied}>
          <h2>Access Denied</h2>
          <p>You do not have permission to view appointments.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.appointmentsPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Appointments</h1>
        {canManage && !showCreateForm && (
          <button
            className={styles.createButton}
            onClick={() => setShowCreateForm(true)}
          >
            + New Appointment
          </button>
        )}
      </header>

      {/* Filters and View Mode */}
      {!showCreateForm && (
        <div className={styles.filtersSection}>
          <div className={styles.viewModeButtons}>
            <button
              className={viewMode === 'all' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('all')}
            >
              All
            </button>
            <button
              className={viewMode === 'upcoming' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('upcoming')}
            >
              Upcoming
            </button>
            <button
              className={viewMode === 'today' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setViewMode('today')}
            >
              Today
            </button>
          </div>

          <div className={styles.statusFilters}>
            <button
              className={!filters.status ? styles.activeButton : styles.inactiveButton}
              onClick={() => setFilters({ ...filters, status: undefined })}
            >
              All Status
            </button>
            <button
              className={filters.status === 'SCHEDULED' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setFilters({ ...filters, status: 'SCHEDULED' })}
            >
              Scheduled
            </button>
            <button
              className={filters.status === 'CONFIRMED' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setFilters({ ...filters, status: 'CONFIRMED' })}
            >
              Confirmed
            </button>
            <button
              className={filters.status === 'COMPLETED' ? styles.activeButton : styles.inactiveButton}
              onClick={() => setFilters({ ...filters, status: 'COMPLETED' })}
            >
              Completed
            </button>
          </div>

          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by patient name or ID..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setFilters({ ...filters, search: e.target.value || undefined });
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  loadAppointments();
                }
              }}
            />
            <button onClick={loadAppointments}>Search</button>
          </div>
        </div>
      )}

      {/* Create/Edit Form */}
      {showCreateForm && (
        <div className={styles.formContainer}>
          <h2>{editingAppointment ? 'Edit Appointment' : 'Create New Appointment'}</h2>
          
          <div className={styles.formGroup}>
            <label>Patient *</label>
            <div className={styles.patientSearch}>
              <input
                type="text"
                placeholder="Search for patient by name, ID, phone, or national ID..."
                value={patientSearchQuery}
                onChange={(e) => {
                  const value = e.target.value;
                  setPatientSearchQuery(value);
                  
                  // Clear existing timeout
                  if (searchTimeoutRef.current) {
                    clearTimeout(searchTimeoutRef.current);
                  }
                  
                  // If empty, show initial list
                  if (!value.trim()) {
                    loadInitialPatients();
                    return;
                  }
                  
                  // Debounce search - only search if user stops typing for 300ms
                  searchTimeoutRef.current = setTimeout(() => {
                    handlePatientSearch(value);
                  }, 300);
                }}
                onFocus={() => {
                  // Show initial list when input is focused
                  if (!patientSearchQuery.trim() && patientSearchResults.length === 0) {
                    loadInitialPatients();
                  }
                }}
              />
              {patientSearchResults.length > 0 && !selectedPatient && (
                <div className={styles.searchResults}>
                  <div className={styles.searchResultsHeader}>
                    {patientSearchQuery.trim() ? 'Search Results' : 'Recent Patients'}
                  </div>
                  {patientSearchResults.map((patient) => (
                    <div
                      key={patient.id}
                      className={styles.searchResultItem}
                      onClick={() => handleSelectPatient(patient)}
                    >
                      <div>
                        <strong>{patient.full_name || `${patient.first_name} ${patient.last_name}`}</strong>
                        {patient.patient_id && <span className={styles.patientId}>ID: {patient.patient_id}</span>}
                      </div>
                      {patient.phone && <div className={styles.patientMeta}>📞 {patient.phone}</div>}
                    </div>
                  ))}
                </div>
              )}
              {selectedPatient && (
                <div className={styles.selectedPatient}>
                  <span>Selected: <strong>{selectedPatient.full_name || `${selectedPatient.first_name} ${selectedPatient.last_name}`}</strong> ({selectedPatient.patient_id})</span>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPatient(null);
                      setFormData({ ...formData, patient: 0 });
                      setPatientSearchQuery('');
                    }}
                  >
                    Change
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Doctor *</label>
            {loadingDoctors ? (
              <p>Loading doctors...</p>
            ) : (
              <select
                value={formData.doctor}
                onChange={(e) => setFormData({ ...formData, doctor: parseInt(e.target.value) })}
                required
                disabled={!!editingAppointment || (user?.role === 'DOCTOR' && !editingAppointment)}
              >
                <option value={0}>Select a doctor...</option>
                {doctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    Dr. {doctor.first_name} {doctor.last_name}
                    {user?.role === 'DOCTOR' && doctor.id === user.id ? ' (You)' : ''}
                  </option>
                ))}
              </select>
            )}
            {user?.role === 'DOCTOR' && !editingAppointment && (
              <p className={styles.helpText}>You are automatically selected as the doctor for this appointment.</p>
            )}
          </div>

          <div className={styles.formGroup}>
            <label>Appointment Date & Time *</label>
            <input
              type="datetime-local"
              value={formData.appointment_date}
              onChange={(e) => setFormData({ ...formData, appointment_date: e.target.value })}
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label>Duration (minutes)</label>
            <input
              type="number"
              min="15"
              step="15"
              value={formData.duration_minutes}
              onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) || 30 })}
            />
          </div>

          <div className={styles.formGroup}>
            <label>Reason</label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              rows={3}
              placeholder="Reason for appointment or chief complaint"
            />
          </div>

          <div className={styles.formGroup}>
            <label>Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              placeholder="Additional notes"
            />
          </div>

          <div className={styles.formActions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={handleCancelForm}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="button"
              className={styles.saveButton}
              onClick={editingAppointment ? handleUpdate : handleCreate}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : editingAppointment ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      )}

      {/* Appointments List */}
      {!showCreateForm && (
        <div className={styles.appointmentsList}>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : appointments.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No appointments found</p>
            </div>
          ) : (
            appointments.map((appointment) => (
              <div key={appointment.id} className={styles.appointmentCard}>
                <div className={styles.appointmentHeader}>
                  <div>
                    <h3>
                      {appointment.patient_name || 'Unknown Patient'}
                      {appointment.patient_id && ` (${appointment.patient_id})`}
                    </h3>
                    <p className={styles.appointmentDate}>
                      {formatDateTime(appointment.appointment_date)}
                    </p>
                  </div>
                  <div className={styles.appointmentBadges}>
                    <span className={`${styles.statusBadge} ${getStatusBadgeClass(appointment.status)}`}>
                      {appointment.status}
                    </span>
                  </div>
                </div>

                <div className={styles.appointmentDetails}>
                  <p><strong>Doctor:</strong> {appointment.doctor_name || 'Unknown'}</p>
                  <p><strong>Duration:</strong> {appointment.duration_minutes} minutes</p>
                  {appointment.reason && (
                    <p><strong>Reason:</strong> {appointment.reason}</p>
                  )}
                  {appointment.notes && (
                    <p><strong>Notes:</strong> {appointment.notes}</p>
                  )}
                  {appointment.visit && (
                    <p>
                      <strong>Visit:</strong>{' '}
                      <button
                        className={styles.linkButton}
                        onClick={() => navigate(`/visits/${appointment.visit}`)}
                      >
                        View Visit #{appointment.visit}
                      </button>
                    </p>
                  )}
                </div>

                <div className={styles.appointmentActions}>
                  {canManage && (
                    <>
                      {appointment.status === 'SCHEDULED' && (
                        <button
                          className={styles.confirmButton}
                          onClick={() => handleConfirm(appointment.id)}
                        >
                          Confirm
                        </button>
                      )}
                      {appointment.status === 'CONFIRMED' && (
                        <button
                          className={styles.completeButton}
                          onClick={() => handleComplete(appointment.id)}
                        >
                          Complete
                        </button>
                      )}
                      {appointment.status !== 'CANCELLED' && (
                        <>
                          <button
                            className={styles.editButton}
                            onClick={() => handleEdit(appointment)}
                          >
                            Edit
                          </button>
                          <button
                            className={styles.cancelButton}
                            onClick={() => handleCancel(appointment.id)}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </>
                  )}
                  {/* Show action buttons for doctors viewing their own appointments if they don't have manage permissions */}
                  {canViewOwn && !canManage && (
                    <>
                      {appointment.status === 'SCHEDULED' && (
                        <button
                          className={styles.confirmButton}
                          onClick={() => handleConfirm(appointment.id)}
                        >
                          Confirm
                        </button>
                      )}
                      {appointment.status === 'CONFIRMED' && (
                        <button
                          className={styles.completeButton}
                          onClick={() => handleComplete(appointment.id)}
                        >
                          Complete
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
