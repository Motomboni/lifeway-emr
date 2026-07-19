/**
 * NAFDAC formulary reference with NHIA tariff alignment.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { fetchNafdacFormulary, NafdacFormularyEntry } from '../api/pharmacy';
import styles from '../styles/RevenueLeakDashboard.module.css';

export default function NafdacFormularyPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  const [entries, setEntries] = useState<NafdacFormularyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [nhiaOnly, setNhiaOnly] = useState(false);

  useEffect(() => {
    if (!user) navigate('/login');
  }, [user, navigate]);

  const load = async () => {
    try {
      setLoading(true);
      setEntries(await fetchNafdacFormulary({ search: search || undefined, nhia_tariff_only: nhiaOnly }));
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load formulary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) load();
  }, [user, nhiaOnly]);

  if (loading && entries.length === 0) {
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
        <h1>NAFDAC Formulary</h1>
        <p className={styles.subtitle}>Drug reference with NHIA tariff code alignment</p>
      </header>

      <div className={styles.filters}>
        <input
          placeholder="Search product or reg. no."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label>
          <input type="checkbox" checked={nhiaOnly} onChange={(e) => setNhiaOnly(e.target.checked)} />
          NHIA tariff linked only
        </label>
        <button type="button" onClick={load}>Search</button>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Reg. No.</th>
              <th>Product</th>
              <th>Ingredient</th>
              <th>NHIA code</th>
              <th>Essential</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr><td colSpan={5}>No formulary entries — seed via admin or management command</td></tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.nafdac_reg_no}</td>
                  <td>{e.product_name}</td>
                  <td>{e.active_ingredient || '—'}</td>
                  <td>{e.nhia_tariff_code || '—'}</td>
                  <td>{e.is_essential_medicine ? 'Yes' : 'No'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
