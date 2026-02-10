/**
 * Add to Bill Button Component
 * 
 * Reusable button for adding services to visit bills from department screens.
 * Used in: Lab results, Pharmacy dispense, Radiology reports.
 * Per EMR Rules: Visit-scoped, automatic price fetching.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { apiRequest } from '../../utils/apiClient';

interface AddToBillButtonProps {
  visitId: number;
  department: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  serviceCode: string;
  serviceName?: string;
  disabled?: boolean;
  onSuccess?: () => void;
  className?: string;
}

const DEPARTMENT_CONFIG = {
  LAB: {
    label: 'Lab',
    icon: '🧪',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    hoverColor: 'hover:bg-blue-200',
  },
  PHARMACY: {
    label: 'Pharmacy',
    icon: '💊',
    color: 'bg-green-100 text-green-800 border-green-200',
    hoverColor: 'hover:bg-green-200',
  },
  RADIOLOGY: {
    label: 'Radiology',
    icon: '📷',
    color: 'bg-purple-100 text-purple-800 border-purple-200',
    hoverColor: 'hover:bg-purple-200',
  },
  PROCEDURE: {
    label: 'Procedure',
    icon: '⚕️',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    hoverColor: 'hover:bg-orange-200',
  },
};

export default function AddToBillButton({
  visitId,
  department,
  serviceCode,
  serviceName,
  disabled: externalDisabled = false,
  onSuccess,
  className = '',
}: AddToBillButtonProps) {
  const { showSuccess, showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [isBilled, setIsBilled] = useState(false);
  const [checking, setChecking] = useState(true);

  const deptConfig = DEPARTMENT_CONFIG[department];

  // Check if this service is already billed
  useEffect(() => {
    checkIfBilled();
  }, [visitId, department, serviceCode]);

  const checkIfBilled = async () => {
    try {
      setChecking(true);
      // Get billing summary to check for existing items
      const summary = await apiRequest(`/billing/visit/${visitId}/summary/`) as any;
      
      if (summary?.items_by_department && summary.items_by_department[department]) {
        const items = summary.items_by_department[department] as any[];
        // Check if service with this code or name is already in the bill
        const alreadyBilled = items.some((item: any) => {
          // Check by service code if available, or by service name
          return (
            item.service_code === serviceCode ||
            (serviceName && item.service_name === serviceName)
          );
        });
        setIsBilled(alreadyBilled);
      }
    } catch (error) {
      console.error('Failed to check billing status:', error);
      // Don't block the button if check fails
      setIsBilled(false);
    } finally {
      setChecking(false);
    }
  };

  const handleAddToBill = async () => {
    if (!visitId || !serviceCode) {
      showError('Missing required information to add item to bill');
      return;
    }

    try {
      setLoading(true);
      
      // POST to /billing/add-item/
      const response = await apiRequest(`/billing/add-item/`, {
        method: 'POST',
        body: JSON.stringify({
          visit_id: visitId,
          department: department,
          service_code: serviceCode,
        }),
      });

      showSuccess(`${deptConfig.label} service added to bill successfully`);
      setIsBilled(true);
      
      // Call success callback if provided
      if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      const data = error?.responseData ?? error?.response?.data;
      const backendMsg =
        data?.detail != null
          ? Array.isArray(data.detail)
            ? data.detail.map((x: any) => (typeof x === 'string' ? x : x?.message ?? String(x))).join('; ')
            : String(data.detail)
          : error?.message;
      const message = backendMsg || `Failed to add ${deptConfig.label.toLowerCase()} service to bill`;
      console.error('Billing add-item failed:', message, data ?? error);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = externalDisabled || isBilled || loading || checking;

  return (
    <button
      onClick={handleAddToBill}
      disabled={isDisabled}
      className={`
        inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg
        border text-sm font-medium transition-all
        ${deptConfig.color}
        ${isDisabled ? 'opacity-50 cursor-not-allowed' : deptConfig.hoverColor}
        ${className}
      `}
      title={
        isBilled
          ? 'Already added to bill'
          : loading
          ? 'Adding to bill...'
          : `Add ${serviceName || deptConfig.label} service to bill`
      }
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
          <span>Adding...</span>
        </>
      ) : isBilled ? (
        <>
          <span>✅</span>
          <span>Added to Bill</span>
        </>
      ) : (
        <>
          <span>{deptConfig.icon}</span>
          <span>Add to Bill</span>
        </>
      )}
    </button>
  );
}

