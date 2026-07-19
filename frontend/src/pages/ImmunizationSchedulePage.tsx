/**
 * Nigeria EPI immunization schedule for a patient.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import {
  createImmunizationRecord,
  fetchPatientImmunizations,
  ImmunizationRecord,
  updateImmunizationRecord,
} from '../api/clinical';
import { getPatient, searchPatients } from '../api/patient';
import { Patient } from '../types/patient';
import styles from '../styles/ImmunizationSchedule.module.css';

type VaccineOption = {
  value: string;
  label: string;
  guidance: string;
};

const VACCINES: VaccineOption[] = [
  { value: 'BCG', label: 'BCG', guidance: 'At birth' },
  { value: 'HEP_B', label: 'Hepatitis B birth dose', guidance: 'Within 24 hours of birth' },
  { value: 'OPV', label: 'Oral Polio Vaccine (OPV)', guidance: 'Birth, 6, 10 and 14 weeks' },
  { value: 'IPV', label: 'Inactivated Polio Vaccine (IPV)', guidance: '6 and 14 weeks' },
  { value: 'PENTA', label: 'Pentavalent', guidance: '6, 10 and 14 weeks' },
  { value: 'PCV', label: 'Pneumococcal (PCV)', guidance: '6, 10 and 14 weeks' },
  { value: 'ROTA', label: 'Rotavirus', guidance: '6, 10 and 14 weeks' },
  { value: 'MEASLES', label: 'Measles-containing vaccine', guidance: '9 and 15 months' },
  { value: 'YELLOW_FEVER', label: 'Yellow Fever', guidance: '9 months' },
  { value: 'MEN_A', label: 'Meningococcal A', guidance: '9 months' },
  { value: 'MALARIA', label: 'Malaria vaccine', guidance: 'According to the national eligibility schedule' },
  { value: 'HPV', label: 'Human Papillomavirus (HPV)', guidance: 'Eligible adolescents' },
  { value: 'TD', label: 'Tetanus-Diphtheria (Td)', guidance: 'According to eligibility' },
];

const today = () => new Date().toISOString().slice(0, 10);

const formatDate = (value: string | null) => {
  if (!value) return 'Not recorded';
  return new Intl.DateTimeFormat('en-NG', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
};

const getStatus = (record: ImmunizationRecord) => {
  if (record.administered_date) return 'administered';
  if (record.scheduled_date && record.scheduled_date < today()) return 'overdue';
  return 'scheduled';
};

const displayPatientName = (patient: Patient) =>
  patient.full_name ||
  [patient.first_name, patient.middle_name, patient.last_name].filter(Boolean).join(' ');

export default function ImmunizationSchedulePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { showError, showSuccess } = useToast();
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [records, setRecords] = useState<ImmunizationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [vaccine, setVaccine] = useState('BCG');
  const [doseNumber, setDoseNumber] = useState(1);
  const [scheduledDate, setScheduledDate] = useState('');
  const [batchNumber, setBatchNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [administerNow, setAdministerNow] = useState(false);
  const [administeringRecord, setAdministeringRecord] =
    useState<ImmunizationRecord | null>(null);
  const [administrationDate, setAdministrationDate] = useState(today());
  const [administrationBatch, setAdministrationBatch] = useState('');
  const [administrationNotes, setAdministrationNotes] = useState('');

  const loadRecords = useCallback(
    async (patientId: number) => {
      try {
        setLoading(true);
        setRecords(await fetchPatientImmunizations(patientId));
      } catch (error: unknown) {
        showError(error instanceof Error ? error.message : 'Failed to load immunizations');
      } finally {
        setLoading(false);
      }
    },
    [showError],
  );

  const selectPatient = useCallback(
    (patient: Patient) => {
      setSelectedPatient(patient);
      setSearchResults([]);
      setQuery('');
      setSearchParams({ patient_id: String(patient.id) }, { replace: true });
      void loadRecords(patient.id);
    },
    [loadRecords, setSearchParams],
  );

  useEffect(() => {
    const patientId = Number(searchParams.get('patient_id'));
    if (!Number.isInteger(patientId) || patientId <= 0) return;

    let active = true;
    void getPatient(patientId)
      .then((patient) => {
        if (!active) return;
        setSelectedPatient(patient);
        return loadRecords(patient.id);
      })
      .catch((error: unknown) => {
        if (active) {
          showError(error instanceof Error ? error.message : 'Patient could not be loaded');
        }
      });
    return () => {
      active = false;
    };
  }, [loadRecords, searchParams, showError]);

  const handlePatientSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    const term = query.trim();
    if (term.length < 2) {
      showError('Enter at least 2 characters of a name, phone number, or patient ID');
      return;
    }
    try {
      setSearching(true);
      const results = await searchPatients(term);
      setSearchResults(results);
      if (results.length === 0) showError('No matching patients found');
    } catch (error: unknown) {
      showError(error instanceof Error ? error.message : 'Patient search failed');
    } finally {
      setSearching(false);
    }
  };

  const resetForm = () => {
    setVaccine('BCG');
    setDoseNumber(1);
    setScheduledDate('');
    setBatchNumber('');
    setNotes('');
    setAdministerNow(false);
    setShowForm(false);
  };

  const handleAdd = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedPatient) {
      showError('Select a patient first');
      return;
    }
    if (!administerNow && !scheduledDate) {
      showError('Select a scheduled date or record the dose as administered now');
      return;
    }
    try {
      setSaving(true);
      await createImmunizationRecord(selectedPatient.id, {
        vaccine,
        scheduled_date: scheduledDate || null,
        administered_date: administerNow ? today() : null,
        administered: administerNow,
        dose_number: doseNumber,
        batch_number: batchNumber.trim(),
        notes: notes.trim(),
      });
      showSuccess(administerNow ? 'Immunization recorded' : 'Immunization scheduled');
      resetForm();
      await loadRecords(selectedPatient.id);
    } catch (error: unknown) {
      showError(error instanceof Error ? error.message : 'Failed to save immunization');
    } finally {
      setSaving(false);
    }
  };

  const openAdministration = (record: ImmunizationRecord) => {
    setAdministeringRecord(record);
    setAdministrationDate(today());
    setAdministrationBatch(record.batch_number || '');
    setAdministrationNotes(record.notes || '');
  };

  const handleMarkAdministered = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!administeringRecord || !selectedPatient) return;
    try {
      setSaving(true);
      await updateImmunizationRecord(administeringRecord.id, {
        administered_date: administrationDate,
        batch_number: administrationBatch.trim(),
        notes: administrationNotes.trim(),
        mark_administered: true,
      });
      showSuccess('Dose marked as administered');
      setAdministeringRecord(null);
      await loadRecords(selectedPatient.id);
    } catch (error: unknown) {
      showError(error instanceof Error ? error.message : 'Failed to update immunization');
    } finally {
      setSaving(false);
    }
  };

  const summary = useMemo(
    () =>
      records.reduce(
        (counts, record) => {
          counts[getStatus(record)] += 1;
          return counts;
        },
        { administered: 0, scheduled: 0, overdue: 0 },
      ),
    [records],
  );

  const vaccineLabel = (value: string) =>
    VACCINES.find((option) => option.value === value)?.label || value;

  return (
    <main className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>Clinical care</span>
          <h1>Immunization Schedule</h1>
          <p>Schedule and document vaccinations using Nigeria EPI guidance.</p>
        </div>
        {selectedPatient && (
          <button className={styles.secondaryButton} type="button" onClick={() => setShowForm(true)}>
            + Add immunization
          </button>
        )}
      </header>

      <section className={styles.patientSearch} aria-labelledby="patient-search-title">
        <div>
          <h2 id="patient-search-title">Find a patient</h2>
          <p>Search by name, hospital number, phone number, or national ID.</p>
        </div>
        <form className={styles.searchForm} onSubmit={handlePatientSearch}>
          <input
            aria-label="Search patients"
            placeholder="e.g. Amina Bello or LMC-000123"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {searchResults.length > 0 && (
          <div className={styles.searchResults}>
            {searchResults.map((patient) => (
              <button
                key={patient.id}
                type="button"
                className={styles.patientResult}
                onClick={() => selectPatient(patient)}
              >
                <span className={styles.avatar}>
                  {patient.first_name?.[0]}
                  {patient.last_name?.[0]}
                </span>
                <span>
                  <strong>{displayPatientName(patient)}</strong>
                  <small>
                    {patient.patient_id} · {patient.gender || 'Gender not recorded'} ·{' '}
                    {patient.age != null ? `${patient.age} years` : 'Age not recorded'}
                  </small>
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      {!selectedPatient ? (
        <section className={styles.welcomeState}>
          <div className={styles.welcomeIcon}>💉</div>
          <h2>Select a patient to view their schedule</h2>
          <p>Patient vaccination history, upcoming doses, and overdue doses will appear here.</p>
        </section>
      ) : (
        <>
          <section className={styles.patientBanner}>
            <div className={styles.avatarLarge}>
              {selectedPatient.first_name?.[0]}
              {selectedPatient.last_name?.[0]}
            </div>
            <div className={styles.patientDetails}>
              <span>Selected patient</span>
              <h2>{displayPatientName(selectedPatient)}</h2>
              <p>
                {selectedPatient.patient_id} ·{' '}
                {selectedPatient.date_of_birth
                  ? `Born ${formatDate(selectedPatient.date_of_birth)}`
                  : 'Date of birth not recorded'}
                {selectedPatient.phone ? ` · ${selectedPatient.phone}` : ''}
              </p>
            </div>
            <button
              type="button"
              className={styles.textButton}
              onClick={() => {
                setSelectedPatient(null);
                setRecords([]);
                setSearchParams({}, { replace: true });
              }}
            >
              Change patient
            </button>
          </section>

          <section className={styles.summaryGrid} aria-label="Immunization summary">
            <article className={styles.summaryCard}>
              <span className={`${styles.summaryDot} ${styles.dotGreen}`} />
              <div><strong>{summary.administered}</strong><span>Administered</span></div>
            </article>
            <article className={styles.summaryCard}>
              <span className={`${styles.summaryDot} ${styles.dotBlue}`} />
              <div><strong>{summary.scheduled}</strong><span>Upcoming</span></div>
            </article>
            <article className={styles.summaryCard}>
              <span className={`${styles.summaryDot} ${styles.dotRed}`} />
              <div><strong>{summary.overdue}</strong><span>Overdue</span></div>
            </article>
            <article className={styles.summaryCard}>
              <span className={`${styles.summaryDot} ${styles.dotSlate}`} />
              <div><strong>{records.length}</strong><span>Total records</span></div>
            </article>
          </section>

          {showForm && (
            <section className={styles.formCard}>
              <div className={styles.sectionHeading}>
                <div><h2>Add immunization</h2><p>Schedule a future dose or document one given today.</p></div>
                <button type="button" className={styles.closeButton} onClick={resetForm} aria-label="Close form">×</button>
              </div>
              <form onSubmit={handleAdd}>
                <div className={styles.formGrid}>
                  <label>
                    Vaccine
                    <select value={vaccine} onChange={(event) => setVaccine(event.target.value)}>
                      {VACCINES.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                    <small>{VACCINES.find((option) => option.value === vaccine)?.guidance}</small>
                  </label>
                  <label>
                    Dose number
                    <input type="number" min={1} max={10} value={doseNumber} onChange={(event) => setDoseNumber(Number(event.target.value))} />
                  </label>
                  <label>
                    Scheduled date
                    <input type="date" value={scheduledDate} onChange={(event) => setScheduledDate(event.target.value)} disabled={administerNow} />
                  </label>
                  <label>
                    Batch / lot number
                    <input value={batchNumber} onChange={(event) => setBatchNumber(event.target.value)} placeholder="Optional" />
                  </label>
                  <label className={styles.fullWidth}>
                    Clinical notes
                    <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} placeholder="Optional observations or context" />
                  </label>
                </div>
                <label className={styles.checkbox}>
                  <input type="checkbox" checked={administerNow} onChange={(event) => setAdministerNow(event.target.checked)} />
                  Record this dose as administered today
                </label>
                <div className={styles.formActions}>
                  <button type="button" className={styles.secondaryButton} onClick={resetForm}>Cancel</button>
                  <button type="submit" disabled={saving}>{saving ? 'Saving…' : administerNow ? 'Record dose' : 'Schedule dose'}</button>
                </div>
              </form>
            </section>
          )}

          <section className={styles.recordsSection}>
            <div className={styles.sectionHeading}>
              <div><h2>Vaccination record</h2><p>Complete history and scheduled doses for this patient.</p></div>
            </div>
            {loading ? (
              <LoadingSkeleton count={5} />
            ) : records.length === 0 ? (
              <div className={styles.emptyState}>
                <span>💉</span>
                <h3>No immunizations recorded</h3>
                <p>Add the first vaccination record for this patient.</p>
                <button type="button" onClick={() => setShowForm(true)}>Add immunization</button>
              </div>
            ) : (
              <div className={styles.tableContainer}>
                <table>
                  <thead>
                    <tr>
                      <th>Vaccine</th>
                      <th>Dose</th>
                      <th>Scheduled</th>
                      <th>Administered</th>
                      <th>Batch</th>
                      <th>Status</th>
                      <th><span className={styles.srOnly}>Actions</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((record) => {
                      const status = getStatus(record);
                      return (
                        <tr key={record.id}>
                          <td><strong>{vaccineLabel(record.vaccine)}</strong>{record.notes && <small>{record.notes}</small>}</td>
                          <td>{record.dose_number}</td>
                          <td>{formatDate(record.scheduled_date)}</td>
                          <td>{formatDate(record.administered_date)}</td>
                          <td>{record.batch_number || '—'}</td>
                          <td><span className={`${styles.status} ${styles[status]}`}>{status}</span></td>
                          <td>
                            {!record.administered_date && (
                              <button className={styles.actionButton} type="button" onClick={() => openAdministration(record)}>Administer</button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {administeringRecord && (
        <div className={styles.modalBackdrop} role="presentation" onMouseDown={() => setAdministeringRecord(null)}>
          <section className={styles.modal} role="dialog" aria-modal="true" aria-labelledby="administer-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className={styles.sectionHeading}>
              <div><span className={styles.eyebrow}>Record administration</span><h2 id="administer-title">{vaccineLabel(administeringRecord.vaccine)} · Dose {administeringRecord.dose_number}</h2></div>
              <button type="button" className={styles.closeButton} onClick={() => setAdministeringRecord(null)} aria-label="Close">×</button>
            </div>
            <form onSubmit={handleMarkAdministered}>
              <label>
                Administration date
                <input type="date" required max={today()} value={administrationDate} onChange={(event) => setAdministrationDate(event.target.value)} />
              </label>
              <label>
                Batch / lot number
                <input value={administrationBatch} onChange={(event) => setAdministrationBatch(event.target.value)} placeholder="Enter vaccine batch number" />
              </label>
              <label>
                Notes
                <textarea rows={3} value={administrationNotes} onChange={(event) => setAdministrationNotes(event.target.value)} placeholder="Optional clinical notes" />
              </label>
              <div className={styles.formActions}>
                <button type="button" className={styles.secondaryButton} onClick={() => setAdministeringRecord(null)}>Cancel</button>
                <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Confirm administration'}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
