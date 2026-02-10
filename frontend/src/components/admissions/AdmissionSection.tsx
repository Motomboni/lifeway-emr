/**
 * Admission Section Component
 * 
 * Component for viewing and managing patient admission to wards/beds.
 * Doctor-only: Create, update, discharge, and transfer admissions.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import {
  fetchAdmission,
  createAdmission,
  updateAdmission,
  dischargeAdmission,
  transferAdmission,
  fetchWards,
  fetchWardAvailableBeds,
  Ward,
  Bed,
  Admission,
  AdmissionCreateData,
  AdmissionTransferData,
} from '../../api/admissions';
import styles from '../../styles/Admission.module.css';
import { extractPaginatedResults } from '../../utils/pagination';
import { logger } from '../../utils/logger';

interface AdmissionSectionProps {
  visitId: number;
  visitStatus: string;
  patientName: string;
}

interface ParsedAdmissionNotes {
  clinical_data?: {
    history_of_present_illness?: string;
    past_medical_history?: string;
    allergies?: string;
    current_medications?: string;
    vital_signs_at_admission?: string;
    physical_examination?: string;
    provisional_diagnosis?: string;
    plan_of_care?: string;
  };
  additional_notes?: string;
  formatted_text?: string;
}

export default function AdmissionSection({
  visitId,
  visitStatus,
  patientName,
}: AdmissionSectionProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showTransferForm, setShowTransferForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [wards, setWards] = useState<Ward[]>([]);
  const [availableBeds, setAvailableBeds] = useState<Bed[]>([]);
  const [loadingWards, setLoadingWards] = useState(false);
  const [selectedWardId, setSelectedWardId] = useState<number | ''>('');
  const [parsedNotes, setParsedNotes] = useState<ParsedAdmissionNotes | null>(null);
  
  const [formData, setFormData] = useState<AdmissionCreateData>({
    visit: visitId,
    ward: 0,
    bed: 0,
    admission_type: 'ELECTIVE',
    admission_source: 'OUTPATIENT',
    admission_date: new Date().toISOString().slice(0, 16),
    chief_complaint: '',
    admission_notes: '',
    history_of_present_illness: '',
    past_medical_history: '',
    allergies: '',
    current_medications: '',
    vital_signs_at_admission: '',
    physical_examination: '',
    provisional_diagnosis: '',
    plan_of_care: '',
  });
  
  const [transferData, setTransferData] = useState<AdmissionTransferData>({
    new_ward_id: 0,
    new_bed_id: 0,
    transfer_notes: '',
  });

  const isDoctor = user?.role === 'DOCTOR';
  const canAdmit = isDoctor && visitStatus === 'OPEN' && !admission;
  const canDischarge = isDoctor && admission && admission.admission_status === 'ADMITTED';
  const canTransfer = isDoctor && admission && admission.admission_status === 'ADMITTED';

  useEffect(() => {
    loadAdmission();
    loadWards();
  }, [visitId]);

  useEffect(() => {
    if (selectedWardId) {
      loadAvailableBeds(selectedWardId);
    } else {
      setAvailableBeds([]);
    }
  }, [selectedWardId]);

  const loadAdmission = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true);
      }
      const data = await fetchAdmission(visitId);
      setAdmission(data);
      
      // Parse admission notes if available
      if (data?.admission_notes) {
        try {
          const parsed = JSON.parse(data.admission_notes);
          setParsedNotes(parsed);
        } catch (e) {
          // If not JSON, treat as plain text
          setParsedNotes({ additional_notes: data.admission_notes });
        }
      } else {
        setParsedNotes(null);
      }
      } catch (error: any) {
        logger.error('Failed to load admission:', error);
        if (error.status !== 404) {
          showError('Failed to load admission information.');
        }
        // Explicitly set to null if 404
        setAdmission(null);
        setParsedNotes(null);
      } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  const loadWards = async () => {
    try {
      setLoadingWards(true);
      const data = await fetchWards(true); // Only active wards
      const wardsArray = extractPaginatedResults(data);
      setWards(wardsArray);
    } catch (error: any) {
      logger.error('Failed to load wards:', error);
      showError('Failed to load wards.');
      setWards([]); // Ensure wards is always an array
    } finally {
      setLoadingWards(false);
    }
  };

  const loadAvailableBeds = async (wardId: number) => {
    try {
      const beds = await fetchWardAvailableBeds(wardId);
      const bedsArray = extractPaginatedResults(beds);
      setAvailableBeds(bedsArray);
    } catch (error: any) {
      logger.error('Failed to load available beds:', error);
      showError('Failed to load available beds.');
      setAvailableBeds([]); // Ensure beds is always an array
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.ward || !formData.bed) {
      showError('Please select a ward and bed.');
      return;
    }
    
    if (!formData.chief_complaint.trim()) {
      showError('Chief complaint is required.');
      return;
    }

    try {
      setSaving(true);
      
      // Format clinical data into structured admission notes
      const clinicalData: any = {};
      if (formData.history_of_present_illness?.trim()) {
        clinicalData.history_of_present_illness = formData.history_of_present_illness.trim();
      }
      if (formData.past_medical_history?.trim()) {
        clinicalData.past_medical_history = formData.past_medical_history.trim();
      }
      if (formData.allergies?.trim()) {
        clinicalData.allergies = formData.allergies.trim();
      }
      if (formData.current_medications?.trim()) {
        clinicalData.current_medications = formData.current_medications.trim();
      }
      if (formData.vital_signs_at_admission?.trim()) {
        clinicalData.vital_signs_at_admission = formData.vital_signs_at_admission.trim();
      }
      if (formData.physical_examination?.trim()) {
        clinicalData.physical_examination = formData.physical_examination.trim();
      }
      if (formData.provisional_diagnosis?.trim()) {
        clinicalData.provisional_diagnosis = formData.provisional_diagnosis.trim();
      }
      if (formData.plan_of_care?.trim()) {
        clinicalData.plan_of_care = formData.plan_of_care.trim();
      }
      
      // Combine structured clinical data with additional notes
      const admissionNotesParts: string[] = [];
      
      // Format clinical data as readable text
      if (Object.keys(clinicalData).length > 0) {
        admissionNotesParts.push('=== CLINICAL INFORMATION ===');
        if (clinicalData.history_of_present_illness) {
          admissionNotesParts.push(`\nHistory of Present Illness:\n${clinicalData.history_of_present_illness}`);
        }
        if (clinicalData.past_medical_history) {
          admissionNotesParts.push(`\nPast Medical History:\n${clinicalData.past_medical_history}`);
        }
        if (clinicalData.allergies) {
          admissionNotesParts.push(`\nAllergies:\n${clinicalData.allergies}`);
        }
        if (clinicalData.current_medications) {
          admissionNotesParts.push(`\nCurrent Medications:\n${clinicalData.current_medications}`);
        }
        if (clinicalData.vital_signs_at_admission) {
          admissionNotesParts.push(`\nVital Signs at Admission:\n${clinicalData.vital_signs_at_admission}`);
        }
        if (clinicalData.physical_examination) {
          admissionNotesParts.push(`\nPhysical Examination:\n${clinicalData.physical_examination}`);
        }
        if (clinicalData.provisional_diagnosis) {
          admissionNotesParts.push(`\nProvisional Diagnosis:\n${clinicalData.provisional_diagnosis}`);
        }
        if (clinicalData.plan_of_care) {
          admissionNotesParts.push(`\nPlan of Care:\n${clinicalData.plan_of_care}`);
        }
        admissionNotesParts.push('\n=== END CLINICAL INFORMATION ===');
      }
      
      // Add additional notes if provided
      if (formData.admission_notes?.trim()) {
        admissionNotesParts.push(`\n\nAdditional Notes:\n${formData.admission_notes.trim()}`);
      }
      
      // Store structured JSON data in admission_notes for programmatic access
      const structuredNotes = {
        clinical_data: clinicalData,
        additional_notes: formData.admission_notes?.trim() || '',
        formatted_text: admissionNotesParts.join('\n')
      };
      
      // Prepare submission data - only include fields accepted by backend serializer
      const submissionData: AdmissionCreateData = {
        visit: formData.visit,
        ward: formData.ward,
        bed: formData.bed,
        admission_type: formData.admission_type,
        admission_source: formData.admission_source,
        admission_date: formData.admission_date,
        chief_complaint: formData.chief_complaint,
        admission_notes: JSON.stringify(structuredNotes)
      };
      
      const newAdmission = await createAdmission(visitId, submissionData);
      logger.debug('Admission created:', newAdmission);
      // Reload admission to get all computed fields (ward_name, bed_number, etc.)
      // Use showLoading=false to avoid hiding the admission with loading state
      await loadAdmission(false);
      setShowForm(false);
      showSuccess('Patient admitted successfully!');
      setFormData({
        visit: visitId,
        ward: 0,
        bed: 0,
        admission_type: 'ELECTIVE',
        admission_source: 'OUTPATIENT',
        admission_date: new Date().toISOString().slice(0, 16),
        chief_complaint: '',
        admission_notes: '',
        history_of_present_illness: '',
        past_medical_history: '',
        allergies: '',
        current_medications: '',
        vital_signs_at_admission: '',
        physical_examination: '',
        provisional_diagnosis: '',
        plan_of_care: '',
      });
      setSelectedWardId('');
    } catch (error: any) {
      logger.error('Failed to admit patient:', error);
      
      // Check if error indicates admission already exists
      const errorMessage = error.message || '';
      const errorData = error.data || [];
      const hasAdmissionError = 
        errorMessage.includes('already has an admission') ||
        errorData.some((msg: string) => msg.includes('already has an admission'));
      
      if (hasAdmissionError) {
        // Reload admission data to show the existing admission
        await loadAdmission();
        setShowForm(false);
        showError('This visit already has an admission. The admission details are now displayed.');
      } else {
        showError(errorMessage || 'Failed to admit patient.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDischarge = async () => {
    if (!admission) return;
    
    if (!window.confirm(`Are you sure you want to discharge ${patientName}?`)) {
      return;
    }

    try {
      setSaving(true);
      const updated = await dischargeAdmission(visitId, admission.id);
      setAdmission(updated);
      showSuccess('Patient discharged successfully!');
    } catch (error: any) {
      logger.error('Failed to discharge patient:', error);
      showError(error.message || 'Failed to discharge patient.');
    } finally {
      setSaving(false);
    }
  };

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!transferData.new_ward_id || !transferData.new_bed_id) {
      showError('Please select a ward and bed for transfer.');
      return;
    }

    if (!admission) return;

    try {
      setSaving(true);
      const newAdmission = await transferAdmission(visitId, admission.id, transferData);
      setAdmission(newAdmission);
      setShowTransferForm(false);
      showSuccess('Patient transferred successfully!');
      setTransferData({
        new_ward_id: 0,
        new_bed_id: 0,
        transfer_notes: '',
      });
      setSelectedWardId('');
    } catch (error: any) {
      logger.error('Failed to transfer patient:', error);
      showError(error.message || 'Failed to transfer patient.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Admission</h3>
        <p>Loading admission information...</p>
      </div>
    );
  }

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Admission</h3>
        {canAdmit && (
          <button
            onClick={async () => {
              // Reload admission data before showing form to check for race conditions
              try {
                const existingAdmission = await fetchAdmission(visitId);
                if (existingAdmission) {
                  setAdmission(existingAdmission);
                  showError('This visit already has an admission.');
                } else {
                  setShowForm(true);
                }
              } catch (error: any) {
                // If error is 404, no admission exists, so show form
                if (error.status === 404) {
                  setShowForm(true);
                } else {
                  logger.error('Failed to check admission:', error);
                  showError('Failed to check admission status. Please try again.');
                }
              }
            }}
            className={styles.actionButton}
          >
            + Admit Patient
          </button>
        )}
      </div>

      {admission ? (
        <div className={styles.admissionCard}>
          <div className={styles.admissionHeader}>
            <div>
              <span className={styles.statusBadge}>
                {admission.admission_status}
              </span>
              <span className={styles.wardBedInfo}>
                {admission.ward_name} - Bed {admission.bed_number}
              </span>
            </div>
            <div className={styles.admissionActions}>
              {canTransfer && (
                <button
                  onClick={() => setShowTransferForm(true)}
                  className={styles.transferButton}
                >
                  Transfer
                </button>
              )}
              {canDischarge && (
                <button
                  onClick={handleDischarge}
                  className={styles.dischargeButton}
                  disabled={saving}
                >
                  {saving ? 'Discharging...' : 'Discharge'}
                </button>
              )}
            </div>
          </div>

          <div className={styles.admissionDetails}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Patient Name:</span>
              <span>{admission.patient_name || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Patient ID:</span>
              <span>{admission.patient_id || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Ward Name:</span>
              <span>{admission.ward_name || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Ward Code:</span>
              <span>{admission.ward_code || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Bed Number:</span>
              <span>{admission.bed_number || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Admission Type:</span>
              <span>{admission.admission_type || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Admission Source:</span>
              <span>{admission.admission_source || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Admission Status:</span>
              <span>{admission.admission_status || 'N/A'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Admission Date:</span>
              <span>{admission.admission_date ? new Date(admission.admission_date).toLocaleString() : 'N/A'}</span>
            </div>
            {admission.discharge_date && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Discharge Date:</span>
                <span>{new Date(admission.discharge_date).toLocaleString()}</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Length of Stay:</span>
              <span>{admission.length_of_stay_days !== undefined ? `${admission.length_of_stay_days} day(s)` : 'N/A'}</span>
            </div>
            {admission.transferred_from && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Transferred From:</span>
                <span>Admission #{admission.transferred_from}</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Chief Complaint:</span>
              <span>{admission.chief_complaint || 'N/A'}</span>
            </div>
            
            {/* Display structured admission notes */}
            {parsedNotes && parsedNotes.clinical_data && Object.keys(parsedNotes.clinical_data).length > 0 && (
              <>
                {parsedNotes.clinical_data.history_of_present_illness && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>History of Present Illness:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.history_of_present_illness}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.past_medical_history && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Past Medical History:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.past_medical_history}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.allergies && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Allergies:</span>
                    <span style={{ color: '#d32f2f', fontWeight: 'bold', whiteSpace: 'pre-wrap' }}>⚠️ {parsedNotes.clinical_data.allergies}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.current_medications && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Current Medications:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.current_medications}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.vital_signs_at_admission && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Vital Signs at Admission:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.vital_signs_at_admission}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.physical_examination && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Physical Examination:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.physical_examination}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.provisional_diagnosis && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Provisional Diagnosis:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.provisional_diagnosis}</span>
                  </div>
                )}
                {parsedNotes.clinical_data.plan_of_care && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Plan of Care:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.clinical_data.plan_of_care}</span>
                  </div>
                )}
                {parsedNotes.additional_notes && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Additional Notes:</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.additional_notes}</span>
                  </div>
                )}
              </>
            )}
            
            {/* Fallback: Display formatted text if available but no structured data */}
            {parsedNotes?.formatted_text && (!parsedNotes.clinical_data || Object.keys(parsedNotes.clinical_data).length === 0) && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Admission Notes:</span>
                <span style={{ whiteSpace: 'pre-wrap' }}>{parsedNotes.formatted_text}</span>
              </div>
            )}
            
            {/* Fallback: Display raw notes if not parsed */}
            {!parsedNotes && admission.admission_notes && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Admission Notes:</span>
                <span style={{ whiteSpace: 'pre-wrap' }}>{admission.admission_notes}</span>
              </div>
            )}
            
            {!admission.admission_notes && !parsedNotes && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Admission Notes:</span>
                <span>No notes provided</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Admitted By:</span>
              <span>{admission.admitting_doctor_name || 'N/A'}</span>
            </div>
            {admission.discharge_summary && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Discharge Summary:</span>
                <span>Available (ID: {admission.discharge_summary})</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Record Created:</span>
              <span>{admission.created_at ? new Date(admission.created_at).toLocaleString() : 'N/A'}</span>
            </div>
            {admission.updated_at && admission.updated_at !== admission.created_at && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Last Updated:</span>
                <span>{new Date(admission.updated_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.noAdmission}>
          <p>No admission record for this visit.</p>
          {!canAdmit && (
            <p className={styles.helpText}>
              {visitStatus !== 'OPEN' 
                ? 'Visit must be OPEN to admit patient.'
                : !isDoctor
                ? 'Only doctors can admit patients.'
                : ''}
            </p>
          )}
        </div>
      )}

      {/* Admission Form Modal */}
      {showForm && (
        <div className={styles.modalOverlay} onClick={() => setShowForm(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>Admit Patient</h3>
              <button
                onClick={() => setShowForm(false)}
                className={styles.closeButton}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit} className={styles.form}>
              <div className={styles.formGroup}>
                <label>Ward *</label>
                <select
                  value={selectedWardId}
                  onChange={(e) => {
                    const wardId = parseInt(e.target.value);
                    setSelectedWardId(wardId);
                    setFormData({ ...formData, ward: wardId, bed: 0 });
                  }}
                  required
                  disabled={loadingWards}
                >
                  <option value="">Select Ward</option>
                  {wards.map((ward) => (
                    <option key={ward.id} value={ward.id}>
                      {ward.name} ({ward.available_beds_count} beds available)
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Bed *</label>
                <select
                  value={formData.bed}
                  onChange={(e) => setFormData({ ...formData, bed: parseInt(e.target.value) })}
                  required
                  disabled={!selectedWardId || availableBeds.length === 0}
                >
                  <option value="0">Select Bed</option>
                  {availableBeds.map((bed) => (
                    <option key={bed.id} value={bed.id}>
                      {bed.bed_number} ({bed.bed_type})
                    </option>
                  ))}
                </select>
                {selectedWardId && availableBeds.length === 0 && (
                  <p className={styles.helpText}>No available beds in this ward.</p>
                )}
              </div>

              <div className={styles.formGroup}>
                <label>Admission Type *</label>
                <select
                  value={formData.admission_type}
                  onChange={(e) => setFormData({ ...formData, admission_type: e.target.value as any })}
                  required
                >
                  <option value="ELECTIVE">Elective</option>
                  <option value="EMERGENCY">Emergency</option>
                  <option value="OBSERVATION">Observation</option>
                  <option value="DAY_CARE">Day Care</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Admission Source *</label>
                <select
                  value={formData.admission_source}
                  onChange={(e) => setFormData({ ...formData, admission_source: e.target.value as any })}
                  required
                >
                  <option value="OUTPATIENT">Outpatient Department</option>
                  <option value="EMERGENCY">Emergency Department</option>
                  <option value="REFERRAL">Referred from Another Facility</option>
                  <option value="TRANSFER">Transfer from Another Ward</option>
                  <option value="DIRECT">Direct Admission</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Admission Date *</label>
                <input
                  type="datetime-local"
                  value={formData.admission_date}
                  onChange={(e) => setFormData({ ...formData, admission_date: e.target.value })}
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label>Chief Complaint *</label>
                <textarea
                  value={formData.chief_complaint}
                  onChange={(e) => setFormData({ ...formData, chief_complaint: e.target.value })}
                  required
                  rows={3}
                  placeholder="Primary reason for admission..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>History of Present Illness</label>
                <textarea
                  value={formData.history_of_present_illness}
                  onChange={(e) => setFormData({ ...formData, history_of_present_illness: e.target.value })}
                  rows={4}
                  placeholder="Detailed history of the current illness, onset, progression, associated symptoms..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Past Medical History</label>
                <textarea
                  value={formData.past_medical_history}
                  onChange={(e) => setFormData({ ...formData, past_medical_history: e.target.value })}
                  rows={3}
                  placeholder="Previous medical conditions, surgeries, hospitalizations..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Allergies</label>
                <textarea
                  value={formData.allergies}
                  onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
                  rows={2}
                  placeholder="Known allergies (drugs, food, environmental). Write 'None known' if no allergies."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Current Medications</label>
                <textarea
                  value={formData.current_medications}
                  onChange={(e) => setFormData({ ...formData, current_medications: e.target.value })}
                  rows={3}
                  placeholder="List all current medications with dosages and frequencies..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Vital Signs at Admission</label>
                <textarea
                  value={formData.vital_signs_at_admission}
                  onChange={(e) => setFormData({ ...formData, vital_signs_at_admission: e.target.value })}
                  rows={2}
                  placeholder="BP, HR, RR, Temperature, O2 Sat, Weight, Height..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Physical Examination Findings</label>
                <textarea
                  value={formData.physical_examination}
                  onChange={(e) => setFormData({ ...formData, physical_examination: e.target.value })}
                  rows={4}
                  placeholder="General appearance, cardiovascular, respiratory, abdominal, neurological, etc..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Provisional Diagnosis</label>
                <textarea
                  value={formData.provisional_diagnosis}
                  onChange={(e) => setFormData({ ...formData, provisional_diagnosis: e.target.value })}
                  rows={3}
                  placeholder="Working diagnosis or differential diagnoses..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Plan of Care</label>
                <textarea
                  value={formData.plan_of_care}
                  onChange={(e) => setFormData({ ...formData, plan_of_care: e.target.value })}
                  rows={4}
                  placeholder="Treatment plan, investigations ordered, medications prescribed, monitoring required..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Additional Admission Notes</label>
                <textarea
                  value={formData.admission_notes}
                  onChange={(e) => setFormData({ ...formData, admission_notes: e.target.value })}
                  rows={3}
                  placeholder="Any additional notes or special instructions..."
                />
              </div>

              <div className={styles.formActions}>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className={styles.cancelButton}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.submitButton}
                  disabled={saving}
                >
                  {saving ? 'Admitting...' : 'Admit Patient'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transfer Form Modal */}
      {showTransferForm && admission && (
        <div className={styles.modalOverlay} onClick={() => setShowTransferForm(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>Transfer Patient</h3>
              <button
                onClick={() => setShowTransferForm(false)}
                className={styles.closeButton}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleTransfer} className={styles.form}>
              <div className={styles.formGroup}>
                <label>Current Location</label>
                <input
                  type="text"
                  value={`${admission.ward_name} - Bed ${admission.bed_number}`}
                  disabled
                />
              </div>

              <div className={styles.formGroup}>
                <label>New Ward *</label>
                <select
                  value={selectedWardId}
                  onChange={(e) => {
                    const wardId = parseInt(e.target.value);
                    setSelectedWardId(wardId);
                    setTransferData({ ...transferData, new_ward_id: wardId, new_bed_id: 0 });
                  }}
                  required
                  disabled={loadingWards}
                >
                  <option value="">Select Ward</option>
                  {wards.filter(w => w.id !== admission.ward).map((ward) => (
                    <option key={ward.id} value={ward.id}>
                      {ward.name} ({ward.available_beds_count} beds available)
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>New Bed *</label>
                <select
                  value={transferData.new_bed_id}
                  onChange={(e) => setTransferData({ ...transferData, new_bed_id: parseInt(e.target.value) })}
                  required
                  disabled={!selectedWardId || availableBeds.length === 0}
                >
                  <option value="0">Select Bed</option>
                  {availableBeds.map((bed) => (
                    <option key={bed.id} value={bed.id}>
                      {bed.bed_number} ({bed.bed_type})
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Transfer Notes</label>
                <textarea
                  value={transferData.transfer_notes}
                  onChange={(e) => setTransferData({ ...transferData, transfer_notes: e.target.value })}
                  rows={3}
                  placeholder="Reason for transfer..."
                />
              </div>

              <div className={styles.formActions}>
                <button
                  type="button"
                  onClick={() => setShowTransferForm(false)}
                  className={styles.cancelButton}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.submitButton}
                  disabled={saving}
                >
                  {saving ? 'Transferring...' : 'Transfer Patient'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

