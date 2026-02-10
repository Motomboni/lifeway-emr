/**
 * Antenatal Record New Page
 * 
 * Page for creating new antenatal records.
 * Per EMR Rules: Only DOCTOR and ADMIN can create records.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import { searchPatients, getPatient } from '../api/patient';
import { createAntenatalRecord, AntenatalRecordCreateData } from '../api/antenatal';
import { Patient } from '../types/patient';
import { Parity, PregnancyType } from '../types/antenatal';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/AntenatalRecordForm.module.css';

const PARITY_OPTIONS: { value: Parity; label: string }[] = [
  { value: 'PRIMIGRAVIDA', label: 'Primigravida (First Pregnancy)' },
  { value: 'MULTIGRAVIDA', label: 'Multigravida (2-4 Pregnancies)' },
  { value: 'GRAND_MULTIGRAVIDA', label: 'Grand Multigravida (5+ Pregnancies)' },
];

const PREGNANCY_TYPE_OPTIONS: { value: PregnancyType; label: string }[] = [
  { value: 'SINGLETON', label: 'Singleton' },
  { value: 'TWINS', label: 'Twins' },
  { value: 'TRIPLETS', label: 'Triplets' },
  { value: 'MORE', label: 'More' },
];

export default function AntenatalRecordNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Form fields
  const [pregnancyNumber, setPregnancyNumber] = useState<number>(1);
  const [bookingDate, setBookingDate] = useState<string>('');
  const [lmp, setLmp] = useState<string>('');
  const [edd, setEdd] = useState<string>('');
  const [parity, setParity] = useState<Parity>('PRIMIGRAVIDA');
  const [gravida, setGravida] = useState<number>(1);
  const [para, setPara] = useState<number>(0);
  const [abortions, setAbortions] = useState<number>(0);
  const [livingChildren, setLivingChildren] = useState<number>(0);
  const [pastMedicalHistory, setPastMedicalHistory] = useState<string>('');
  const [pastSurgicalHistory, setPastSurgicalHistory] = useState<string>('');
  const [familyHistory, setFamilyHistory] = useState<string>('');
  const [allergies, setAllergies] = useState<string>('');
  const [previousCs, setPreviousCs] = useState<boolean>(false);
  const [previousCsCount, setPreviousCsCount] = useState<number>(0);
  const [previousComplications, setPreviousComplications] = useState<string>('');
  const [pregnancyType, setPregnancyType] = useState<PregnancyType>('SINGLETON');
  const [highRisk, setHighRisk] = useState<boolean>(false);
  const [riskFactors, setRiskFactors] = useState<string>('');
  const [clinicalNotes, setClinicalNotes] = useState<string>('');

  // Calculate EDD from LMP (280 days = 40 weeks)
  const calculateEDD = (lmpDate: string) => {
    if (!lmpDate) return '';
    const lmp = new Date(lmpDate);
    const edd = new Date(lmp);
    edd.setDate(edd.getDate() + 280);
    return edd.toISOString().split('T')[0];
  };

  const handleLmpChange = (value: string) => {
    setLmp(value);
    if (value) {
      const calculatedEdd = calculateEDD(value);
      setEdd(calculatedEdd);
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
    } catch (error) {
      showError('Failed to search patients');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectPatient = (patient: Patient) => {
    // Verify patient is female
    if (patient.gender !== 'FEMALE') {
      showError('Antenatal records can only be created for female patients');
      return;
    }
    setSelectedPatient(patient);
    setSearchResults([]);
    setSearchQuery('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedPatient) {
      showError('Please select a patient');
      return;
    }

    if (!bookingDate || !lmp || !edd) {
      showError('Booking date, LMP, and EDD are required');
      return;
    }

    try {
      setIsCreating(true);

      const riskFactorsArray = riskFactors
        ? riskFactors.split(',').map(f => f.trim()).filter(f => f)
        : [];

      const data: AntenatalRecordCreateData = {
        patient: selectedPatient.id,
        pregnancy_number: pregnancyNumber,
        booking_date: bookingDate,
        lmp: lmp,
        edd: edd,
        parity: parity,
        gravida: gravida,
        para: para,
        abortions: abortions,
        living_children: livingChildren,
        past_medical_history: pastMedicalHistory || undefined,
        past_surgical_history: pastSurgicalHistory || undefined,
        family_history: familyHistory || undefined,
        allergies: allergies || undefined,
        previous_cs: previousCs,
        previous_cs_count: previousCsCount,
        previous_complications: previousComplications || undefined,
        pregnancy_type: pregnancyType,
        high_risk: highRisk,
        risk_factors: riskFactorsArray.length > 0 ? riskFactorsArray : undefined,
        clinical_notes: clinicalNotes || undefined,
      };

      const record = await createAntenatalRecord(data);
      showSuccess('Antenatal record created successfully');
      navigate(`/antenatal/records/${record.id}`);
    } catch (error: any) {
      const errorMessage = error?.responseData?.detail || error?.message || 'Failed to create antenatal record';
      showError(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  if (user?.role !== 'DOCTOR' && user?.role !== 'ADMIN') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. Only Doctors and Administrators can create antenatal records.</p>
        <BackToDashboard />
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Create New Antenatal Record</h1>
      </header>

      <form onSubmit={handleSubmit} className={styles.form}>
        {/* Patient Selection */}
        <div className={styles.section}>
          <h2>Patient Selection</h2>
          {!selectedPatient ? (
            <div className={styles.patientSearch}>
              <div className={styles.searchBox}>
                <input
                  type="text"
                  placeholder="Search by name, MRN, or phone number..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleSearch();
                    }
                  }}
                />
                <button type="button" onClick={handleSearch} disabled={isSearching}>
                  {isSearching ? 'Searching...' : 'Search'}
                </button>
              </div>
              {searchResults.length > 0 && (
                <div className={styles.searchResults}>
                  {searchResults.map((patient) => (
                    <div
                      key={patient.id}
                      className={styles.patientCard}
                      onClick={() => handleSelectPatient(patient)}
                    >
                      <div>
                        <strong>{patient.first_name} {patient.last_name}</strong>
                        <p>ID: {patient.patient_id} | Gender: {patient.gender || 'N/A'} | DOB: {patient.date_of_birth ? new Date(patient.date_of_birth).toLocaleDateString() : 'N/A'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className={styles.selectedPatient}>
              <div className={styles.patientInfo}>
                <strong>{selectedPatient.first_name} {selectedPatient.last_name}</strong>
                <p>ID: {selectedPatient.patient_id} | Gender: {selectedPatient.gender || 'N/A'}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPatient(null)}
                className={styles.changeButton}
              >
                Change Patient
              </button>
            </div>
          )}
        </div>

        {/* Pregnancy Information */}
        <div className={styles.section}>
          <h2>Pregnancy Information</h2>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Pregnancy Number *</label>
              <input
                type="number"
                min="1"
                value={pregnancyNumber}
                onChange={(e) => setPregnancyNumber(parseInt(e.target.value) || 1)}
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label>Booking Date *</label>
              <input
                type="date"
                value={bookingDate}
                onChange={(e) => setBookingDate(e.target.value)}
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label>Last Menstrual Period (LMP) *</label>
              <input
                type="date"
                value={lmp}
                onChange={(e) => handleLmpChange(e.target.value)}
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label>Expected Due Date (EDD) *</label>
              <input
                type="date"
                value={edd}
                onChange={(e) => setEdd(e.target.value)}
                required
              />
              {lmp && (
                <small className={styles.helpText}>
                  Auto-calculated from LMP (280 days)
                </small>
              )}
            </div>
            <div className={styles.formGroup}>
              <label>Parity *</label>
              <select
                value={parity}
                onChange={(e) => setParity(e.target.value as Parity)}
                required
              >
                {PARITY_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.formGroup}>
              <label>Gravida</label>
              <input
                type="number"
                min="1"
                value={gravida}
                onChange={(e) => setGravida(parseInt(e.target.value) || 1)}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Para</label>
              <input
                type="number"
                min="0"
                value={para}
                onChange={(e) => setPara(parseInt(e.target.value) || 0)}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Abortions</label>
              <input
                type="number"
                min="0"
                value={abortions}
                onChange={(e) => setAbortions(parseInt(e.target.value) || 0)}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Living Children</label>
              <input
                type="number"
                min="0"
                value={livingChildren}
                onChange={(e) => setLivingChildren(parseInt(e.target.value) || 0)}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Pregnancy Type</label>
              <select
                value={pregnancyType}
                onChange={(e) => setPregnancyType(e.target.value as PregnancyType)}
              >
                {PREGNANCY_TYPE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Medical History */}
        <div className={styles.section}>
          <h2>Medical History</h2>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>Past Medical History</label>
              <textarea
                value={pastMedicalHistory}
                onChange={(e) => setPastMedicalHistory(e.target.value)}
                rows={3}
                placeholder="Relevant past medical history"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Past Surgical History</label>
              <textarea
                value={pastSurgicalHistory}
                onChange={(e) => setPastSurgicalHistory(e.target.value)}
                rows={3}
                placeholder="Past surgical procedures"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Family History</label>
              <textarea
                value={familyHistory}
                onChange={(e) => setFamilyHistory(e.target.value)}
                rows={3}
                placeholder="Family history relevant to pregnancy"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Allergies</label>
              <textarea
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
                rows={2}
                placeholder="Known allergies"
              />
            </div>
          </div>
        </div>

        {/* Obstetric History */}
        <div className={styles.section}>
          <h2>Obstetric History</h2>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={previousCs}
                  onChange={(e) => setPreviousCs(e.target.checked)}
                />
                Previous Cesarean Section
              </label>
            </div>
            {previousCs && (
              <div className={styles.formGroup}>
                <label>Number of Previous CS</label>
                <input
                  type="number"
                  min="0"
                  value={previousCsCount}
                  onChange={(e) => setPreviousCsCount(parseInt(e.target.value) || 0)}
                />
              </div>
            )}
            <div className={styles.formGroup}>
              <label>Previous Complications</label>
              <textarea
                value={previousComplications}
                onChange={(e) => setPreviousComplications(e.target.value)}
                rows={3}
                placeholder="Previous pregnancy complications"
              />
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        <div className={styles.section}>
          <h2>Risk Assessment</h2>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={highRisk}
                  onChange={(e) => setHighRisk(e.target.checked)}
                />
                High Risk Pregnancy
              </label>
            </div>
            <div className={styles.formGroup}>
              <label>Risk Factors (comma-separated)</label>
              <input
                type="text"
                value={riskFactors}
                onChange={(e) => setRiskFactors(e.target.value)}
                placeholder="e.g., Advanced maternal age, Hypertension, Diabetes"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Clinical Notes</label>
              <textarea
                value={clinicalNotes}
                onChange={(e) => setClinicalNotes(e.target.value)}
                rows={4}
                placeholder="Additional clinical notes"
              />
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className={styles.formActions}>
          <button
            type="button"
            onClick={() => navigate('/antenatal')}
            className={styles.cancelButton}
            disabled={isCreating}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.submitButton}
            disabled={isCreating || !selectedPatient}
          >
            {isCreating ? 'Creating...' : 'Create Antenatal Record'}
          </button>
        </div>
      </form>
    </div>
  );
}
