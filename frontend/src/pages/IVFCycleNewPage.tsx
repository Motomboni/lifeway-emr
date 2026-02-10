/**
 * IVF Cycle New Page
 * 
 * Form for creating a new IVF cycle with:
 * - Patient selection
 * - Cycle type selection
 * - Planned start date
 * - Diagnosis and protocol
 * - Consent documentation
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createIVFCycle, IVFCycleCreateData, CycleType, CYCLE_TYPE_LABELS } from '../api/ivf';
import { fetchPatients } from '../api/patient';
import { Patient } from '../types/patient';
import styles from '../styles/IVFCycleNew.module.css';

interface FormData {
  patient: number | null;
  partner: number | null;
  cycle_type: CycleType;
  planned_start_date: string;
  lmp_date: string;
  protocol: string;
  diagnosis: string;
  estimated_cost: string;
  insurance_pre_auth: boolean;
  insurance_pre_auth_number: string;
  clinical_notes: string;
}

const PROTOCOL_OPTIONS = [
  { value: 'LONG_AGONIST', label: 'Long Agonist Protocol' },
  { value: 'SHORT_AGONIST', label: 'Short Agonist Protocol' },
  { value: 'ANTAGONIST', label: 'GnRH Antagonist Protocol' },
  { value: 'MILD_STIMULATION', label: 'Mild Stimulation Protocol' },
  { value: 'NATURAL_CYCLE', label: 'Natural Cycle' },
  { value: 'MINI_IVF', label: 'Mini IVF' },
  { value: 'MODIFIED_NATURAL', label: 'Modified Natural Cycle' },
];

const DIAGNOSIS_OPTIONS = [
  'Unexplained Infertility',
  'Male Factor Infertility',
  'Tubal Factor',
  'Endometriosis',
  'Ovulatory Dysfunction',
  'Diminished Ovarian Reserve',
  'Polycystic Ovary Syndrome (PCOS)',
  'Uterine Factor',
  'Recurrent Pregnancy Loss',
  'Advanced Maternal Age',
  'Combined Factors',
  'Other',
];

export default function IVFCycleNewPage() {
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState<FormData>({
    patient: null,
    partner: null,
    cycle_type: 'FRESH_IVF',
    planned_start_date: '',
    lmp_date: '',
    protocol: '',
    diagnosis: '',
    estimated_cost: '',
    insurance_pre_auth: false,
    insurance_pre_auth_number: '',
    clinical_notes: '',
  });
  
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientSearch, setPatientSearch] = useState('');
  const [partnerSearch, setPartnerSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchingPatients, setSearchingPatients] = useState(false);

  // Load patients on search
  useEffect(() => {
    const searchPatientsAsync = async () => {
      if (patientSearch.length < 2 && partnerSearch.length < 2) {
        return;
      }
      
      try {
        setSearchingPatients(true);
        const query = patientSearch || partnerSearch;
        const data = await fetchPatients(query);
        setPatients(data);
      } catch (err) {
        console.error('Failed to search patients:', err);
      } finally {
        setSearchingPatients(false);
      }
    };

    const debounce = setTimeout(searchPatientsAsync, 300);
    return () => clearTimeout(debounce);
  }, [patientSearch, partnerSearch]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handlePatientSelect = (patient: Patient) => {
    setFormData(prev => ({ ...prev, patient: patient.id }));
    setPatientSearch(`${patient.first_name} ${patient.last_name} (${patient.patient_id})`);
  };

  const handlePartnerSelect = (patient: Patient) => {
    setFormData(prev => ({ ...prev, partner: patient.id }));
    setPartnerSearch(`${patient.first_name} ${patient.last_name} (${patient.patient_id})`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.patient) {
      setError('Please select a patient');
      return;
    }
    
    if (!formData.planned_start_date) {
      setError('Please set a planned start date');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const createData: IVFCycleCreateData = {
        patient: formData.patient,
        partner: formData.partner || undefined,
        cycle_type: formData.cycle_type,
        planned_start_date: formData.planned_start_date,
        lmp_date: formData.lmp_date || undefined,
        protocol: formData.protocol || undefined,
        diagnosis: formData.diagnosis || undefined,
        estimated_cost: formData.estimated_cost ? parseFloat(formData.estimated_cost) : undefined,
        insurance_pre_auth: formData.insurance_pre_auth,
        insurance_pre_auth_number: formData.insurance_pre_auth_number || undefined,
        clinical_notes: formData.clinical_notes || undefined,
      };

      const cycle = await createIVFCycle(createData);
      navigate(`/ivf/cycles/${cycle.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create IVF cycle');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <button 
          className={styles.backButton}
          onClick={() => navigate('/ivf')}
        >
          ← Back to IVF Dashboard
        </button>
        <h1>New IVF Cycle</h1>
      </header>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <form onSubmit={handleSubmit} className={styles.form}>
        {/* Patient Selection Section */}
        <section className={styles.section}>
          <h2>Patient Information</h2>
          
          <div className={styles.formGroup}>
            <label htmlFor="patient">Primary Patient *</label>
            <div className={styles.searchContainer}>
              <input
                type="text"
                id="patient"
                placeholder="Search by name or patient ID..."
                value={patientSearch}
                onChange={(e) => {
                  setPatientSearch(e.target.value);
                  if (!e.target.value) {
                    setFormData(prev => ({ ...prev, patient: null }));
                  }
                }}
                className={styles.searchInput}
              />
              {searchingPatients && <span className={styles.searching}>Searching...</span>}
              {patientSearch.length >= 2 && patients.length > 0 && !formData.patient && (
                <ul className={styles.searchResults}>
                  {patients.map(p => (
                    <li key={p.id} onClick={() => handlePatientSelect(p)}>
                      <strong>{p.first_name} {p.last_name}</strong>
                      <span>{p.patient_id} • {p.gender} • {p.date_of_birth}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <small>Search for the female patient undergoing IVF treatment</small>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="partner">Partner (Optional)</label>
            <div className={styles.searchContainer}>
              <input
                type="text"
                id="partner"
                placeholder="Search for partner..."
                value={partnerSearch}
                onChange={(e) => {
                  setPartnerSearch(e.target.value);
                  if (!e.target.value) {
                    setFormData(prev => ({ ...prev, partner: null }));
                  }
                }}
                className={styles.searchInput}
              />
              {partnerSearch.length >= 2 && patients.length > 0 && !formData.partner && (
                <ul className={styles.searchResults}>
                  {patients.map(p => (
                    <li key={p.id} onClick={() => handlePartnerSelect(p)}>
                      <strong>{p.first_name} {p.last_name}</strong>
                      <span>{p.patient_id} • {p.gender} • {p.date_of_birth}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <small>Search for the male partner if applicable</small>
          </div>
        </section>

        {/* Cycle Details Section */}
        <section className={styles.section}>
          <h2>Cycle Details</h2>
          
          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="cycle_type">Cycle Type *</label>
              <select
                id="cycle_type"
                name="cycle_type"
                value={formData.cycle_type}
                onChange={handleInputChange}
                required
              >
                {Object.entries(CYCLE_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="protocol">Stimulation Protocol</label>
              <select
                id="protocol"
                name="protocol"
                value={formData.protocol}
                onChange={handleInputChange}
              >
                <option value="">Select protocol...</option>
                {PROTOCOL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="planned_start_date">Planned Start Date *</label>
              <input
                type="date"
                id="planned_start_date"
                name="planned_start_date"
                value={formData.planned_start_date}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="lmp_date">Last Menstrual Period (LMP)</label>
              <input
                type="date"
                id="lmp_date"
                name="lmp_date"
                value={formData.lmp_date}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="diagnosis">Primary Diagnosis</label>
            <select
              id="diagnosis"
              name="diagnosis"
              value={formData.diagnosis}
              onChange={handleInputChange}
            >
              <option value="">Select diagnosis...</option>
              {DIAGNOSIS_OPTIONS.map(diag => (
                <option key={diag} value={diag}>{diag}</option>
              ))}
            </select>
          </div>
        </section>

        {/* Financial Section */}
        <section className={styles.section}>
          <h2>Financial Information</h2>
          
          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="estimated_cost">Estimated Cost (₦)</label>
              <input
                type="number"
                id="estimated_cost"
                name="estimated_cost"
                value={formData.estimated_cost}
                onChange={handleInputChange}
                placeholder="Enter estimated cost..."
                min="0"
                step="0.01"
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  name="insurance_pre_auth"
                  checked={formData.insurance_pre_auth}
                  onChange={handleInputChange}
                />
                Insurance Pre-Authorization Obtained
              </label>
            </div>
          </div>

          {formData.insurance_pre_auth && (
            <div className={styles.formGroup}>
              <label htmlFor="insurance_pre_auth_number">Pre-Authorization Number</label>
              <input
                type="text"
                id="insurance_pre_auth_number"
                name="insurance_pre_auth_number"
                value={formData.insurance_pre_auth_number}
                onChange={handleInputChange}
                placeholder="Enter pre-auth number..."
              />
            </div>
          )}
        </section>

        {/* Notes Section */}
        <section className={styles.section}>
          <h2>Clinical Notes</h2>
          
          <div className={styles.formGroup}>
            <label htmlFor="clinical_notes">Initial Notes</label>
            <textarea
              id="clinical_notes"
              name="clinical_notes"
              value={formData.clinical_notes}
              onChange={handleInputChange}
              rows={4}
              placeholder="Enter any relevant clinical notes, history, or observations..."
            />
          </div>
        </section>

        {/* Consent Notice */}
        <section className={styles.consentNotice}>
          <h3>⚠️ Consent Required</h3>
          <p>
            Per Nigerian healthcare regulations, patient consent must be obtained and documented 
            before proceeding with any IVF procedures. After creating this cycle, navigate to 
            the cycle details page to record consent documentation.
          </p>
        </section>

        {/* Form Actions */}
        <div className={styles.formActions}>
          <button
            type="button"
            className={styles.cancelButton}
            onClick={() => navigate('/ivf')}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.submitButton}
            disabled={loading || !formData.patient}
          >
            {loading ? 'Creating...' : 'Create IVF Cycle'}
          </button>
        </div>
      </form>
    </div>
  );
}
