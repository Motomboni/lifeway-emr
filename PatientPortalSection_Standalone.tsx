/**
 * Patient Portal Account Creation Section
 * Standalone component for reference
 * 
 * This is the exact Tailwind-styled section added to PatientRegistrationPage.tsx
 * Can be extracted as a separate component if needed
 */

import React, { useState } from 'react';

interface PortalSectionProps {
  createPortalAccount: boolean;
  setCreatePortalAccount: (value: boolean) => void;
  portalData: {
    email: string;
    phone: string;
  };
  setPortalData: React.Dispatch<React.SetStateAction<{
    email: string;
    phone: string;
  }>>;
  fieldErrors: Record<string, string>;
  setFieldErrors: React.Dispatch<React.SetStateAction<Record<string, string>>>;
}

export default function PatientPortalSection({
  createPortalAccount,
  setCreatePortalAccount,
  portalData,
  setPortalData,
  fieldErrors,
  setFieldErrors
}: PortalSectionProps) {
  return (
    <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6 mb-6">
      <div className="flex items-start mb-4">
        <input
          type="checkbox"
          id="createPortalAccount"
          checked={createPortalAccount}
          onChange={(e) => {
            setCreatePortalAccount(e.target.checked);
            // Clear portal field errors when unchecking
            if (!e.target.checked) {
              setFieldErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors.portal_email;
                delete newErrors.portal_phone;
                return newErrors;
              });
            }
          }}
          className="w-5 h-5 text-blue-600 bg-white border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 mt-0.5 cursor-pointer"
        />
        <div className="ml-3">
          <label 
            htmlFor="createPortalAccount" 
            className="text-base font-semibold text-gray-900 cursor-pointer select-none"
          >
            Create Patient Portal Login
          </label>
          <p className="text-sm text-gray-600 mt-1">
            Allows patient to log in to view appointments, records and bills.
          </p>
        </div>
      </div>

      {createPortalAccount && (
        <div className="mt-6 space-y-4 pl-8 border-l-4 border-blue-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Email Field */}
            <div>
              <label 
                htmlFor="portalEmail" 
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                id="portalEmail"
                value={portalData.email}
                onChange={(e) => {
                  setPortalData(prev => ({ ...prev, email: e.target.value }));
                  // Clear error when typing
                  if (fieldErrors.portal_email) {
                    setFieldErrors(prev => {
                      const newErrors = { ...prev };
                      delete newErrors.portal_email;
                      return newErrors;
                    });
                  }
                }}
                placeholder="patient@example.com"
                className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                  fieldErrors.portal_email 
                    ? 'border-red-500 bg-red-50' 
                    : 'border-gray-300 bg-white'
                }`}
                required={createPortalAccount}
                aria-invalid={!!fieldErrors.portal_email}
                aria-describedby={fieldErrors.portal_email ? 'portal-email-error' : undefined}
              />
              {fieldErrors.portal_email && (
                <p id="portal-email-error" className="mt-1.5 text-sm text-red-600 flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {fieldErrors.portal_email}
                </p>
              )}
              <p className="mt-1.5 text-xs text-gray-500">
                Used for login and notifications
              </p>
            </div>

            {/* Phone Field */}
            <div>
              <label 
                htmlFor="portalPhone" 
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Phone Number
              </label>
              <input
                type="tel"
                id="portalPhone"
                value={portalData.phone}
                onChange={(e) => {
                  setPortalData(prev => ({ ...prev, phone: e.target.value }));
                  // Clear error when typing
                  if (fieldErrors.portal_phone) {
                    setFieldErrors(prev => {
                      const newErrors = { ...prev };
                      delete newErrors.portal_phone;
                      return newErrors;
                    });
                  }
                }}
                placeholder="0712345678"
                className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                  fieldErrors.portal_phone 
                    ? 'border-red-500 bg-red-50' 
                    : 'border-gray-300 bg-white'
                }`}
                aria-invalid={!!fieldErrors.portal_phone}
                aria-describedby={fieldErrors.portal_phone ? 'portal-phone-error' : undefined}
              />
              {fieldErrors.portal_phone && (
                <p id="portal-phone-error" className="mt-1.5 text-sm text-red-600 flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {fieldErrors.portal_phone}
                </p>
              )}
              <p className="mt-1.5 text-xs text-gray-500">
                Optional: For SMS notifications
              </p>
            </div>
          </div>

          {/* Information Box */}
          <div className="bg-blue-100 border border-blue-300 rounded-lg p-4 mt-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-blue-800">
                <p className="font-medium">Portal Access Information</p>
                <p className="mt-1">
                  A temporary password will be generated and sent to the patient's email. 
                  They will be required to change it on first login.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


/**
 * VALIDATION LOGIC
 * Add this to your form submission handler
 */

// Example validation in handleSubmit:
/*
const validatePortalAccount = () => {
  if (createPortalAccount) {
    // Email required
    if (!portalData.email || !portalData.email.trim()) {
      showError('Email is required when creating a patient portal account');
      setFieldErrors(prev => ({ 
        ...prev, 
        portal_email: 'Email is required for portal access' 
      }));
      return false;
    }
    
    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(portalData.email)) {
      showError('Please enter a valid email address');
      setFieldErrors(prev => ({ 
        ...prev, 
        portal_email: 'Invalid email format' 
      }));
      return false;
    }
  }
  return true;
};
*/


/**
 * DATA SUBMISSION
 * Add this to your form data before sending to API
 */

// Example in handleSubmit:
/*
// Add patient portal data if portal account requested
if (createPortalAccount) {
  cleanedData.create_portal_account = true;
  cleanedData.portal_enabled = true;
  if (portalData.email?.trim()) {
    cleanedData.portal_email = portalData.email.trim();
  }
  if (portalData.phone?.trim()) {
    cleanedData.portal_phone = portalData.phone.trim();
  }
}
*/


/**
 * TAILWIND CSS CLASSES USED
 * 
 * Container:
 * - bg-blue-50: Light blue background
 * - border-2 border-blue-200: Blue border
 * - rounded-lg: Rounded corners
 * - p-6: Padding
 * - mb-6: Bottom margin
 * 
 * Checkbox:
 * - w-5 h-5: Size
 * - text-blue-600: Checked color
 * - bg-white: Background
 * - border-gray-300: Border
 * - rounded: Rounded corners
 * - focus:ring-2 focus:ring-blue-500: Focus ring
 * - cursor-pointer: Pointer cursor
 * 
 * Labels:
 * - text-base font-semibold text-gray-900: Main label
 * - text-sm text-gray-600: Helper text
 * - text-sm font-medium text-gray-700: Field labels
 * - text-red-500: Required asterisk
 * 
 * Inputs:
 * - w-full: Full width
 * - px-4 py-2.5: Padding
 * - border rounded-lg: Border and corners
 * - focus:ring-2 focus:ring-blue-500: Focus ring
 * - focus:border-blue-500: Focus border
 * - transition-colors: Smooth transitions
 * - border-gray-300 bg-white: Normal state
 * - border-red-500 bg-red-50: Error state
 * 
 * Layout:
 * - grid grid-cols-1 md:grid-cols-2: Responsive grid
 * - gap-4: Grid gap
 * - space-y-4: Vertical spacing
 * - pl-8: Left padding
 * - border-l-4 border-blue-300: Left border accent
 * 
 * Info Box:
 * - bg-blue-100: Background
 * - border border-blue-300: Border
 * - rounded-lg p-4: Rounded with padding
 * - text-blue-800: Text color
 * - font-medium: Bold text
 * 
 * Error Message:
 * - text-sm text-red-600: Size and color
 * - flex items-center: Flex layout
 * - mt-1.5: Top margin
 * 
 * Icons:
 * - w-4 h-4: Error icon size
 * - w-5 h-5: Info icon size
 * - mr-1 / mr-2: Right margin
 * - flex-shrink-0: Don't shrink
 * - mt-0.5: Top margin for alignment
 */
