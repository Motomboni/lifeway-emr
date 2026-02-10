/**
 * Visit Details Page
 * 
 * Shows complete visit history including:
 * - Visit information
 * - Consultation
 * - Services ordered from catalog (billed services)
 * - Payments
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getVisit } from '../api/visits';
import { getPatient } from '../api/patient';
import { fetchConsultation } from '../api/consultation';
import { fetchPayments } from '../api/payment';
import { getBillingSummary, getHMOProviders, getVisitCharges, BillingSummary, VisitCharge } from '../api/billing';
import { Visit } from '../types/visit';
import { Patient } from '../types/patient';
import { Consultation } from '../types/consultation';
import { Payment } from '../types/payment';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import { printVisitSummary, downloadVisitSummaryAsText, downloadVisitSummaryAsHTML } from '../utils/exportUtils';
import DischargeSummarySection from '../components/discharges/DischargeSummarySection';
import AdmissionSection from '../components/admissions/AdmissionSection';
import VisitTimeline from '../components/timeline/VisitTimeline';
import OperationNotes from '../components/clinical/OperationNotes';
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';
import WalletPaymentButton from '../components/wallet/WalletPaymentButton';
import WalletTopUpButton from '../components/wallet/WalletTopUpButton';
import BillingSection from '../components/billing/BillingSection';
import InvoiceReceiptPanel from '../components/billing/InvoiceReceiptPanel';
import { PaystackReturnHandler } from '../components/billing/PaystackCheckout';
import AINotesPanel from '../components/ai/AINotesPanel';
import PrescriptionModule from '../components/pharmacy/PrescriptionModule';
import styles from '../styles/VisitDetails.module.css';

export default function VisitDetailsPage() {
  const { visitId } = useParams<{ visitId: string }>();
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useToast();

  const [visit, setVisit] = useState<Visit | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [charges, setCharges] = useState<VisitCharge[]>([]);
  
  // Billing state (Receptionist only) - passed to BillingSection component
  const [billingSummary, setBillingSummary] = useState<BillingSummary | null>(null);
  const [hmoProviders, setHmoProviders] = useState<any[]>([]);
  
  // Lock checks for explainable locks
  const consultationLock = useActionLock({
    actionType: 'consultation',
    params: { visit_id: visitId ? parseInt(visitId) : 0 },
    enabled: !!visitId && !!visit,
  });

  const loadVisitDetails = useCallback(async (retryCount = 0): Promise<void> => {
    if (!visitId) return;

    try {
      setLoading(true);
      let visitData;
      const visitIdNum = parseInt(visitId);

      if (isNaN(visitIdNum)) {
        console.error('Invalid visit ID:', visitId);
        showError(`Invalid visit ID: ${visitId}`);
        setVisit(null);
        return;
      }

      try {
        const visitValue = await getVisit(visitIdNum);
        visitData = [{ status: 'fulfilled' as const, value: visitValue }];
      } catch (error: any) {
        const is404 = error?.status === 404 || error?.message?.includes('404') || error?.message?.includes('Not Found');
        if (is404 && retryCount === 0) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          return loadVisitDetails(1);
        }
        visitData = [{ status: 'rejected' as const, reason: error }];
      }

      if (visitData[0].status === 'fulfilled') {
        const visitValue = visitData[0].value;
        setVisit(visitValue);
        
        // Load patient information
        if (visitValue.patient) {
          try {
            const patientData = await getPatient(visitValue.patient);
            setPatient(patientData);
          } catch (error) {
            console.warn('Failed to load patient information:', error);
          }
        }
        
        // Load billing summary (all roles) and payments first so we can gate consultation on payment_gates
        const [summaryResult, paymentsData] = await Promise.allSettled([
          getBillingSummary(visitValue.id).catch(() => null),
          fetchPayments(visitId).catch(() => [])
        ]);

        const billingSummaryValue =
          summaryResult.status === 'fulfilled' && summaryResult.value
            ? summaryResult.value
            : null;
        setBillingSummary(billingSummaryValue);

        if (paymentsData.status === 'fulfilled') {
          setPayments(paymentsData.value as Payment[]);
        }

        // Only fetch consultation when registration payment gate is cleared (avoids 403 from backend)
        // CLOSED visits: allow read-only consultation load if we have it
        const registrationPaid = billingSummaryValue?.payment_gates?.registration_paid === true;
        const canLoadClinicalData =
          visitValue.status === 'CLOSED' ? true : registrationPaid;

        if (canLoadClinicalData) {
          try {
            const data = await fetchConsultation(visitId);
            if (Array.isArray(data)) {
              setConsultation(data.length > 0 ? data[0] : null);
            } else {
              setConsultation(data);
            }
          } catch (err) {
            // 404 = no consultation yet; 403 = payment required (handled by UI)
            if (err instanceof Error && !err.message.includes('404') && !err.message.includes('403')) {
              console.warn('Failed to load consultation:', err);
            }
          }
        }
        
        // Load charges for displaying costs with services
        try {
          const chargesData = await getVisitCharges(visitIdNum);
          setCharges(chargesData);
        } catch (error) {
          console.warn('Failed to load charges:', error);
        }
        
        // HMO providers for Receptionists only
        if (user?.role === 'RECEPTIONIST') {
          try {
            const providers = await getHMOProviders();
            setHmoProviders(providers);
          } catch (error) {
            console.warn('Failed to load HMO providers:', error);
          }
        }
      } else {
        // If visit data failed to load, set visit to null to show "Visit Not Found"
        setVisit(null);
        
        // Show error message
        if (visitData[0].status === 'rejected') {
          const reason = visitData[0].reason;
          console.error('Visit data rejected:', reason);
          
          // Check if it's a permission error (403) vs not found (404)
          if (reason instanceof Error) {
            const errorMessage = reason.message;
            const errorStatus = (reason as any).status;
            const errorResponse = (reason as any).responseData;
            
            console.error('Failed to load visit - Full error details:', {
              message: errorMessage,
              status: errorStatus,
              responseData: errorResponse,
              error: reason,
              visitId: visitId,
              visitIdNum: visitIdNum,
              errorType: reason.constructor.name
            });
            
            // Show error for debugging
            if (errorStatus === 403 || errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
              showError('You do not have permission to view this visit. Please contact an administrator.');
            } else if (errorStatus === 404 || errorMessage.includes('404') || errorMessage.includes('Not Found')) {
              // For 404, show a more helpful message
              console.warn('Visit not found - Visit ID:', visitId, 'Error:', errorResponse);
              const detailMessage = errorResponse?.detail || errorMessage || 'Visit does not exist';
              
              // Check if visit might exist but there's a routing/permission issue
              console.warn('Visit 404 details:', {
                visitId,
                visitIdNum,
                errorMessage,
                errorResponse,
                userRole: user?.role,
                endpoint: `/api/v1/visits/${visitIdNum}/`
              });
              
              showError(`Visit ${visitId} not found: ${detailMessage}. Please check the visits list to confirm the visit exists, or contact support if this persists.`);
            } else {
              const detailMessage = errorResponse?.detail || errorMessage || 'Unknown error';
              showError(`Failed to load visit details: ${detailMessage}`);
            }
          } else {
            console.error('Unexpected error format:', reason);
            showError('Failed to load visit details. Please try again or check the visits list.');
          }
        } else {
          console.error('Visit data status is not fulfilled or rejected:', visitData[0]);
          showError('Unexpected error loading visit. Please try again.');
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visit details';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [visitId, showError, user]);

  useEffect(() => {
    if (visitId && !authLoading) {
      const stateVisit = (location.state as any)?.visit;
      if (stateVisit && stateVisit.id === parseInt(visitId)) {
        setVisit(stateVisit);
        setLoading(false);
        loadVisitDetails().catch((err: unknown) => {
          console.warn('Failed to reload visit details, using state data:', err);
        });
      } else {
        loadVisitDetails();
      }
    }
    if (location.hash === '#billing-section') {
      setTimeout(() => {
        const billingSection = document.getElementById('billing-section');
        if (billingSection) {
          billingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 500);
    }
  }, [visitId, location.state, location.hash, authLoading, loadVisitDetails]);

  if (authLoading || (loading && !visit)) {
    return (
      <div className={styles.visitDetailsPage}>
        <LoadingSkeleton count={10} />
      </div>
    );
  }

  if (!visit) {
    return (
      <div className={styles.visitDetailsPage}>
        <BackToDashboard />
        <div className={styles.errorContainer}>
          <h2>Visit Not Found</h2>
          <p>The visit you're looking for doesn't exist or you don't have permission to view it.</p>
          <p className={styles.errorHint}>
            Visit ID: {visitId}
          </p>
          <div className={styles.errorActions}>
            <button onClick={() => navigate('/visits')} className={styles.backButton}>
              Back to Visits
            </button>
            <button onClick={() => navigate('/dashboard')} className={styles.backButton}>
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: string | number) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN'
    }).format(num);
  };

  const getChargeForConsultation = () => {
    return charges.find(c => c.category === 'CONSULTATION');
  };

  return (
    <div className={styles.visitDetailsPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>Visit #{visit.id}</h1>
            <p className={styles.visitMeta}>
              Created: {new Date(visit.created_at).toLocaleString()}
              {visit.closed_at && ` • Closed: ${new Date(visit.closed_at).toLocaleString()}`}
            </p>
          </div>
          <div className={styles.headerActions}>
            <span className={`${styles.statusBadge} ${visit.status === 'OPEN' ? styles.statusOpen : styles.statusClosed}`}>
              {visit.status}
            </span>
            <span className={`${styles.paymentBadge} ${visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED' ? styles.paymentCleared : styles.paymentPending}`}>
              {visit.payment_status}
            </span>
            <div className={styles.exportActions}>
              <button
                className={styles.exportButton}
                onClick={() => printVisitSummary({
                  visit,
                  patient,
                  consultation,
                  payments
                })}
                title="Print visit summary"
              >
                🖨️ Print
              </button>
              <button
                className={styles.exportButton}
                onClick={() => downloadVisitSummaryAsText({
                  visit,
                  patient,
                  consultation,
                  payments
                })}
                title="Download as text file"
              >
                📄 Text
              </button>
              <button
                className={styles.exportButton}
                onClick={() => downloadVisitSummaryAsHTML({
                  visit,
                  patient,
                  consultation,
                  payments
                })}
                title="Download as HTML file"
              >
                🌐 HTML
              </button>
            </div>
            {visit.status === 'OPEN' && user?.role === 'DOCTOR' && (
              <>
                {(() => {
                  const gates = billingSummary?.payment_gates;
                  // Only enable when we have gates (billing loaded) and both payments are done
                  const registrationPaid = gates ? gates.registration_paid === true : false;
                  const consultationPaid = gates ? gates.consultation_paid === true : false;
                  const canAccessConsultation = registrationPaid;
                  const canStartEncounter = consultationPaid;
                  const canStart = canAccessConsultation && canStartEncounter;
                  const disabledTitle = !canAccessConsultation
                    ? 'Registration payment required before access. Collect at reception.'
                    : !canStartEncounter
                    ? 'Consultation payment is required before starting the encounter. Collect at reception.'
                    : undefined;
                  const handleConsultationClick = () => {
                    if (!canStart) {
                      if (!canAccessConsultation) {
                        showError('Registration payment is required before access to consultation. Collect at reception.');
                      } else {
                        showError('Consultation payment is required before starting the encounter. Collect at reception.');
                      }
                      return;
                    }
                    navigate(`/visits/${visitId}/consultation`);
                  };
                  return (
                    <>
                      {consultation ? (
                        <button
                          type="button"
                          className={styles.consultationButton}
                          onClick={handleConsultationClick}
                          disabled={!canStart}
                          title={disabledTitle ?? 'Open consultation'}
                        >
                          Open Consultation
                        </button>
                      ) : (
                        <button
                          type="button"
                          className={styles.consultationButton}
                          onClick={handleConsultationClick}
                          disabled={!canStart}
                          title={disabledTitle ?? 'Start consultation'}
                        >
                          Start Consultation
                        </button>
                      )}
                    </>
                  );
                })()}
                <button
                  className={styles.telemedicineButton}
                  onClick={() => navigate(`/visits/${visitId}/telemedicine`)}
                  title="Start or join telemedicine video call"
                >
                  📹 Telemedicine
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <div className={styles.content}>
        {/* Payment gates: Registration & Consultation must be paid before access */}
        {billingSummary?.payment_gates && (
          <>
            {!billingSummary.payment_gates.registration_paid && (
              <div className={styles.paymentWarning}>
                <div className={styles.warningContent}>
                  <span className={styles.warningIcon}>⚠️</span>
                  <div>
                    <h3>Registration Payment Required</h3>
                    <p>Registration must be paid before access to consultation. Collect at reception.</p>
                    {user?.role === 'RECEPTIONIST' && (
                      <p>
                        <a href="#billing-section" className={styles.paymentLink} onClick={(e) => { e.preventDefault(); document.getElementById('billing-section')?.scrollIntoView({ behavior: 'smooth' }); }}>Go to Billing →</a>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
            {billingSummary.payment_gates.registration_paid && !billingSummary.payment_gates.consultation_paid && user?.role === 'DOCTOR' && (
              <div className={styles.paymentWarning}>
                <div className={styles.warningContent}>
                  <span className={styles.warningIcon}>⚠️</span>
                  <div>
                    <h3>Consultation Payment Required</h3>
                    <p>Consultation must be paid before starting the encounter. Collect at reception.</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Consultation Section */}
        <section className={styles.section}>
          <h2>Consultation</h2>
          {consultationLock.isLocked && consultationLock.lockResult && (
            <LockIndicator 
              lockResult={consultationLock.lockResult} 
              loading={consultationLock.loading}
              variant="card"
            />
          )}
          {billingSummary?.payment_gates && !billingSummary.payment_gates.registration_paid ? (
            <div className={styles.emptyState}>
              <p>Registration payment is required before access to consultation.</p>
            </div>
          ) : billingSummary?.payment_gates && !billingSummary.payment_gates.consultation_paid && user?.role === 'DOCTOR' ? (
            <div className={styles.emptyState}>
              <p>Consultation payment is required before starting the encounter.</p>
            </div>
          ) : consultation ? (
            <div className={styles.consultationCard}>
              <div className={styles.consultationDetails}>
                {consultation.history && (
                  <div className={styles.detailItem}>
                    <label>History:</label>
                    <p>{consultation.history}</p>
                  </div>
                )}
                {consultation.examination && (
                  <div className={styles.detailItem}>
                    <label>Examination:</label>
                    <p>{consultation.examination}</p>
                  </div>
                )}
                {consultation.diagnosis && (
                  <div className={styles.detailItem}>
                    <label>Diagnosis:</label>
                    <p>{consultation.diagnosis}</p>
                  </div>
                )}
                {consultation.clinical_notes && (
                  <div className={styles.detailItem}>
                    <label>Clinical Notes:</label>
                    <p>{consultation.clinical_notes}</p>
                  </div>
                )}
                <div className={styles.consultationMeta}>
                  <span>Created: {new Date(consultation.created_at).toLocaleString()}</span>
                  {getChargeForConsultation() && (
                    <span className={styles.chargeAmount}>
                      Cost: {formatCurrency(getChargeForConsultation()!.amount)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.emptyState}>
              <p>No consultation recorded for this visit</p>
            </div>
          )}
        </section>

        {/* Admission Section - Doctor only */}
        {visit && (
          <AdmissionSection
            visitId={visit.id}
            visitStatus={visit.status}
            patientName={patient ? `${patient.first_name} ${patient.last_name}` : 'Patient'}
          />
        )}

        {/* Discharge Summary Section - Only for closed visits */}
        {visit && (
          <DischargeSummarySection
            visitId={visit.id}
            visitStatus={visit.status}
            consultation={consultation}
          />
        )}

        {/* Operation Notes Section - Doctor only */}
        {visit && user?.role === 'DOCTOR' && (
          <OperationNotes
            visitId={visit.id}
            visitStatus={visit.status}
            consultationId={consultation?.id}
            registrationPaid={billingSummary?.payment_gates?.registration_paid === true}
          />
        )}

        {/* AI Clinical Notes - Doctor only */}
        {patient && user?.role === 'DOCTOR' && billingSummary?.payment_gates?.registration_paid && (
          <section className={styles.section}>
            <h2>AI Clinical Notes</h2>
            <AINotesPanel
              patientId={patient.id}
              appointmentId={visit?.appointment ?? undefined}
              onSaved={() => loadVisitDetails()}
            />
          </section>
        )}

        {/* E-Prescription (drug interaction check) - Doctor only */}
        {patient && user?.role === 'DOCTOR' && billingSummary?.payment_gates?.registration_paid && (
          <section className={styles.section}>
            <h2>E-Prescription</h2>
            <PrescriptionModule
              patientId={patient.id}
              onSaved={() => loadVisitDetails()}
            />
          </section>
        )}

        {/* Visit Timeline - Replaces traditional tab navigation */}
        {visit && (
          <section className={styles.section}>
            <VisitTimeline visitId={visit.id} showHeader={true} />
          </section>
        )}

        {/* Paystack Return Handler */}
        {visit && visit.id && (
          <PaystackReturnHandler
            visitId={visit.id}
            onPaymentSuccess={async () => {
              await loadVisitDetails();
            }}
          />
        )}

        {/* Billing Section - Receptionist only */}
        {/* Per billing_context.md: Billing is VISIT-SCOPED and Receptionist-only */}
        {user?.role === 'RECEPTIONIST' && visit && (
          <div id="billing-section" data-testid="billing-section-wrapper">
            <BillingSection
              visitId={visit.id}
              visit={visit}
              patient={patient}
              billingSummary={billingSummary}
              hmoProviders={hmoProviders}
              onBillingUpdate={async () => {
                await loadVisitDetails();
              }}
            />
            
            {/* Invoice/Receipt Panel */}
            <div style={{ marginTop: '24px' }}>
              <InvoiceReceiptPanel
                visitId={visit.id}
                visit={visit}
              />
            </div>
          </div>
        )}

        {/* Payments Section */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Payments ({payments.length})</h2>
            {visit && (visit.payment_status === 'UNPAID' || visit.payment_status === 'PARTIALLY_PAID' || visit.payment_status === 'INSURANCE_PENDING') && user?.role === 'PATIENT' && (
              <div className={styles.paymentActions}>
                <WalletTopUpButton
                  onTopUpSuccess={() => {
                    // Reload to refresh wallet balance
                    loadVisitDetails();
                  }}
                />
                <WalletPaymentButton
                  visitId={visit.id}
                  amount={payments.reduce((sum, p) => sum + parseFloat(p.amount.toString()), 0) || 1000}
                  onPaymentSuccess={() => {
                    // Reload visit details to update payment status
                    loadVisitDetails();
                  }}
                />
              </div>
            )}
          </div>
          {payments.length > 0 ? (
            <div className={styles.ordersList}>
              {payments.map((payment) => (
                <div key={payment.id} className={styles.orderCard}>
                  <div className={styles.orderHeader}>
                    <h3>Payment #{payment.id}</h3>
                    <span className={`${styles.statusBadge} ${payment.status === 'CLEARED' ? styles.paymentCleared : styles.paymentPending}`}>
                      {payment.status}
                    </span>
                  </div>
                  <div className={styles.orderDetails}>
                    <p><strong>Amount:</strong> {payment.amount}</p>
                    <p><strong>Method:</strong> {payment.payment_method}</p>
                    {payment.transaction_reference && (
                      <p><strong>Reference:</strong> {payment.transaction_reference}</p>
                    )}
                    {payment.notes && <p><strong>Notes:</strong> {payment.notes}</p>}
                    {payment.processed_by_name && (
                      <p><strong>Processed By:</strong> {payment.processed_by_name}</p>
                    )}
                    <p><strong>Created:</strong> {new Date(payment.created_at).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>
              <p>No payments recorded for this visit</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
