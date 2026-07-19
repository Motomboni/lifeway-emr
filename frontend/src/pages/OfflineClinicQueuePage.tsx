/**
 * Offline clinic queue — view and sync pending actions captured while offline.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../hooks/useOffline';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { fetchOfflineQueue, syncOfflineEntry, OfflineQueueEntry } from '../api/offline';
import styles from '../styles/RevenueLeakDashboard.module.css';

export default function OfflineClinicQueuePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isOffline = useOffline();
  const { showError, showSuccess } = useToast();
  const [entries, setEntries] = useState<OfflineQueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [deviceId, setDeviceId] = useState(
    () => localStorage.getItem('offline_device_id') || `web-${Date.now()}`,
  );

  useEffect(() => {
    if (!user) navigate('/login');
    localStorage.setItem('offline_device_id', deviceId);
  }, [user, navigate, deviceId]);

  const load = async () => {
    try {
      setLoading(true);
      setEntries(await fetchOfflineQueue(deviceId));
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load offline queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) load();
  }, [user, deviceId]);

  const handleSync = async (id: number) => {
    try {
      await syncOfflineEntry(id);
      showSuccess('Entry synced');
      load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Sync failed');
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Offline Clinic Queue</h1>
        <p className={styles.subtitle}>
          Pending actions from low-connectivity sessions {isOffline ? '(offline now)' : ''}
        </p>
      </header>

      <div className={styles.filters}>
        <label>
          Device ID
          <input value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
        </label>
        <button type="button" onClick={load}>Refresh</button>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Action</th>
              <th>Status</th>
              <th>Created</th>
              <th>Sync</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr><td colSpan={5}>No pending offline entries</td></tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.id}</td>
                  <td>{e.action}</td>
                  <td>{e.status}</td>
                  <td>{new Date(e.created_at).toLocaleString()}</td>
                  <td>
                    {e.status === 'PENDING' && (
                      <button type="button" onClick={() => handleSync(e.id)}>Sync</button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
