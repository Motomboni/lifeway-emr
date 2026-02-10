/**
 * Code Splitting Utilities
 *
 * Lazy-loads route pages to reduce initial bundle size and improve TTI.
 */
import { lazy, ComponentType } from 'react';

// Core / high-traffic pages (lazy)
export const LazyDashboardPage = lazy(() => import('../pages/DashboardPage'));
export const LazyConsultationPage = lazy(() => import('../pages/ConsultationPage'));
export const LazyNurseVisitPage = lazy(() => import('../pages/NurseVisitPage'));
export const LazyVisitDetailsPage = lazy(() => import('../pages/VisitDetailsPage'));
export const LazyVisitsListPage = lazy(() => import('../pages/VisitsListPage'));
export const LazyCreateVisitPage = lazy(() => import('../pages/CreateVisitPage'));
export const LazyPatientRegistrationPage = lazy(() => import('../pages/PatientRegistrationPage'));
export const LazyPatientManagementPage = lazy(() => import('../pages/PatientManagementPage'));
export const LazyPatientVerificationPage = lazy(() => import('../pages/PatientVerificationPage'));
export const LazyLabOrdersPage = lazy(() => import('../pages/LabOrdersPage'));
export const LazyRadiologyOrdersPage = lazy(() => import('../pages/RadiologyOrdersPage'));
export const LazyRadiologyUploadStatusPage = lazy(() => import('../pages/RadiologyUploadStatusPage'));
export const LazyPrescriptionsPage = lazy(() => import('../pages/PrescriptionsPage'));
export const LazyDrugsPage = lazy(() => import('../pages/DrugsPage'));
export const LazyInventoryPage = lazy(() => import('../pages/InventoryPage'));
export const LazyLabTestCatalogPage = lazy(() => import('../pages/LabTestCatalogPage'));
export const LazyRadiologyStudyTypesPage = lazy(() => import('../pages/RadiologyStudyTypesPage'));
export const LazyPaymentProcessingPage = lazy(() => import('../pages/PaymentProcessingPage'));
export const LazyAppointmentsPage = lazy(() => import('../pages/AppointmentsPage'));
export const LazyInpatientsPage = lazy(() => import('../pages/InpatientsPage'));
export const LazyMedicalHistoryPage = lazy(() => import('../pages/MedicalHistoryPage'));
export const LazyAuditLogPage = lazy(() => import('../pages/AuditLogPage'));
export const LazyHealthStatusPage = lazy(() => import('../pages/HealthStatusPage'));
export const LazyReportsPage = lazy(() => import('../pages/ReportsPage'));
export const LazyBackupPage = lazy(() => import('../pages/BackupPage'));
export const LazyTelemedicinePage = lazy(() => import('../pages/TelemedicinePage'));
export const LazyEndOfDayReconciliationPage = lazy(() => import('../pages/EndOfDayReconciliationPage'));
export const LazyRevenueLeakDashboardPage = lazy(() => import('../pages/RevenueLeakDashboardPage'));
// Patient portal
export const LazyPatientPortalDashboard = lazy(() => import('../pages/PatientPortalDashboard'));
export const LazyPatientPortalVisitsPage = lazy(() => import('../pages/PatientPortalVisitsPage'));
export const LazyPatientPortalVisitDetailPage = lazy(() => import('../pages/PatientPortalVisitDetailPage'));
export const LazyPatientPortalAppointmentsPage = lazy(() => import('../pages/PatientPortalAppointmentsPage'));
export const LazyPatientPortalLabResultsPage = lazy(() => import('../pages/PatientPortalLabResultsPage'));
export const LazyPatientPortalRadiologyResultsPage = lazy(() => import('../pages/PatientPortalRadiologyResultsPage'));
export const LazyPatientPortalPrescriptionsPage = lazy(() => import('../pages/PatientPortalPrescriptionsPage'));
export const LazyPatientPortalMedicalHistoryPage = lazy(() => import('../pages/PatientPortalMedicalHistoryPage'));
export const LazyPatientPortalTelemedicinePage = lazy(() => import('../pages/PatientPortalTelemedicinePage'));
export const LazyWalletPage = lazy(() => import('../pages/WalletPage'));
export const LazyWalletCallbackPage = lazy(() => import('../pages/WalletCallbackPage'));
// IVF
export const LazyIVFDashboardPage = lazy(() => import('../pages/IVFDashboardPage'));
export const LazyIVFCyclesListPage = lazy(() => import('../pages/IVFCyclesListPage'));
export const LazyIVFCycleDetailPage = lazy(() => import('../pages/IVFCycleDetailPage'));
export const LazyIVFCycleNewPage = lazy(() => import('../pages/IVFCycleNewPage'));
export const LazySpermAnalysesPage = lazy(() => import('../pages/SpermAnalysesPage'));
export const LazyEmbryoInventoryPage = lazy(() => import('../pages/EmbryoInventoryPage'));
export const LazyIVFReportsPage = lazy(() => import('../pages/IVFReportsPage'));
export const LazyIVFStimulationMonitoringPage = lazy(() => import('../pages/IVFStimulationMonitoringPage'));
export const LazyIVFMedicationAdminPage = lazy(() => import('../pages/IVFMedicationAdminPage'));
// Antenatal
export const LazyAntenatalDashboardPage = lazy(() => import('../pages/AntenatalDashboardPage'));
export const LazyAntenatalRecordNewPage = lazy(() => import('../pages/AntenatalRecordNewPage'));
export const LazyAntenatalRecordDetailPage = lazy(() => import('../pages/AntenatalRecordDetailPage'));
// 404 (lazy so main bundle stays small)
export const LazyNotFoundPage = lazy(() => import('../pages/NotFoundPage'));

/** Preload a component for faster navigation */
export function preloadComponent(componentLoader: () => Promise<{ default: ComponentType<unknown> }>): void {
  componentLoader();
}
