/**
 * Inpatients Page
 * 
 * Displays a list of all currently admitted patients (inpatients).
 * Shows ward, bed, admission date, length of stay, etc.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import { fetchInpatients, fetchWards, Admission, Ward } from '../api/admissions';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Inpatients.module.css';

export default function InpatientsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  
  const [inpatients, setInpatients] = useState<Admission[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWardId, setSelectedWardId] = useState<number | ''>('');

  useEffect(() => {
    loadData();
  }, [selectedWardId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [inpatientsData, wardsData] = await Promise.all([
        fetchInpatients(selectedWardId ? selectedWardId : undefined),
        fetchWards(true), // Only active wards
      ]);
      
      // Handle paginated responses
      const inpatientsArray = Array.isArray(inpatientsData) ? inpatientsData : (inpatientsData as any).results || [];
      const wardsArray = Array.isArray(wardsData) ? wardsData : (wardsData as any).results || [];
      
      setInpatients(inpatientsArray);
      setWards(wardsArray);
    } catch (error: any) {
      console.error('Failed to load inpatients:', error);
      showError('Failed to load inpatients list.');
      // Ensure wards is always an array even on error
      setWards([]);
      setInpatients([]);
    } finally {
      setLoading(false);
    }
  };

  const handleViewVisit = (visitId: number) => {
    navigate(`/visits/${visitId}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Inpatients</h1>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <BackToDashboard />
      <div className={styles.header}>
        <h1>Inpatients</h1>
        <div className={styles.filters}>
          <label>Filter by Ward:</label>
          <select
            value={selectedWardId}
            onChange={(e) => setSelectedWardId(e.target.value ? parseInt(e.target.value) : '')}
            className={styles.wardFilter}
          >
            <option value="">All Wards</option>
            {wards.map((ward) => (
              <option key={ward.id} value={ward.id}>
                {ward.name} ({ward.occupied_beds_count} occupied)
              </option>
            ))}
          </select>
        </div>
      </div>

      {inpatients.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No inpatients currently admitted.</p>
        </div>
      ) : (
        <div className={styles.inpatientsGrid}>
          {inpatients.map((admission) => (
            <div
              key={admission.id}
              className={styles.inpatientCard}
              onClick={() => handleViewVisit(admission.visit_id)}
            >
              <div className={styles.cardHeader}>
                <div>
                  <h3 className={styles.patientName}>{admission.patient_name}</h3>
                  <p className={styles.patientId}>ID: {admission.patient_id}</p>
                </div>
                <span className={styles.statusBadge}>{admission.admission_status}</span>
              </div>

              <div className={styles.cardDetails}>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Ward:</span>
                  <span className={styles.detailValue}>{admission.ward_name}</span>
                </div>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Bed:</span>
                  <span className={styles.detailValue}>{admission.bed_number}</span>
                </div>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Admission Date:</span>
                  <span className={styles.detailValue}>
                    {new Date(admission.admission_date).toLocaleDateString()}
                  </span>
                </div>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Length of Stay:</span>
                  <span className={styles.detailValue}>
                    {admission.length_of_stay_days} day(s)
                  </span>
                </div>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Type:</span>
                  <span className={styles.detailValue}>{admission.admission_type}</span>
                </div>
                <div className={styles.detailItem}>
                  <span className={styles.detailLabel}>Admitted By:</span>
                  <span className={styles.detailValue}>{admission.admitting_doctor_name}</span>
                </div>
              </div>

              <div className={styles.cardFooter}>
                <button
                  className={styles.viewButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleViewVisit(admission.visit_id);
                  }}
                >
                  View Visit →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

