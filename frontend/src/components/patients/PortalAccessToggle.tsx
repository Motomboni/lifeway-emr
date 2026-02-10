/**
 * Portal Access Toggle Component
 * 
 * Admin toggle switch to enable/disable patient portal access.
 * 
 * Features:
 * - Visual toggle switch (Tailwind styled)
 * - Confirmation modal before disabling
 * - Loading state
 * - Success/error feedback
 * - Shows portal status badge
 * - Admin only (checks user role)
 * 
 * Behavior:
 * - When disabled: Sets user.is_active=False (blocks login)
 * - When enabled: Sets user.is_active=True (allows login)
 */
import React, { useState } from 'react';
import { togglePortalAccess } from '../../api/patient';
import { useAuth } from '../../contexts/AuthContext';

interface PortalAccessToggleProps {
  patient: {
    id: number;
    patient_id?: string;
    first_name: string;
    last_name: string;
    portal_enabled: boolean;
  };
  onToggle?: (enabled: boolean) => void;
  showLabel?: boolean;
}

export default function PortalAccessToggle({
  patient,
  onToggle,
  showLabel = true
}: PortalAccessToggleProps) {
  const { user } = useAuth();
  const [isEnabled, setIsEnabled] = useState(patient.portal_enabled);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingState, setPendingState] = useState<boolean | null>(null);

  // Only show for Admin users
  if (user?.role !== 'ADMIN') {
    // Show read-only badge for non-admin
    return (
      <div className="flex items-center gap-2">
        {showLabel && (
          <span className="text-sm text-gray-600">Portal Access:</span>
        )}
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          isEnabled 
            ? 'bg-green-100 text-green-800' 
            : 'bg-gray-100 text-gray-600'
        }`}>
          {isEnabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>
    );
  }

  const handleToggleClick = (newState: boolean) => {
    // If disabling, show confirmation modal
    if (!newState && isEnabled) {
      setPendingState(newState);
      setShowConfirmModal(true);
    } else {
      performToggle(newState);
    }
  };

  const performToggle = async (newState: boolean) => {
    setIsLoading(true);
    setShowConfirmModal(false);

    try {
      const response = await togglePortalAccess(patient.id, newState);

      if (response.success) {
        setIsEnabled(response.portal_enabled);
        
        if (onToggle) {
          onToggle(response.portal_enabled);
        }

        // Show success message
        const message = newState 
          ? 'Portal access enabled successfully' 
          : 'Portal access disabled successfully';
        
        // You can integrate with toast notification here
        console.log(message, response);
      } else {
        throw new Error(response.message || 'Failed to toggle portal access');
      }

    } catch (error: any) {
      console.error('Toggle portal error:', error);
      alert(error.message || 'Failed to toggle portal access');
      // Revert state on error
      setIsEnabled(patient.portal_enabled);
    } finally {
      setIsLoading(false);
      setPendingState(null);
    }
  };

  const patientName = `${patient.first_name} ${patient.last_name}`.trim();

  return (
    <>
      <div className="flex items-center gap-3">
        {showLabel && (
          <span className="text-sm font-medium text-gray-700">
            Portal Access:
          </span>
        )}
        
        {/* Toggle Switch */}
        <button
          onClick={() => handleToggleClick(!isEnabled)}
          disabled={isLoading}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full transition-colors
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            disabled:opacity-50 disabled:cursor-not-allowed
            ${isEnabled ? 'bg-green-600' : 'bg-gray-300'}
          `}
          role="switch"
          aria-checked={isEnabled}
          aria-label="Toggle portal access"
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform
              ${isEnabled ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </button>

        {/* Status Badge */}
        <span className={`
          px-2 py-1 rounded text-xs font-medium
          ${isEnabled 
            ? 'bg-green-100 text-green-800' 
            : 'bg-gray-100 text-gray-600'
          }
        `}>
          {isLoading ? 'Updating...' : (isEnabled ? 'Enabled' : 'Disabled')}
        </span>

        {/* Info Icon with Tooltip */}
        <div className="relative group">
          <svg 
            className="w-4 h-4 text-gray-400 cursor-help" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path 
              fillRule="evenodd" 
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" 
              clipRule="evenodd" 
            />
          </svg>
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-64">
            <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 shadow-lg">
              {isEnabled 
                ? 'Patient can log in to view records, appointments, and bills.'
                : 'Patient cannot access the portal. Login is blocked.'}
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>

            <h3 className="text-lg font-bold text-gray-900 mb-2 text-center">
              Disable Portal Access?
            </h3>
            
            <p className="text-gray-600 text-center mb-4">
              Disable portal access for <strong>{patientName}</strong>?
            </p>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
              <p className="text-sm text-yellow-800">
                <strong>Warning:</strong> This will:
              </p>
              <ul className="text-sm text-yellow-800 mt-2 ml-4 list-disc space-y-1">
                <li>Block patient from logging into the portal</li>
                <li>Set user account to inactive</li>
                <li>Patient will see "Invalid credentials" when trying to login</li>
              </ul>
              <p className="text-sm text-yellow-800 mt-2">
                You can re-enable access at any time.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowConfirmModal(false);
                  setPendingState(null);
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => performToggle(false)}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
              >
                Disable Portal
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
