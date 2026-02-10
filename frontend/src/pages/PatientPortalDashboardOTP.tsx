/**
 * Patient Portal Dashboard (OTP Version)
 * 
 * Mobile-optimized patient portal dashboard.
 * Shows:
 * - Upcoming appointments
 * - Recent prescriptions
 * - Lab results
 * - Bills
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface DashboardData {
  patient_name: string;
  patient_id: string;
  summary: {
    upcoming_appointments: number;
    open_visits: number;
    unpaid_bills: number;
    recent_lab_results: number;
  };
}

export default function PatientPortalDashboardOTP() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        navigate('/otp-login');
        return;
      }

      const response = await fetch('/api/mobile/dashboard/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.status === 401) {
        // Token expired
        localStorage.clear();
        navigate('/otp-login');
        return;
      }

      const data = await response.json();
      setDashboard(data);

    } catch (err: any) {
      setError('Failed to load dashboard');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/otp-login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Failed to load'}</p>
          <button
            onClick={loadDashboard}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 shadow">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">{dashboard.patient_name}</h1>
            <p className="text-blue-100 text-sm">ID: {dashboard.patient_id}</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-800 rounded-lg text-sm font-medium transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="max-w-4xl mx-auto p-4">
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Appointments */}
          <div
            onClick={() => navigate('/patient-portal/appointments')}
            className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">📅</span>
              <span className="text-2xl font-bold text-blue-600">
                {dashboard.summary.upcoming_appointments}
              </span>
            </div>
            <p className="text-sm font-medium text-gray-700">Appointments</p>
          </div>

          {/* Lab Results */}
          <div
            onClick={() => navigate('/patient-portal/lab-results')}
            className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">🧪</span>
              <span className="text-2xl font-bold text-green-600">
                {dashboard.summary.recent_lab_results}
              </span>
            </div>
            <p className="text-sm font-medium text-gray-700">Lab Results</p>
          </div>

          {/* Bills */}
          <div
            onClick={() => navigate('/patient-portal/bills')}
            className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">💰</span>
              <span className="text-2xl font-bold text-yellow-600">
                {dashboard.summary.unpaid_bills}
              </span>
            </div>
            <p className="text-sm font-medium text-gray-700">Unpaid Bills</p>
          </div>

          {/* Prescriptions */}
          <div
            onClick={() => navigate('/patient-portal/prescriptions')}
            className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">💊</span>
              <span className="text-2xl font-bold text-purple-600">
                {dashboard.summary.open_visits}
              </span>
            </div>
            <p className="text-sm font-medium text-gray-700">Prescriptions</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          
          <div className="space-y-3">
            <button
              onClick={() => navigate('/patient-portal/appointments')}
              className="w-full py-3 px-4 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg flex items-center justify-between transition-colors"
            >
              <span className="font-medium">View Appointments</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            
            <button
              onClick={() => navigate('/patient-portal/prescriptions')}
              className="w-full py-3 px-4 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg flex items-center justify-between transition-colors"
            >
              <span className="font-medium">View Prescriptions</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            
            <button
              onClick={() => navigate('/patient-portal/lab-results')}
              className="w-full py-3 px-4 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg flex items-center justify-between transition-colors"
            >
              <span className="font-medium">View Lab Results</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            
            <button
              onClick={() => navigate('/patient-portal/bills')}
              className="w-full py-3 px-4 bg-yellow-50 hover:bg-yellow-100 text-yellow-700 rounded-lg flex items-center justify-between transition-colors"
            >
              <span className="font-medium">View Bills</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
