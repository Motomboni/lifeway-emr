/**
 * Create Portal Account Button
 * 
 * Button component for patient profile/list to trigger portal account creation.
 * 
 * Usage:
 *   <CreatePortalAccountButton
 *     patient={patient}
 *     onSuccess={() => refetchPatient()}
 *   />
 */
import React, { useState } from 'react';
import CreatePortalAccountModal from './CreatePortalAccountModal';

interface CreatePortalAccountButtonProps {
  patient: {
    id: number;
    patient_id?: string;
    first_name: string;
    last_name: string;
    portal_enabled?: boolean;
  };
  onSuccess?: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}

export default function CreatePortalAccountButton({
  patient,
  onSuccess,
  variant = 'primary',
  size = 'md'
}: CreatePortalAccountButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Don't show button if portal already enabled
  if (patient.portal_enabled) {
    return (
      <div className="inline-flex items-center px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm">
        <svg className="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
        Portal Active
      </div>
    );
  }

  const patientName = `${patient.first_name} ${patient.last_name}`.trim();

  // Size classes
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  // Variant classes
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700',
    outline: 'bg-white text-blue-600 border-2 border-blue-600 hover:bg-blue-50'
  };

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className={`
          ${sizeClasses[size]}
          ${variantClasses[variant]}
          rounded-lg font-medium transition-colors
          flex items-center justify-center gap-2
          focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        `}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
        </svg>
        Create Portal Account
      </button>

      <CreatePortalAccountModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        patientId={patient.id}
        patientName={patientName}
        onSuccess={() => {
          setIsModalOpen(false);
          if (onSuccess) {
            onSuccess();
          }
        }}
      />
    </>
  );
}
