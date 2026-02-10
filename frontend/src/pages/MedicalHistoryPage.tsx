/**
 * Medical History Page
 * 
 * Shows comprehensive medical history for a patient across all visits:
 * - All visits (chronological)
 * - Consultations and diagnoses
 * - Prescriptions history
 * - Lab results history
 * - Radiology results history
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatient } from '../api/patient';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { fetchConsultation } from '../api/consultation';
import { fetchPrescriptions } from '../api/prescription';
import { fetchLabOrders, fetchLabResults } from '../api/lab';
import { fetchRadiologyOrders, fetchRadiologyResults } from '../api/radiology';
import { Patient } from '../types/patient';
import { Visit } from '../types/visit';
import { Consultation } from '../types/consultation';
import { Prescription } from '../types/prescription';
import { LabOrder, LabResult } from '../types/lab';
import { RadiologyOrder, RadiologyResult } from '../types/radiology';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/MedicalHistory.module.css';

interface VisitHistory {
  visit: Visit;
  consultation: Consultation | null;
  prescriptions: Prescription[];
  labOrders: LabOrder[];
  labResults: LabResult[];
  radiologyOrders: RadiologyOrder[];
  radiologyResults: RadiologyResult[];
}

export default function MedicalHistoryPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [visitHistory, setVisitHistory] = useState<VisitHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedVisits, setExpandedVisits] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (patientId) {
      loadMedicalHistory();
    }
  }, [patientId]);

  const loadMedicalHistory = async () => {
    if (!patientId) return;

    try {
      setLoading(true);

      // Load patient
      const patientData = await getPatient(parseInt(patientId));
      setPatient(patientData);

      // Load all visits for this patient
      const visitsResponse = await fetchVisits({ patient: parseInt(patientId) });
      const visits = Array.isArray(visitsResponse)
        ? visitsResponse
        : (visitsResponse as PaginatedResponse<Visit>).results;

      // Sort visits by date (newest first)
      visits.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      // Load data for each visit
      // Only fetch consultation for CLOSED visits (OPEN visits may return 403 until registration is paid)
      const history: VisitHistory[] = await Promise.all(
        visits.map(async (visit) => {
          try {
            const consultationPromise =
              visit.status === 'CLOSED'
                ? fetchConsultation(visit.id.toString()).catch(() => null)
                : Promise.resolve(null);
            const [consultation, prescriptions, labOrders, labResults, radiologyOrders, radiologyResults] =
              await Promise.all([
                consultationPromise,
                fetchPrescriptions(visit.id.toString()).catch(() => []),
                fetchLabOrders(visit.id.toString()).catch(() => []),
                fetchLabResults(visit.id.toString()).catch((err: any) => {
                  // 404 is expected when no results exist
                  const status = err?.status || err?.response?.status || err?.responseData?.status;
                  if (status === 404) {
                    return [];
                  }
                  console.warn(`Error loading lab results for visit ${visit.id}:`, err);
                  return [];
                }),
                fetchRadiologyOrders(visit.id.toString()).catch(() => []),
                fetchRadiologyResults(visit.id.toString()).catch((err: any) => {
                  // 404 is expected when no results exist
                  const status = err?.status || err?.response?.status || err?.responseData?.status;
                  if (status === 404) {
                    return [];
                  }
                  console.warn(`Error loading radiology results for visit ${visit.id}:`, err);
                  return [];
                }),
              ]);

            return {
              visit,
              consultation: consultation as Consultation | null,
              prescriptions: prescriptions as Prescription[],
              labOrders: labOrders as LabOrder[],
              labResults: labResults as LabResult[],
              radiologyOrders: radiologyOrders as RadiologyOrder[],
              radiologyResults: radiologyResults as RadiologyResult[],
            };
          } catch (error) {
            console.error(`Error loading data for visit ${visit.id}:`, error);
            return {
              visit,
              consultation: null,
              prescriptions: [],
              labOrders: [],
              labResults: [],
              radiologyOrders: [],
              radiologyResults: [],
            };
          }
        })
      );

      setVisitHistory(history);
      // Expand the most recent visit by default
      if (history.length > 0) {
        setExpandedVisits(new Set([history[0].visit.id]));
      }
    } catch (error) {
      console.error('Error loading medical history:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load medical history';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const toggleVisit = (visitId: number) => {
    setExpandedVisits((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(visitId)) {
        newSet.delete(visitId);
      } else {
        newSet.add(visitId);
      }
      return newSet;
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
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

  if (loading) {
    return (
      <div className={styles.medicalHistoryPage}>
        <BackToDashboard />
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  if (!patient) {
    return (
      <div className={styles.medicalHistoryPage}>
        <BackToDashboard />
        <div className={styles.errorContainer}>
          <p>Patient not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.medicalHistoryPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Medical History</h1>
        <div className={styles.patientInfo}>
          <h2>{patient.full_name}</h2>
          <p>Patient ID: {patient.patient_id}</p>
          {patient.age && <p>Age: {patient.age} years</p>}
          {patient.gender && <p>Gender: {patient.gender}</p>}
        </div>
      </header>

      {visitHistory.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No visit history found for this patient</p>
        </div>
      ) : (
        <div className={styles.timeline}>
          {visitHistory.map((history) => {
            const isExpanded = expandedVisits.has(history.visit.id);
            const hasData =
              history.consultation ||
              history.prescriptions.length > 0 ||
              history.labOrders.length > 0 ||
              history.labResults.length > 0 ||
              history.radiologyOrders.length > 0 ||
              history.radiologyResults.length > 0;

            return (
              <div key={history.visit.id} className={styles.timelineItem}>
                <div className={styles.timelineHeader} onClick={() => toggleVisit(history.visit.id)}>
                  <div className={styles.timelineDate}>
                    <strong>{formatDate(history.visit.created_at)}</strong>
                    <span className={styles.visitId}>Visit #{history.visit.id}</span>
                  </div>
                  <div className={styles.timelineBadges}>
                    <span
                      className={`${styles.badge} ${
                        history.visit.status === 'OPEN' ? styles.badgeOpen : styles.badgeClosed
                      }`}
                    >
                      {history.visit.status}
                    </span>
                    <span
                      className={`${styles.badge} ${
                        history.visit.payment_status === 'PAID' || history.visit.payment_status === 'SETTLED'
                          ? styles.badgeCleared
                          : styles.badgePending
                      }`}
                    >
                      {history.visit.payment_status}
                    </span>
                    {hasData && (
                      <span className={styles.expandIcon}>
                        {isExpanded ? '▼' : '▶'}
                      </span>
                    )}
                  </div>
                </div>

                {isExpanded && hasData && (
                  <div className={styles.timelineContent}>
                    {/* Consultation */}
                    {history.consultation && (
                      <div className={styles.section}>
                        <h3>Consultation</h3>
                        <div className={styles.consultationCard}>
                          {history.consultation.history && (
                            <div className={styles.field}>
                              <label>History:</label>
                              <p>{history.consultation.history}</p>
                            </div>
                          )}
                          {history.consultation.examination && (
                            <div className={styles.field}>
                              <label>Examination:</label>
                              <p>{history.consultation.examination}</p>
                            </div>
                          )}
                          {history.consultation.diagnosis && (
                            <div className={styles.field}>
                              <label>Diagnosis:</label>
                              <p className={styles.diagnosis}>{history.consultation.diagnosis}</p>
                            </div>
                          )}
                          {history.consultation.clinical_notes && (
                            <div className={styles.field}>
                              <label>Clinical Notes:</label>
                              <p>{history.consultation.clinical_notes}</p>
                            </div>
                          )}
                          <div className={styles.meta}>
                            <span>Date: {formatDateTime(history.consultation.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Prescriptions */}
                    {history.prescriptions.length > 0 && (
                      <div className={styles.section}>
                        <h3>Prescriptions ({history.prescriptions.length})</h3>
                        <div className={styles.itemsList}>
                          {history.prescriptions.map((prescription) => (
                            <div key={prescription.id} className={styles.itemCard}>
                              <div className={styles.itemHeader}>
                                <strong>{prescription.drug}</strong>
                                <span className={styles.statusBadge}>{prescription.status}</span>
                                {prescription.dispensed && (
                                  <span className={styles.dispensedBadge}>DISPENSED</span>
                                )}
                              </div>
                              <div className={styles.itemDetails}>
                                <p><strong>Dosage:</strong> {prescription.dosage}</p>
                                {prescription.frequency && (
                                  <p><strong>Frequency:</strong> {prescription.frequency}</p>
                                )}
                                {prescription.duration && (
                                  <p><strong>Duration:</strong> {prescription.duration}</p>
                                )}
                                {prescription.quantity && (
                                  <p><strong>Quantity:</strong> {prescription.quantity}</p>
                                )}
                                {prescription.instructions && (
                                  <p><strong>Instructions:</strong> {prescription.instructions}</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Lab Results */}
                    {history.labResults.length > 0 && (
                      <div className={styles.section}>
                        <h3>Lab Results ({history.labResults.length})</h3>
                        <div className={styles.itemsList}>
                          {history.labResults.map((result) => (
                            <div key={result.id} className={styles.itemCard}>
                              <div className={styles.itemHeader}>
                                <strong>Lab Order #{result.lab_order_id}</strong>
                                {result.abnormal_flag && result.abnormal_flag !== 'NORMAL' && (
                                  <span className={styles.abnormalBadge}>
                                    {result.abnormal_flag}
                                  </span>
                                )}
                              </div>
                              <div className={styles.itemDetails}>
                                {result.result_data && (
                                  <div className={styles.resultsData}>
                                    <pre>{typeof result.result_data === 'string' ? result.result_data : JSON.stringify(result.result_data, null, 2)}</pre>
                                  </div>
                                )}
                                <div className={styles.meta}>
                                  <span>Recorded: {formatDateTime(result.recorded_at)}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Radiology Results */}
                    {history.radiologyResults.length > 0 && (
                      <div className={styles.section}>
                        <h3>Radiology Reports ({history.radiologyResults.length})</h3>
                        <div className={styles.itemsList}>
                          {history.radiologyResults.map((result) => (
                            <div key={result.id} className={styles.itemCard}>
                              <div className={styles.itemHeader}>
                                <strong>Radiology Request #{result.radiology_request_id}</strong>
                                {result.finding_flag && result.finding_flag !== 'NORMAL' && (
                                  <span className={styles.findingsBadge}>
                                    {result.finding_flag}
                                  </span>
                                )}
                              </div>
                              <div className={styles.itemDetails}>
                                {result.report && (
                                  <div className={styles.reportData}>
                                    <p>{result.report}</p>
                                  </div>
                                )}
                                {result.image_count !== undefined && result.image_count > 0 && (
                                  <p><strong>Images:</strong> {result.image_count}</p>
                                )}
                                <div className={styles.meta}>
                                  <span>Reported: {formatDateTime(result.reported_at)}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className={styles.actions}>
                      <button
                        className={styles.viewButton}
                        onClick={() => navigate(`/visits/${history.visit.id}`)}
                      >
                        View Full Visit Details
                      </button>
                      {history.visit.status === 'OPEN' && user?.role === 'DOCTOR' && (
                        <button
                          className={styles.consultButton}
                          onClick={() => navigate(`/visits/${history.visit.id}/consultation`)}
                        >
                          Continue Consultation
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

