/**
 * Patient Management Page
 * 
 * For searching, viewing, and managing patient records.
 * Per EMR Rules: Receptionist can register/update, all roles can view.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchPatients, searchPatients, getPatient, updatePatient, archivePatient } from '../api/patient';
import { Patient, PatientCreateData } from '../types/patient';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/PatientManagement.module.css';

export default function PatientManagementPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const [editForm, setEditForm] = useState<Partial<PatientCreateData>>({});
  const [isArchiving, setIsArchiving] = useState(false);

  const loadRecentPatients = useCallback(async () => {
    try {
      setLoading(true);
      const allPatients = await fetchPatients();
      setPatients(allPatients);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load patients';
      showError(errorMessage);
      setPatients([]);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    loadRecentPatients();
  }, [loadRecentPatients]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadRecentPatients();
      return;
    }

    try {
      setIsSearching(true);
      const results = await searchPatients(searchQuery);
      setPatients(results);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Search failed';
      showError(errorMessage);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectPatient = async (patientId: number) => {
    try {
      const patient = await getPatient(patientId);
      setSelectedPatient(patient);
      setShowEditForm(false);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load patient';
      showError(errorMessage);
    }
  };

  const handleEdit = () => {
    if (!selectedPatient) return;
    setEditForm({
      first_name: selectedPatient.first_name,
      last_name: selectedPatient.last_name,
      middle_name: selectedPatient.middle_name || '',
      date_of_birth: selectedPatient.date_of_birth || '',
      gender: selectedPatient.gender,
      phone: selectedPatient.phone || '',
      email: selectedPatient.email || '',
      address: selectedPatient.address || '',
      national_id: selectedPatient.national_id || '',
      blood_group: selectedPatient.blood_group || undefined,
      allergies: selectedPatient.allergies || '',
      medical_history: selectedPatient.medical_history || '',
    });
    setShowEditForm(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedPatient) return;

    try {
      setIsSaving(true);
      await updatePatient(selectedPatient.id, editForm);
      showSuccess('Patient updated successfully');
      await handleSelectPatient(selectedPatient.id); // Reload patient
      setShowEditForm(false);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update patient';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateVisit = () => {
    if (selectedPatient) {
      navigate(`/visits/new?patient=${selectedPatient.id}`);
    }
  };

  const handleArchivePatient = async () => {
    if (!selectedPatient) return;
    if (!window.confirm(`Archive patient ${selectedPatient.first_name} ${selectedPatient.last_name}? This will soft-delete the record (compliance: no hard delete).`)) {
      return;
    }
    try {
      setIsArchiving(true);
      await archivePatient(selectedPatient.id);
      showSuccess('Patient record archived successfully.');
      setSelectedPatient(null);
      loadRecentPatients();
      handleSearch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to archive patient';
      showError(msg);
    } finally {
      setIsArchiving(false);
    }
  };

  const canEdit = user?.role === 'RECEPTIONIST' || user?.role === 'ADMIN';
  const canArchive = user?.role === 'RECEPTIONIST' || user?.role === 'ADMIN' || user?.is_superuser;

  return (
    <div className={styles.patientManagementPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Patient Management</h1>
        <p>Search and manage patient records</p>
      </header>

      <div className={styles.content}>
        <div className={styles.searchPanel}>
          <div className={styles.searchBox}>
            <input
              type="text"
              placeholder="Search by name, phone, patient ID, or national ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className={styles.searchButton}
            >
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className={styles.patientsList}>
            {loading ? (
              <LoadingSkeleton count={5} />
            ) : patients.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No patients found</p>
                {!loading && (
                  <p className={styles.emptyStateHint}>
                    {searchQuery.trim() 
                      ? 'Try a different search term' 
                      : 'Register a new patient to get started'}
                  </p>
                )}
              </div>
            ) : (
              <div className={styles.patientsGrid}>
                {patients.map((patient) => (
                  <div
                    key={patient.id}
                    className={`${styles.patientCard} ${selectedPatient?.id === patient.id ? styles.selected : ''}`}
                    onClick={() => handleSelectPatient(patient.id)}
                  >
                    <div className={styles.patientCardHeader}>
                      <h3>{patient.full_name || `${patient.first_name} ${patient.last_name}`}</h3>
                      <span className={styles.patientId}>ID: {patient.patient_id}</span>
                    </div>
                    <div className={styles.patientCardDetails}>
                      {patient.phone && <p>📞 {patient.phone}</p>}
                      {patient.date_of_birth && (
                        <p>🎂 {new Date(patient.date_of_birth).toLocaleDateString()}</p>
                      )}
                      {patient.gender && <p>👤 {patient.gender}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className={styles.detailsPanel}>
          {selectedPatient ? (
            <>
              <div className={styles.panelHeader}>
                <h2>Patient Details</h2>
                <div className={styles.panelActions}>
                  {canEdit && (
                    <button
                      className={styles.editButton}
                      onClick={handleEdit}
                      disabled={showEditForm}
                    >
                      {showEditForm ? 'Editing...' : 'Edit'}
                    </button>
                  )}
                  <button
                    className={styles.createVisitButton}
                    onClick={handleCreateVisit}
                  >
                    Create Visit
                  </button>
                  {canArchive && (
                    <button
                      className={styles.archiveButton}
                      onClick={handleArchivePatient}
                      disabled={isArchiving}
                    >
                      {isArchiving ? 'Archiving...' : 'Archive'}
                    </button>
                  )}
                </div>
              </div>

              {showEditForm ? (
                <div className={styles.editForm}>
                  <h3>Edit Patient</h3>
                  <div className={styles.formGrid}>
                    <div className={styles.formGroup}>
                      <label>First Name *</label>
                      <input
                        type="text"
                        value={editForm.first_name || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, first_name: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Last Name *</label>
                      <input
                        type="text"
                        value={editForm.last_name || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, last_name: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Middle Name</label>
                      <input
                        type="text"
                        value={editForm.middle_name || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, middle_name: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Date of Birth</label>
                      <input
                        type="date"
                        value={editForm.date_of_birth || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, date_of_birth: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Gender</label>
                      <select
                        value={editForm.gender || ''}
                        onChange={(e) => {
                          const value = e.target.value;
                          setEditForm(prev => ({ 
                            ...prev, 
                            gender: value ? (value as 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY') : undefined
                          }));
                        }}
                      >
                        <option value="">Select...</option>
                        <option value="MALE">Male</option>
                        <option value="FEMALE">Female</option>
                        <option value="OTHER">Other</option>
                        <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
                      </select>
                    </div>
                    <div className={styles.formGroup}>
                      <label>Phone</label>
                      <input
                        type="tel"
                        value={editForm.phone || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, phone: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Email</label>
                      <input
                        type="email"
                        value={editForm.email || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, email: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>National ID</label>
                      <input
                        type="text"
                        value={editForm.national_id || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, national_id: e.target.value }))}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Blood Group</label>
                      <select
                        value={editForm.blood_group || ''}
                        onChange={(e) => {
                          const value = e.target.value;
                          setEditForm(prev => ({ 
                            ...prev, 
                            blood_group: value ? (value as 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-') : undefined
                          }));
                        }}
                      >
                        <option value="">Select...</option>
                        <option value="A+">A+</option>
                        <option value="A-">A-</option>
                        <option value="B+">B+</option>
                        <option value="B-">B-</option>
                        <option value="AB+">AB+</option>
                        <option value="AB-">AB-</option>
                        <option value="O+">O+</option>
                        <option value="O-">O-</option>
                      </select>
                    </div>
                    <div className={styles.formGroupFull}>
                      <label>Address</label>
                      <textarea
                        value={editForm.address || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, address: e.target.value }))}
                        rows={3}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Emergency Contact Name</label>
                      <input
                        type="text"
                        value={editForm.emergency_contact_name || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, emergency_contact_name: e.target.value }))}
                        placeholder="Full name of emergency contact"
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Emergency Contact Phone</label>
                      <input
                        type="tel"
                        value={editForm.emergency_contact_phone || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, emergency_contact_phone: e.target.value }))}
                        placeholder="Phone number"
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Emergency Contact Relationship</label>
                      <input
                        type="text"
                        value={editForm.emergency_contact_relationship || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, emergency_contact_relationship: e.target.value }))}
                        placeholder="e.g., Spouse, Parent, Sibling, Friend"
                      />
                    </div>
                    <div className={styles.formGroupFull}>
                      <label>Allergies</label>
                      <textarea
                        value={editForm.allergies || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, allergies: e.target.value }))}
                        rows={2}
                        placeholder="List known allergies"
                      />
                    </div>
                    <div className={styles.formGroupFull}>
                      <label>Medical History</label>
                      <textarea
                        value={editForm.medical_history || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, medical_history: e.target.value }))}
                        rows={4}
                        placeholder="Medical history summary"
                      />
                    </div>
                  </div>
                  <div className={styles.formActions}>
                    <button
                      className={styles.cancelButton}
                      onClick={() => {
                        setShowEditForm(false);
                        setEditForm({});
                      }}
                      disabled={isSaving}
                    >
                      Cancel
                    </button>
                    <button
                      className={styles.saveButton}
                      onClick={handleSaveEdit}
                      disabled={isSaving || !editForm.first_name || !editForm.last_name}
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className={styles.patientDetails}>
                  <div className={styles.detailSection}>
                    <h3>Personal Information</h3>
                    <div className={styles.detailGrid}>
                      <div className={styles.detailItem}>
                        <label>Patient ID:</label>
                        <span>{selectedPatient.patient_id}</span>
                      </div>
                      <div className={styles.detailItem}>
                        <label>Full Name:</label>
                        <span>{selectedPatient.full_name || `${selectedPatient.first_name} ${selectedPatient.last_name}`}</span>
                      </div>
                      {selectedPatient.middle_name && (
                        <div className={styles.detailItem}>
                          <label>Middle Name:</label>
                          <span>{selectedPatient.middle_name}</span>
                        </div>
                      )}
                      {selectedPatient.date_of_birth && (
                        <div className={styles.detailItem}>
                          <label>Date of Birth:</label>
                          <span>{new Date(selectedPatient.date_of_birth).toLocaleDateString()}</span>
                        </div>
                      )}
                      {selectedPatient.age && (
                        <div className={styles.detailItem}>
                          <label>Age:</label>
                          <span>{selectedPatient.age} years</span>
                        </div>
                      )}
                      {selectedPatient.gender && (
                        <div className={styles.detailItem}>
                          <label>Gender:</label>
                          <span>{selectedPatient.gender}</span>
                        </div>
                      )}
                      {selectedPatient.phone && (
                        <div className={styles.detailItem}>
                          <label>Phone:</label>
                          <span>{selectedPatient.phone}</span>
                        </div>
                      )}
                      {selectedPatient.email && (
                        <div className={styles.detailItem}>
                          <label>Email:</label>
                          <span>{selectedPatient.email}</span>
                        </div>
                      )}
                      {selectedPatient.national_id && (
                        <div className={styles.detailItem}>
                          <label>National ID:</label>
                          <span>{selectedPatient.national_id}</span>
                        </div>
                      )}
                      {selectedPatient.address && (
                        <div className={styles.detailItemFull}>
                          <label>Address:</label>
                          <span>{selectedPatient.address}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {(selectedPatient.emergency_contact_name || selectedPatient.emergency_contact_phone || selectedPatient.emergency_contact_relationship) && (
                    <div className={styles.detailSection}>
                      <h3>Emergency Contact</h3>
                      <div className={styles.detailGrid}>
                        {selectedPatient.emergency_contact_name && (
                          <div className={styles.detailItem}>
                            <label>Contact Name:</label>
                            <span>{selectedPatient.emergency_contact_name}</span>
                          </div>
                        )}
                        {selectedPatient.emergency_contact_phone && (
                          <div className={styles.detailItem}>
                            <label>Contact Phone:</label>
                            <span>{selectedPatient.emergency_contact_phone}</span>
                          </div>
                        )}
                        {selectedPatient.emergency_contact_relationship && (
                          <div className={styles.detailItem}>
                            <label>Relationship:</label>
                            <span>{selectedPatient.emergency_contact_relationship}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {selectedPatient.blood_group && (
                    <div className={styles.detailSection}>
                      <h3>Medical Information</h3>
                      <div className={styles.detailGrid}>
                        <div className={styles.detailItem}>
                          <label>Blood Group:</label>
                          <span>{selectedPatient.blood_group}</span>
                        </div>
                        {selectedPatient.allergies && (
                          <div className={styles.detailItemFull}>
                            <label>Allergies:</label>
                            <span>{selectedPatient.allergies}</span>
                          </div>
                        )}
                        {selectedPatient.medical_history && (
                          <div className={styles.detailItemFull}>
                            <label>Medical History:</label>
                            <span>{selectedPatient.medical_history}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className={styles.detailSection}>
                    <h3>Record Information</h3>
                    <div className={styles.detailGrid}>
                      <div className={styles.detailItem}>
                        <label>Created:</label>
                        <span>{new Date(selectedPatient.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className={styles.detailItem}>
                        <label>Last Updated:</label>
                        <span>{new Date(selectedPatient.updated_at).toLocaleDateString()}</span>
                      </div>
                      <div className={styles.detailItem}>
                        <label>Status:</label>
                        <span className={selectedPatient.is_active ? styles.statusActive : styles.statusInactive}>
                          {selectedPatient.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className={styles.detailSection}>
                    <h3>Actions</h3>
                    <div className={styles.actionButtons}>
                      <button
                        className={styles.historyButton}
                        onClick={() => navigate(`/patients/${selectedPatient.id}/history`)}
                      >
                        View Medical History
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className={styles.emptyState}>
              <p>Select a patient to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
