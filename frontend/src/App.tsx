/**
 * Main App Component
 * Sets up React Router and authentication context.
 * Per EMR Rules: All routes are protected except login.
 */
import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ProtectedRoute from './components/routing/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoadingSpinner from './components/common/LoadingSpinner';
import OfflineIndicator from './components/common/OfflineIndicator';
import { useOffline } from './hooks/useOffline';
import './styles/theme.css';
import './styles/responsive.css';
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
import ServiceCatalogPage from './pages/ServiceCatalogPage';
import TelemedicinePage from './pages/TelemedicinePage';
import EndOfDayReconciliationPage from './pages/EndOfDayReconciliationPage';
import RevenueLeakDashboardPage from './pages/RevenueLeakDashboardPage';
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
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />
        } 
      />
      <Route path="/biometric-login" element={<BiometricLoginPage />} />
      <Route path="/otp-login" element={<OTPLogin />} />

      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
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

      {/* Visits List - All authenticated users */}
      <Route
        path="/visits"
        element={
          <ProtectedRoute>
            <VisitsListPage />
          </ProtectedRoute>
        }
      />

      {/* Create Visit - Receptionist */}
      <Route
        path="/visits/new"
        element={
          <ProtectedRoute>
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

      {/* Telemedicine - Doctor only */}
      <Route
        path="/visits/:visitId/telemedicine"
        element={
          <ProtectedRoute requiredRole="DOCTOR">
            <TelemedicinePage />
          </ProtectedRoute>
        }
      />
      
      {/* Telemedicine (without visit) - Doctor only */}
      <Route
        path="/telemedicine"
        element={
          <ProtectedRoute requiredRole="DOCTOR">
            <TelemedicinePage />
          </ProtectedRoute>
        }
      />

      {/* Lab Orders - Lab Tech only */}
      <Route
        path="/lab-orders"
        element={
          <ProtectedRoute requiredRole="LAB_TECH">
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

      {/* Redirect /inventory to /drugs for backward compatibility */}
      <Route
        path="/inventory"
        element={
          <ProtectedRoute requiredRole="PHARMACIST">
            <DrugCatalogInventoryPage />
          </ProtectedRoute>
        }
      />

      {/* Lab Test Catalog - Doctor and Lab Tech */}
      <Route
        path="/lab-test-catalog"
        element={
          <ProtectedRoute>
            <LabTestCatalogPage />
          </ProtectedRoute>
        }
      />

      {/* Radiology Study Types Catalog - Doctor and Radiology Tech */}
      <Route
        path="/radiology-study-types"
        element={
          <ProtectedRoute>
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

      {/* Insurance Claims (create, submit, track) - Billing staff only */}
      <Route
        path="/billing/claims"
        element={
          <ProtectedRoute requiredRole={['RECEPTIONIST', 'ADMIN']}>
            <InsuranceClaimsDashboard />
          </ProtectedRoute>
        }
      />

      {/* Appointments - Receptionist and Doctor */}
      <Route
        path="/appointments"
        element={
          <ProtectedRoute>
            <AppointmentsPage />
          </ProtectedRoute>
        }
      />

      {/* Patient Management - All authenticated users */}
      <Route
        path="/patients"
        element={
          <ProtectedRoute>
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

      {/* Visit Details - All authenticated users */}
      <Route
        path="/visits/:visitId"
        element={
          <ProtectedRoute>
            <VisitDetailsPage />
          </ProtectedRoute>
        }
      />

      {/* Inpatients List - All authenticated users */}
      <Route
        path="/inpatients"
        element={
          <ProtectedRoute>
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
            <ProtectedRoute>
              <EndOfDayReconciliationPage />
            </ProtectedRoute>
          }
        />

        {/* Revenue Leak Detection - Admin and Management only */}
        <Route
          path="/billing/revenue-leaks"
          element={
            <ProtectedRoute>
              <RevenueLeakDashboardPage />
            </ProtectedRoute>
          }
        />

      {/* Medical History - All authenticated users */}
      <Route
        path="/patients/:patientId/history"
        element={
          <ProtectedRoute>
            <MedicalHistoryPage />
          </ProtectedRoute>
        }
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
        path="/patient-portal/telemedicine"
        element={
          <ProtectedRoute requiredRole="PATIENT">
            <PatientPortalTelemedicinePage />
          </ProtectedRoute>
        }
      />

      {/* Wallet - Patients and Receptionists */}
      <Route
        path="/wallet"
        element={
          <ProtectedRoute requiredRole="PATIENT">
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
            <NotificationProvider>
              <AppRoutes />
            </NotificationProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
