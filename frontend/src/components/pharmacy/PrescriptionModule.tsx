/**
 * E-Prescription module: search medication, add dosage, auto-check interactions, show alert banners.
 */
import React, { useState, useEffect } from 'react';
import { apiRequest } from '../../utils/apiClient';
import { useToast } from '../../hooks/useToast';

interface Medication {
  id: number;
  name: string;
  generic_name: string;
  drug_class: string;
}

interface LineItem {
  medication_id: number;
  medication_name: string;
  dosage: string;
  frequency: string;
  duration: string;
}

interface Warning {
  severity: string;
  message: string;
}

interface PrescriptionModuleProps {
  patientId: number;
  onSaved?: () => void;
}

export default function PrescriptionModule({ patientId, onSaved }: PrescriptionModuleProps) {
  const { showSuccess, showError } = useToast();
  const [search, setSearch] = useState('');
  const [medications, setMedications] = useState<Medication[]>([]);
  const [lines, setLines] = useState<LineItem[]>([]);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [overrideReason, setOverrideReason] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (search.length < 2) {
      setMedications([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const data = await apiRequest<{ results?: Medication[] }>(
          `/eprescription/medications/?search=${encodeURIComponent(search)}`
        );
        setMedications(Array.isArray(data) ? data : (data.results || []));
      } catch {
        setMedications([]);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const addLine = (m: Medication) => {
    if (lines.some((l) => l.medication_id === m.id)) return;
    setLines((prev) => [
      ...prev,
      { medication_id: m.id, medication_name: m.name, dosage: '', frequency: '', duration: '' },
    ]);
    setSearch('');
    setMedications([]);
  };

  const updateLine = (index: number, field: keyof LineItem, value: string) => {
    setLines((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const removeLine = (index: number) => {
    setLines((prev) => prev.filter((_, i) => i !== index));
    setWarnings([]);
  };

  const checkInteractions = async () => {
    if (lines.length < 2) {
      setWarnings([]);
      return;
    }
    try {
      const data = await apiRequest<{ warnings: Warning[] }>(
        '/eprescription/medications/check-interactions/',
        {
          method: 'POST',
          body: JSON.stringify({ medication_ids: lines.map((l) => l.medication_id) }),
        }
      );
      setWarnings(data.warnings || []);
    } catch {
      setWarnings([]);
    }
  };

  useEffect(() => {
    checkInteractions();
  }, [lines.map((l) => l.medication_id).join(',')]);

  const handleSubmit = async () => {
    if (!lines.length) {
      showError('Add at least one medication');
      return;
    }
    const hasSevere = warnings.some((w) => w.severity === 'Severe');
    if (hasSevere && !overrideReason.trim()) {
      showError('Provide a reason to override severe interaction(s)');
      return;
    }
    setSubmitting(true);
    try {
      await apiRequest('/eprescription/prescriptions/', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          medications: lines.map((l) => ({
            medication_id: l.medication_id,
            dosage: l.dosage,
            frequency: l.frequency,
            duration: l.duration,
          })),
          notes,
          override_reason: overrideReason || undefined,
        }),
      });
      showSuccess('Prescription saved.');
      setLines([]);
      setWarnings([]);
      setOverrideReason('');
      setNotes('');
      onSaved?.();
    } catch (e: unknown) {
      const err = e as { responseData?: { warnings?: Warning[]; detail?: string } };
      if (err.responseData?.warnings) setWarnings(err.responseData.warnings);
      showError(err.responseData?.detail || (e instanceof Error ? e.message : 'Failed to save'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">E-Prescription</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Search medication</label>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Type to search..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          {medications.length > 0 && (
            <ul className="mt-1 border border-gray-200 rounded-lg divide-y max-h-40 overflow-auto">
              {medications.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => addLine(m)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                  >
                    {m.name} {m.generic_name ? `(${m.generic_name})` : ''}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {lines.length > 0 && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Medications</label>
              {lines.map((line, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 p-3 mb-2">
                  <span className="font-medium text-gray-900">{line.medication_name}</span>
                  <input
                    placeholder="Dosage"
                    value={line.dosage}
                    onChange={(e) => updateLine(i, 'dosage', e.target.value)}
                    className="flex-1 min-w-[80px] rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    placeholder="Frequency"
                    value={line.frequency}
                    onChange={(e) => updateLine(i, 'frequency', e.target.value)}
                    className="flex-1 min-w-[80px] rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    placeholder="Duration"
                    value={line.duration}
                    onChange={(e) => updateLine(i, 'duration', e.target.value)}
                    className="flex-1 min-w-[80px] rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <button type="button" onClick={() => removeLine(i)} className="text-red-600 text-sm">
                    Remove
                  </button>
                </div>
              ))}
            </div>
            {warnings.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <p className="font-medium text-amber-800 mb-2">Drug interaction warnings</p>
                <ul className="list-disc list-inside text-sm text-amber-800 space-y-1">
                  {warnings.map((w, i) => (
                    <li key={i}>
                      [{w.severity}] {w.message}
                    </li>
                  ))}
                </ul>
                {warnings.some((w) => w.severity === 'Severe') && (
                  <div className="mt-3">
                    <label className="block text-sm font-medium text-amber-800 mb-1">Override reason</label>
                    <input
                      type="text"
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="Reason for override"
                      className="w-full rounded border border-amber-300 px-2 py-1 text-sm"
                    />
                  </div>
                )}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="min-h-[44px] px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save prescription'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
