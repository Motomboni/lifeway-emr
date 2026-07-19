/**
 * Main App Component
 * Sets up React Router and authentication context.
 * Per EMR Rules: All routes are protected except login.
 */
import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { APP_NAME, APP_SHORT_NAME } from './config/branding';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OrganizationProvider } from './contexts/OrganizationContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { GuideProvider } from './contexts/GuideContext';
import { GuidePageProvider } from './contexts/GuidePageContext';
import { ThemeProvider } from './contexts/ThemeContext';
import GuideShell from './components/guide/GuideShell';
import ProtectedRoute from './components/routing/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoadingSpinner from './components/common/LoadingSpinner';
import OfflineIndicator from './components/common/OfflineIndicator';
import { useOffline } from './hooks/useOffline';
import './styles/theme.css';
import './styles/glass.css';
import './styles/responsive.css';
import './styles/dark-mode-overrides.css';
import './styles/typography-contrast.css';
import './styles/dashboard-contrast.css';
import './styles/content-surfaces.css';
import './styles/surface-contrast.css';
import './styles/page-chrome.css';
import './styles/register-chrome.css';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import BiometricLoginPage from './pages/BiometricLoginPage';
import OTPLogin from './pages/OTPLogin';
import DashboardPage from './pages/DashboardPage';
import ConsultationPage from './pages/ConsultationPage';
import NurseVisitPage from './pages/NurseVisitPage';
import PatientRegistrationPage from './pages/PatientRegistrationPage';
import CreateVisitPage from './pages/CreateVisitPage';
import VisitsListPage from './pages/VisitsListPage';
import LabOrdersPage from './pages/LabOrdersPage';
import RadiologyOrdersPage from './pages/RadiologyOrdersPage';
import RadiologyUploadStatusPage from './pages/RadiologyUploadStatusPage';
import PrescriptionsPage from './pages/PrescriptionsPage';
import DrugCatalogInventoryPage from './pages/DrugCatalogInventoryPage';
import LabTestCatalogPage from './pages/LabTestCatalogPage';
import RadiologyStudyTypesPage from './pages/RadiologyStudyTypesPage';
import PaymentProcessingPage from './pages/PaymentProcessingPage';
import BillingPendingQueuePage from './pages/BillingPendingQueuePage';
import DeferredPaymentsPage from './pages/DeferredPaymentsPage';
import InsuranceClaimsDashboard from './components/billing/InsuranceClaimsDashboard';
import PatientManagementPage from './pages/PatientManagementPage';
import PatientVerificationPage from './pages/PatientVerificationPage';
import VisitDetailsPage from './pages/VisitDetailsPage';
import InpatientsPage from './pages/InpatientsPage';
import AuditLogPage from './pages/AuditLogPage';
import HealthStatusPage from './pages/HealthStatusPage';
import ReportsPage from './pages/ReportsPage';
import BackupPage from './pages/BackupPage';
import StaffApprovalPage from './pages/StaffApprovalPage';
import OrganizationSettingsPage from './pages/OrganizationSettingsPage';
import ServiceCatalogPage from './pages/ServiceCatalogPage';
import TelemedicinePage from './pages/TelemedicinePage';
import TelemedicineRoomPage from './pages/TelemedicineRoomPage';
import EndOfDayReconciliationPage from './pages/EndOfDayReconciliationPage';
import RevenueLeakDashboardPage from './pages/RevenueLeakDashboardPage';
import NHIAComplianceDashboardPage from './pages/NHIAComplianceDashboardPage';
import OfflineClinicQueuePage from './pages/OfflineClinicQueuePage';
import NafdacFormularyPage from './pages/NafdacFormularyPage';
import ImmunizationSchedulePage from './pages/ImmunizationSchedulePage';
import BankTransferReconciliationPage from './pages/BankTransferReconciliationPage';
import IntegrationHubsPage from './pages/IntegrationHubsPage';
import MedicalHistoryPage from './pages/MedicalHistoryPage';
import AppointmentsPage from './pages/AppointmentsPage';
import PatientPortalDashboard from './pages/PatientPortalDashboard';
import PatientPortalVisitsPage from './pages/PatientPortalVisitsPage';
import PatientPortalVisitDetailPage from './pages/PatientPortalVisitDetailPage';
import PatientPortalAppointmentsPage from './pages/PatientPortalAppointmentsPage';
import PatientPortalLabResultsPage from './pages/PatientPortalLabResultsPage';
import PatientPortalRadiologyResultsPage from './pages/PatientPortalRadiologyResultsPage';
import PatientPortalPrescriptionsPage from './pages/PatientPortalPrescriptionsPage';
import PatientPortalMedicalHistoryPage from './pages/PatientPortalMedicalHistoryPage';
import PatientPortalImmunizationsPage from './pages/PatientPortalImmunizationsPage';
import PatientPortalTelemedicinePage from './pages/PatientPortalTelemedicinePage';
import WalletPage from './pages/WalletPage';
import WalletCallbackPage from './pages/WalletCallbackPage';
import NotFoundPage from './pages/NotFoundPage';
import IVFDashboardPage from './pages/IVFDashboardPage';
import IVFCyclesListPage from './pages/IVFCyclesListPage';
import IVFCycleDetailPage from './pages/IVFCycleDetailPage';
import IVFCycleNewPage from './pages/IVFCycleNewPage';
import IVFPatientsPage from './pages/IVFPatientsPage';
import IVFVisitsPage from './pages/IVFVisitsPage';
import SpermAnalysesPage from './pages/SpermAnalysesPage';
import SpermAnalysisDetailPage from './pages/SpermAnalysisDetailPage';
import EmbryoInventoryPage from './pages/EmbryoInventoryPage';
import IVFReportsPage from './pages/IVFReportsPage';
import IVFStimulationMonitoringPage from './pages/IVFStimulationMonitoringPage';
import IVFMedicationAdminPage from './pages/IVFMedicationAdminPage';
import AntenatalDashboardPage from './pages/AntenatalDashboardPage';
import AntenatalRecordNewPage from './pages/AntenatalRecordNewPage';
import AntenatalRecordDetailPage from './pages/AntenatalRecordDetailPage';

/**
 * Wrapper component to extract visitId from URL params
 */
function ConsultationPageWrapper() {
  const { visitId } = useParams<{ visitId: string }>();

  if (!visitId) {
    return <div>Visit ID is required</div>;
  }

  return <ConsultationPage visitId={visitId} />;
}

/**
 * Wrapper component for Nurse Visit Page
 */
function NurseVisitPageWrapper() {
  const { visitId } = useParams<{ visitId: string }>();

  if (!visitId) {
    return <div>Visit ID is required</div>;
  }

  return <NurseVisitPage />;
}

function AppRoutes() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const isOffline = useOffline();

  // Show loading while checking authentication
  if (isLoading) {
    return <LoadingSpinner message="Initializing..." size="large" />;
  }

  return (
    <>
      {isOffline && <OfflineIndicator />}
      <Suspense fallback={<LoadingSpinner message="Loading..." size="large" />}>
        <Routes>
          {/* Public routes */}
          <Route
            path="/"
            element={
              isAuthenticated ? (
                <Navigate
                  to={user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard'}
                  replace
                />
              ) : (
                <LandingPage />
              )
            }
          />
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate
                  to={user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard'}
                  replace
                />
              ) : (
                <LoginPage />
              )
            }
          />
          <Route
            path="/register"
            element={
              isAuthenticated ? (
                <Navigate
                  to={user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard'}
                  replace
                />
              ) : (
                <RegisterPage />
              )
            }
          />
          <Route path="/biometric-login" element={<BiometricLoginPage />} />
          <Route path="/otp-login" element={<OTPLogin />} />

          {/* Protected routes — staff only (patients use patient portal) */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute staffOnly>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Patient Registration - Receptionist only */}
          <Route
            path="/patients/register"
            element={
              <ProtectedRoute requiredRole={['RECEPTIONIST', 'ADMIN'] as any}>
                <PatientRegistrationPage />
              </ProtectedRoute>
            }
          />

          {/* Visits List - Staff only */}
          <Route
            path="/visits"
            element={
              <ProtectedRoute staffOnly>
                <VisitsListPage />
              </ProtectedRoute>
            }
          />

          {/* Create Visit - Receptionist and Admin */}
          <Route
            path="/visits/new"
            element={
              <ProtectedRoute staffOnly requiredRole={['RECEPTIONIST', 'ADMIN']}>
                <CreateVisitPage />
              </ProtectedRoute>
            }
          />

          {/* Consultation route - Doctor only */}
          <Route
            path="/visits/:visitId/consultation"
            element={
              <ProtectedRoute requiredRole="DOCTOR">
                <ConsultationPageWrapper />
              </ProtectedRoute>
            }
          />

          {/* Nurse Visit route - Nurse only */}
          <Route
            path="/visits/:visitId/nursing"
            element={
              <ProtectedRoute requiredRole="NURSE">
                <NurseVisitPageWrapper />
              </ProtectedRoute>
            }
          />

          {/* Telemedicine virtual clinic — host doctors + invited clinical staff */}
          <Route
            path="/visits/:visitId/telemedicine"
            element={
              <ProtectedRoute
                requiredRole={[
                  'DOCTOR',
                  'NURSE',
                  'LAB_TECH',
                  'RADIOLOGY_TECH',
                  'PHARMACIST',
                  'ADMIN',
                  'IVF_SPECIALIST',
                  'EMBRYOLOGIST',
                ]}
              >
                <TelemedicinePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/telemedicine"
            element={
              <ProtectedRoute
                requiredRole={[
                  'DOCTOR',
                  'NURSE',
                  'LAB_TECH',
                  'RADIOLOGY_TECH',
                  'PHARMACIST',
                  'ADMIN',
                  'IVF_SPECIALIST',
                  'EMBRYOLOGIST',
                ]}
              >
                <TelemedicinePage />
              </ProtectedRoute>
            }
          />

          {/* Direct meeting room link (doctor, patient, or invited staff) */}
          <Route
            path="/telemedicine/room/:sessionId"
            element={
              <ProtectedRoute
                requiredRole={[
                  'DOCTOR',
                  'PATIENT',
                  'NURSE',
                  'LAB_TECH',
                  'RADIOLOGY_TECH',
                  'PHARMACIST',
                  'ADMIN',
                  'IVF_SPECIALIST',
                  'EMBRYOLOGIST',
                ]}
              >
                <TelemedicineRoomPage />
              </ProtectedRoute>
            }
          />

          {/* Lab Orders - Lab Tech and Admin */}
          <Route
            path="/lab-orders"
            element={
              <ProtectedRoute staffOnly requiredRole={['LAB_TECH', 'ADMIN']}>
                <LabOrdersPage />
              </ProtectedRoute>
            }
          />

          {/* Radiology Orders - Radiology Tech only */}
          <Route
            path="/radiology-orders"
            element={
              <ProtectedRoute requiredRole="RADIOLOGY_TECH">
                <RadiologyOrdersPage />
              </ProtectedRoute>
            }
          />

          {/* Radiology Upload Status - Radiology Tech and Admin */}
          <Route
            path="/radiology/upload-status"
            element={
              <ProtectedRoute>
                <RadiologyUploadStatusPage />
              </ProtectedRoute>
            }
          />

          {/* Prescriptions - Pharmacist only */}
          <Route
            path="/prescriptions"
            element={
              <ProtectedRoute requiredRole="PHARMACIST">
                <PrescriptionsPage />
              </ProtectedRoute>
            }
          />

          {/* Drug Catalog & Inventory - Pharmacist only (merged) */}
          <Route
            path="/drugs"
            element={
              <ProtectedRoute requiredRole="PHARMACIST">
                <DrugCatalogInventoryPage />
              </ProtectedRoute>
            }
          />

          {/* Redirect /inventory → /drugs (merged single page) */}
          <Route path="/inventory" element={<Navigate to="/drugs" replace />} />

          {/* Lab Test Catalog - Doctor, Lab Tech, Admin */}
          <Route
            path="/lab-test-catalog"
            element={
              <ProtectedRoute staffOnly requiredRole={['DOCTOR', 'LAB_TECH', 'ADMIN'] as any}>
                <LabTestCatalogPage />
              </ProtectedRoute>
            }
          />

          {/* Radiology Study Types Catalog - Doctor, Radiology Tech, Admin */}
          <Route
            path="/radiology-study-types"
            element={
              <ProtectedRoute staffOnly requiredRole={['DOCTOR', 'RADIOLOGY_TECH', 'ADMIN'] as any}>
                <RadiologyStudyTypesPage />
              </ProtectedRoute>
            }
          />

          {/* Payment Processing - Receptionist only */}
          <Route
            path="/payments"
            element={
              <ProtectedRoute requiredRole="RECEPTIONIST">
                <PaymentProcessingPage />
              </ProtectedRoute>
            }
          />

          {/* Central Billing Queue (Pending Payments) - Receptionist only */}
          <Route
            path="/billing/pending-queue"
            element={
              <ProtectedRoute requiredRole="RECEPTIONIST">
                <BillingPendingQueuePage />
              </ProtectedRoute>
            }
          />

          {/* Deferred legacy payments - Receptionist only */}
          <Route
            path="/billing/deferred-payments"
            element={
              <ProtectedRoute requiredRole="RECEPTIONIST">
                <DeferredPaymentsPage />
              </ProtectedRoute>
            }
          />

          {/* Insurance Claims (create, submit, track) - Billing staff only */}
          <Route
            path="/billing/claims"
            element={
              <ProtectedRoute requiredRole={['RECEPTIONIST', 'ADMIN']}>
                <InsuranceClaimsDashboard />
              </ProtectedRoute>
            }
          />

          {/* Appointments - Clinical staff */}
          <Route
            path="/appointments"
            element={
              <ProtectedRoute staffOnly>
                <AppointmentsPage />
              </ProtectedRoute>
            }
          />

          {/* Patient Management - Staff only */}
          <Route
            path="/patients"
            element={
              <ProtectedRoute staffOnly>
                <PatientManagementPage />
              </ProtectedRoute>
            }
          />

          {/* Patient Verification - Receptionist only */}
          <Route
            path="/patients/verification"
            element={
              <ProtectedRoute requiredRole="RECEPTIONIST">
                <PatientVerificationPage />
              </ProtectedRoute>
            }
          />

          {/* Visit Details - Staff only */}
          <Route
            path="/visits/:visitId"
            element={
              <ProtectedRoute staffOnly>
                <VisitDetailsPage />
              </ProtectedRoute>
            }
          />

          {/* Inpatients List - Staff only */}
          <Route
            path="/inpatients"
            element={
              <ProtectedRoute staffOnly>
                <InpatientsPage />
              </ProtectedRoute>
            }
          />

          {/* Audit Logs - Admin only */}
          <Route
            path="/audit-logs"
            element={
              <ProtectedRoute requireAdmin>
                <AuditLogPage />
              </ProtectedRoute>
            }
          />

          {/* Health Status - Admin only */}
          <Route
            path="/health"
            element={
              <ProtectedRoute requireAdmin>
                <HealthStatusPage />
              </ProtectedRoute>
            }
          />

          {/* Staff Approval - Admin only */}
          <Route
            path="/staff-approval"
            element={
              <ProtectedRoute requireAdmin>
                <StaffApprovalPage />
              </ProtectedRoute>
            }
          />

          {/* Clinic settings — single-tenant Lifeway */}
          <Route
            path="/organization/settings"
            element={
              <ProtectedRoute requireAdmin>
                <OrganizationSettingsPage />
              </ProtectedRoute>
            }
          />

          {/* Backup & Restore - Admin only */}
          <Route
            path="/backups"
            element={
              <ProtectedRoute requireAdmin>
                <BackupPage />
              </ProtectedRoute>
            }
          />

          {/* Service Catalog - Admin only */}
          <Route
            path="/service-catalog"
            element={
              <ProtectedRoute requireAdmin>
                <ServiceCatalogPage />
              </ProtectedRoute>
            }
          />

          {/* Reports & Analytics - Admin only */}
          <Route
            path="/reports"
            element={
              <ProtectedRoute requireAdmin>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          {/* End-of-Day Reconciliation - Admin and Receptionist */}
          <Route
            path="/reconciliation"
            element={
              <ProtectedRoute staffOnly>
                <EndOfDayReconciliationPage />
              </ProtectedRoute>
            }
          />

          {/* Revenue Leak Detection - Admin only */}
          <Route
            path="/billing/revenue-leaks"
            element={
              <ProtectedRoute staffOnly requireAdmin>
                <RevenueLeakDashboardPage />
              </ProtectedRoute>
            }
          />

          {/* NHIA Compliance Dashboard - Admin only */}
          <Route
            path="/billing/nhia-compliance"
            element={
              <ProtectedRoute staffOnly requireAdmin>
                <NHIAComplianceDashboardPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/offline/queue"
            element={
              <ProtectedRoute staffOnly>
                <OfflineClinicQueuePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/pharmacy/nafdac-formulary"
            element={
              <ProtectedRoute staffOnly>
                <NafdacFormularyPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/clinical/immunizations"
            element={
              <ProtectedRoute staffOnly>
                <ImmunizationSchedulePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/billing/payment-reconciliation"
            element={
              <ProtectedRoute staffOnly>
                <BankTransferReconciliationPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/integrations"
            element={
              <ProtectedRoute requireAdmin>
                <IntegrationHubsPage />
              </ProtectedRoute>
            }
          />

          {/* Medical History - Staff only */}
          <Route
            path="/patients/:patientId/history"
            element={
              <ProtectedRoute staffOnly>
                <MedicalHistoryPage />
              </ProtectedRoute>
            }
          />

          {/* Patient portal index redirect */}
          <Route
            path="/patient-portal"
            element={<Navigate to="/patient-portal/dashboard" replace />}
          />

          {/* Patient Portal Routes - Patients only */}
          <Route
            path="/patient-portal/dashboard"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/visits"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalVisitsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/visits/:visitId"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalVisitDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/appointments"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalAppointmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/lab-results"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalLabResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/radiology-results"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalRadiologyResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/prescriptions"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalPrescriptionsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/medical-history"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalMedicalHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/immunizations"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalImmunizationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient-portal/telemedicine"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <PatientPortalTelemedicinePage />
              </ProtectedRoute>
            }
          />

          {/* Wallet - Patients (own wallet) and Receptionists (lookup) */}
          <Route
            path="/wallet"
            element={
              <ProtectedRoute requiredRole={['PATIENT', 'RECEPTIONIST', 'ADMIN'] as any}>
                <WalletPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/wallet/callback"
            element={
              <ProtectedRoute requiredRole="PATIENT">
                <WalletCallbackPage />
              </ProtectedRoute>
            }
          />

          {/* IVF Module Routes - IVF_SPECIALIST, EMBRYOLOGIST, NURSE, and DOCTOR */}
          <Route
            path="/ivf"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE', 'ADMIN', 'DOCTOR'] as any}>
                <IVFDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/cycles"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE', 'ADMIN', 'DOCTOR'] as any}>
                <IVFCyclesListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/cycles/new"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'ADMIN'] as any}>
                <IVFCycleNewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/cycles/:cycleId"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE', 'ADMIN', 'DOCTOR'] as any}>
                <IVFCycleDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/patients"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE', 'ADMIN', 'DOCTOR'] as any}>
                <IVFPatientsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/visits"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE', 'ADMIN', 'DOCTOR'] as any}>
                <IVFVisitsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/sperm-analyses"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'ADMIN', 'DOCTOR'] as any}>
                <SpermAnalysesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/sperm-analyses/:id"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'ADMIN', 'DOCTOR'] as any}>
                <SpermAnalysisDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/embryo-inventory"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'EMBRYOLOGIST', 'ADMIN'] as any}>
                <EmbryoInventoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/reports"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'ADMIN'] as any}>
                <IVFReportsPage />
              </ProtectedRoute>
            }
          />
          {/* Nurse-focused IVF routes */}
          <Route
            path="/ivf/cycles/:cycleId/stimulation"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'NURSE', 'ADMIN'] as any}>
                <IVFStimulationMonitoringPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ivf/cycles/:cycleId/medications"
            element={
              <ProtectedRoute requiredRole={['IVF_SPECIALIST', 'NURSE', 'ADMIN'] as any}>
                <IVFMedicationAdminPage />
              </ProtectedRoute>
            }
          />

          {/* Antenatal Clinic Management Routes - DOCTOR, NURSE, and ADMIN */}
          <Route
            path="/antenatal"
            element={
              <ProtectedRoute requiredRole={['DOCTOR', 'NURSE', 'ADMIN'] as any}>
                <AntenatalDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/antenatal/records"
            element={
              <ProtectedRoute requiredRole={['DOCTOR', 'NURSE', 'ADMIN'] as any}>
                <AntenatalDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/antenatal/records/new"
            element={
              <ProtectedRoute requiredRole={['DOCTOR', 'ADMIN'] as any}>
                <AntenatalRecordNewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/antenatal/records/:recordId"
            element={
              <ProtectedRoute requiredRole={['DOCTOR', 'NURSE', 'ADMIN'] as any}>
                <AntenatalRecordDetailPage />
              </ProtectedRoute>
            }
          />

          {/* 404 Not Found */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </>
  );
}

function App() {
  useEffect(() => {
    document.title = `${APP_NAME} - ${APP_SHORT_NAME}`;
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <ThemeProvider>
          <AuthProvider>
            <OrganizationProvider>
              <NotificationProvider>
                <GuidePageProvider>
                  <GuideProvider>
                    <AppRoutes />
                    <GuideShell />
                  </GuideProvider>
                </GuidePageProvider>
              </NotificationProvider>
            </OrganizationProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
