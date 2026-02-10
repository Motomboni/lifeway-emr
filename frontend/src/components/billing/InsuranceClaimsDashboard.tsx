/**
 * Insurance Claims dashboard: create claim, track status, filter by provider, export PDF (stub).
 */
import React, { useState, useEffect } from 'react';
import { apiRequest } from '../../utils/apiClient';
import { useToast } from '../../hooks/useToast';

interface Claim {
  id: number;
  patient: number;
  patient_name: string;
  policy: number;
  policy_number: string;
  provider_id: number;
  provider_name: string;
  services: unknown[];
  total_amount: string;
  status: string;
  submitted_at: string | null;
  created_at: string;
}

interface Policy {
  id: number;
  patient: number;
  patient_name: string;
  provider: number;
  provider_name: string;
  policy_number: string;
  is_active: boolean;
}

export default function InsuranceClaimsDashboard() {
  const { showSuccess, showError } = useToast();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [providerFilter, setProviderFilter] = useState('');
  const [createPatientId, setCreatePatientId] = useState('');
  const [creating, setCreating] = useState(false);
  const [submittingId, setSubmittingId] = useState<number | null>(null);

  const loadClaims = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      if (providerFilter) params.set('provider_id', providerFilter);
      const q = params.toString();
      const data = await apiRequest<Claim[]>(
        q ? `/billing/claims/claims/?${q}` : '/billing/claims/claims/'
      );
      setClaims(Array.isArray(data) ? data : []);
    } catch {
      setClaims([]);
    }
  };

  const loadPolicies = async () => {
    try {
      const data = await apiRequest<{ results?: Policy[] } | Policy[]>(
        '/billing/claims/policies/'
      );
      setPolicies(Array.isArray(data) ? data : (data as { results?: Policy[] }).results || []);
    } catch {
      setPolicies([]);
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([loadClaims(), loadPolicies()]).finally(() => setLoading(false));
  }, [statusFilter, providerFilter]);

  const handleCreateClaim = async () => {
    const pid = parseInt(createPatientId, 10);
    if (!pid) {
      showError('Enter a valid patient ID');
      return;
    }
    setCreating(true);
    try {
      await apiRequest('/billing/claims/claims/', {
        method: 'POST',
        body: JSON.stringify({ patient_id: pid }),
      });
      showSuccess('Draft claim created.');
      setCreatePatientId('');
      loadClaims();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to create claim');
    } finally {
      setCreating(false);
    }
  };

  const handleSubmitClaim = async (claimId: number) => {
    setSubmittingId(claimId);
    try {
      await apiRequest(`/billing/claims/claims/${claimId}/submit/`, {
        method: 'POST',
      });
      showSuccess('Claim submitted.');
      loadClaims();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to submit claim');
    } finally {
      setSubmittingId(null);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <p className="text-gray-500">Loading claims...</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Insurance Claims</h2>
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="paid">Paid</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Provider</label>
          <select
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All</option>
            {Array.from(
              new Map(claims.map((c) => [c.provider_id, c.provider_name])).entries()
            ).map(([id, name]) => (
              <option key={id} value={String(id)}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Patient ID"
            value={createPatientId}
            onChange={(e) => setCreatePatientId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-28"
          />
          <button
            type="button"
            onClick={handleCreateClaim}
            disabled={creating}
            className="min-h-[40px] px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {creating ? 'Creating...' : 'Create claim'}
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">ID</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Patient</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Provider</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Amount</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Submitted</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {claims.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-500">
                  No claims found.
                </td>
              </tr>
            ) : (
              claims.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-2 text-sm text-gray-900">{c.id}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">{c.patient_name}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">{c.provider_name}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">₦{c.total_amount}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        c.status === 'paid'
                          ? 'bg-green-100 text-green-800'
                          : c.status === 'rejected'
                          ? 'bg-red-100 text-red-800'
                          : c.status === 'approved'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-500">
                    {c.submitted_at ? new Date(c.submitted_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-2">
                    {c.status === 'draft' && (
                      <button
                        type="button"
                        onClick={() => handleSubmitClaim(c.id)}
                        disabled={submittingId === c.id}
                        className="text-sm text-blue-600 hover:underline disabled:opacity-50"
                      >
                        {submittingId === c.id ? 'Submitting...' : 'Submit'}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-gray-500">Export PDF: configure in production.</p>
    </div>
  );
}
