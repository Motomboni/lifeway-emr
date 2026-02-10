/**
 * ServiceCatalogInline Component
 * 
 * Inline component for doctors to order services from the catalog.
 * 
 * Per EMR Rules:
 * - Visit-scoped: Requires visitId
 * - Doctor: Can order services from catalog
 * - Services ordered by doctors will reflect in patient's account in Receptionist dashboard
 * - Automatic billing: Services are automatically added to bill with correct prices
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import { Visit, getVisit } from '../../api/visits';
import { Service, addServiceToBill } from '../../api/billing';
import ServiceSearchInput from '../billing/ServiceSearchInput';
import LockIndicator from '../locks/LockIndicator';
import { useActionLock } from '../../hooks/useActionLock';
import { evaluateLock } from '../../api/locks';
import PrescriptionDetailsForm, { PrescriptionDetails } from '../pharmacy/PrescriptionDetailsForm';
import LabOrderDetailsForm, { LabOrderDetails } from '../laboratory/LabOrderDetailsForm';
import RadiologyOrderDetailsForm, { RadiologyOrderDetails } from '../radiology/RadiologyOrderDetailsForm';
import { logger } from '../../utils/logger';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ServiceCatalogInlineProps {
  visitId: string;
  onServiceAdded?: () => void;
}

const ALREADY_ADDED_MSG =
  'This service has already been added to the bill for this visit. Each service can only be added once per visit.';

/** Flatten backend detail (may be array, nested array, or JSON string) into one string for matching. */
function flattenDetail(detail: any): string {
  if (detail == null) return '';
  if (typeof detail === 'string') {
    try {
      const parsed = JSON.parse(detail);
      return Array.isArray(parsed) ? parsed.map(flattenDetail).join(' ') : String(parsed);
    } catch {
      return detail;
    }
  }
  if (Array.isArray(detail)) {
    return detail.map(flattenDetail).join(' ');
  }
  return String(detail);
}

/** User-friendly message when billing add-item returns "already exists" for same service/visit. */
function getAddServiceErrorMessage(error: any, fallback: string): string {
  const msg = typeof error?.message === 'string' ? error.message : '';
  const data = error?.responseData ?? error?.response?.data;
  // Backend may return { detail: [...] } or a raw array as the response body
  const rawDetail = data?.detail ?? (Array.isArray(data) ? data : undefined);
  const backendMsg = rawDetail != null ? flattenDetail(rawDetail) : msg;
  const hasAlreadyExists = (s: string) =>
    s.includes('already exists') || s.includes('one billing line item per visit');
  const isAlreadyExists = hasAlreadyExists(backendMsg) || (rawDetail != null && hasAlreadyExists(JSON.stringify(rawDetail)));
  return isAlreadyExists ? ALREADY_ADDED_MSG : (backendMsg || fallback);
}

export default function ServiceCatalogInline({ 
  visitId, 
  onServiceAdded 
}: ServiceCatalogInlineProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [visit, setVisit] = useState<Visit | null>(null);
  const [loading, setLoading] = useState(true);
  const [showServiceSearch, setShowServiceSearch] = useState(false);
  const [addingService, setAddingService] = useState(false);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [showPrescriptionForm, setShowPrescriptionForm] = useState(false);
  const [showLabOrderForm, setShowLabOrderForm] = useState(false);
  const [showRadiologyOrderForm, setShowRadiologyOrderForm] = useState(false);

  // Load visit data
  useEffect(() => {
    const loadVisit = async () => {
      try {
        const visitData = await getVisit(parseInt(visitId));
        setVisit(visitData);
      } catch (error) {
        console.error('Failed to load visit:', error);
        showError('Failed to load visit details');
      } finally {
        setLoading(false);
      }
    };
    loadVisit();
  }, [visitId, showError]);

  // Only show for doctors
  if (user?.role !== 'DOCTOR') {
    return null;
  }

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Order Services from Catalog</h3>
        <p>Loading...</p>
      </div>
    );
  }

  if (!visit) {
    return null;
  }

  // Don't show if visit is closed
  if (visit.status === 'CLOSED') {
    return null;
  }

  const handleServiceSelect = async (service: Service) => {
    if (visit.status === 'CLOSED') {
      showError('Cannot add services to a closed visit');
      return;
    }

    // If it's a PHARMACY service, show prescription details form
    if (service.department === 'PHARMACY') {
      setSelectedService(service);
      setShowServiceSearch(false);
      setShowPrescriptionForm(true);
      return;
    }

    // If it's a LAB service, show lab order details form
    if (service.department === 'LAB') {
      setSelectedService(service);
      setShowServiceSearch(false);
      setShowLabOrderForm(true);
      return;
    }

    // If it's a RADIOLOGY_STUDY service (Service Catalog → RadiologyRequest flow), show radiology order details form
    if (service.workflow_type === 'RADIOLOGY_STUDY' || service.department === 'RADIOLOGY') {
      setSelectedService(service);
      setShowServiceSearch(false);
      setShowRadiologyOrderForm(true);
      return;
    }

    // For PROCEDURE services, check lock before ordering
    if (service.department === 'PROCEDURE' || service.workflow_type === 'PROCEDURE') {
      // Check procedure lock (consultation_id is optional for procedures)
      try {
        const lockResult = await evaluateLock('procedure', { visit_id: parseInt(visitId) });
        
        if (lockResult.is_locked) {
          showError(lockResult.human_readable_message);
          return;
        }
      } catch {
        // If lock check fails, still allow the order (fail open for now)
      }
    }

    // For other services (PROCEDURE, etc.), order directly
    try {
      setAddingService(true);
      await addServiceToBill({
        visit_id: parseInt(visitId),
        department: service.department,
        service_code: service.service_code,
      });
      showSuccess(`${service.service_name} ordered and added to patient's account`);
      
      // Close the service search after successful addition
      setShowServiceSearch(false);
      
      // Notify parent component to refresh data if needed
      if (onServiceAdded) {
        onServiceAdded();
      }
    } catch (error: any) {
      const message = getAddServiceErrorMessage(error, `Failed to order ${service.service_name}`);
      showError(message);
      if (message !== ALREADY_ADDED_MSG) console.error('Error ordering service:', error);
    } finally {
      setAddingService(false);
    }
  };

  const handlePrescriptionSubmit = async (prescriptionDetails: PrescriptionDetails) => {
    if (!selectedService) return;

    try {
      setAddingService(true);
      await addServiceToBill({
        visit_id: parseInt(visitId),
        department: selectedService.department,
        service_code: selectedService.service_code,
        additional_data: prescriptionDetails,
      });
      showSuccess(`Prescription for ${selectedService.service_name} created successfully`);
      
      // Close the prescription form
      setShowPrescriptionForm(false);
      setSelectedService(null);
      
      // Notify parent component to refresh data if needed
      if (onServiceAdded) {
        onServiceAdded();
      }
    } catch (error: any) {
      const message = getAddServiceErrorMessage(error, `Failed to prescribe ${selectedService.service_name}`);
      showError(message);
      if (message !== ALREADY_ADDED_MSG) console.error('Error creating prescription:', error);
    } finally {
      setAddingService(false);
    }
  };

  const handlePrescriptionCancel = () => {
    setShowPrescriptionForm(false);
    setSelectedService(null);
    setShowServiceSearch(true);
  };

  const handleLabOrderSubmit = async (labOrderDetails: LabOrderDetails) => {
    if (!selectedService) return;

    try {
      setAddingService(true);
      await addServiceToBill({
        visit_id: parseInt(visitId),
        department: selectedService.department,
        service_code: selectedService.service_code,
        additional_data: labOrderDetails,
      });
      
      logger.debug('Lab order created successfully');
      showSuccess(`Lab order for ${selectedService.service_name} created successfully`);
      
      // Close the lab order form
      setShowLabOrderForm(false);
      setSelectedService(null);
      
      // Notify parent component to refresh data if needed
      if (onServiceAdded) {
        onServiceAdded();
      }
    } catch (error: any) {
      const message = getAddServiceErrorMessage(error, `Failed to order ${selectedService.service_name}`);
      showError(message);
      if (message !== ALREADY_ADDED_MSG) console.error('Error creating lab order:', error);
    } finally {
      setAddingService(false);
    }
  };

  const handleLabOrderCancel = () => {
    setShowLabOrderForm(false);
    setSelectedService(null);
    setShowServiceSearch(true);
  };

  const handleRadiologyOrderSubmit = async (radiologyOrderDetails: RadiologyOrderDetails) => {
    if (!selectedService) return;

    try {
      setAddingService(true);
      await addServiceToBill({
        visit_id: parseInt(visitId),
        department: selectedService.department,
        service_code: selectedService.service_code,
        additional_data: radiologyOrderDetails,
      });
      showSuccess(`Radiology order for ${selectedService.service_name} created successfully`);
      
      // Close the radiology order form
      setShowRadiologyOrderForm(false);
      setSelectedService(null);
      
      // Notify parent component to refresh data if needed
      if (onServiceAdded) {
        onServiceAdded();
      }
    } catch (error: any) {
      const message = getAddServiceErrorMessage(error, `Failed to order ${selectedService.service_name}`);
      showError(message);
      if (message !== ALREADY_ADDED_MSG) console.error('Error creating radiology order:', error);
    } finally {
      setAddingService(false);
    }
  };

  const handleRadiologyOrderCancel = () => {
    setShowRadiologyOrderForm(false);
    setSelectedService(null);
    setShowServiceSearch(true);
  };

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Order Services from Catalog</h3>
        {!showServiceSearch && !showPrescriptionForm && !showLabOrderForm && !showRadiologyOrderForm && (
          <button
            className={styles.addButton}
            onClick={() => setShowServiceSearch(true)}
            type="button"
            disabled={addingService}
          >
            🔍 Search & Order Service
          </button>
        )}
      </div>

      {showServiceSearch && (
        <div className={styles.createForm}>
          <div className={styles.formGroup}>
            <label>Search Service Catalog</label>
            <p className={styles.helpText}>
              Search and order services from the catalog. Services will be automatically 
              added to the patient's account and will reflect in the Receptionist dashboard.
            </p>
            <ServiceSearchInput
              onServiceSelect={handleServiceSelect}
              placeholder="Search services (e.g., consultation, dental, vaccine, lab test)..."
              disabled={addingService}
            />
          </div>
          <div className={styles.formActions}>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowServiceSearch(false);
              }}
              disabled={addingService}
            >
              Cancel
            </button>
          </div>
          {addingService && (
            <p className={styles.helpText}>Adding service to patient's account...</p>
          )}
        </div>
      )}

      {/* Prescription Details Form Modal */}
      {showPrescriptionForm && selectedService && (
        <PrescriptionDetailsForm
          drugName={selectedService.service_name || 'Unknown Drug'}
          onSubmit={handlePrescriptionSubmit}
          onCancel={handlePrescriptionCancel}
          isSubmitting={addingService}
        />
      )}

      {/* Lab Order Details Form Modal */}
      {showLabOrderForm && selectedService && (
        <LabOrderDetailsForm
          serviceName={selectedService.service_name || 'Lab Tests'}
          onSubmit={handleLabOrderSubmit}
          onCancel={handleLabOrderCancel}
          isSubmitting={addingService}
        />
      )}

      {/* Radiology Order Details Form Modal */}
      {showRadiologyOrderForm && selectedService && (
        <RadiologyOrderDetailsForm
          serviceName={selectedService.service_name || 'Imaging Study'}
          onSubmit={handleRadiologyOrderSubmit}
          onCancel={handleRadiologyOrderCancel}
          isSubmitting={addingService}
        />
      )}

      {!showServiceSearch && !showPrescriptionForm && !showLabOrderForm && !showRadiologyOrderForm && (
        <div className={styles.infoText}>
          <p>
            💡 <strong>Order Services:</strong> Search and order services from the catalog. 
            Services will be automatically added to the patient's bill and will appear 
            in the Receptionist dashboard for payment processing.
          </p>
          <p>
            <strong>Note:</strong> When lab or radiology orders are completed by technicians, 
            the billing will automatically update in the Receptionist dashboard.
          </p>
        </div>
      )}
    </div>
  );
}

