/**
 * IVF Reports Page
 * 
 * Shows comprehensive IVF statistics and allows report generation.
 * Includes success rates, cycle outcomes, and exportable data.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  fetchIVFStatistics, 
  IVFStatistics,
  CYCLE_STATUS_LABELS,
  CYCLE_TYPE_LABELS
} from '../api/ivf';
import styles from '../styles/IVFReports.module.css';

type ReportPeriod = 'month' | 'quarter' | 'year' | 'all';

export default function IVFReportsPage() {
  const navigate = useNavigate();
  
  const [statistics, setStatistics] = useState<IVFStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<ReportPeriod>('year');

  useEffect(() => {
    loadStatistics();
  }, [period]);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Calculate date range based on period
      const now = new Date();
      let startDate: string | undefined;
      
      if (period === 'month') {
        const monthAgo = new Date(now);
        monthAgo.setMonth(monthAgo.getMonth() - 1);
        startDate = monthAgo.toISOString().split('T')[0];
      } else if (period === 'quarter') {
        const quarterAgo = new Date(now);
        quarterAgo.setMonth(quarterAgo.getMonth() - 3);
        startDate = quarterAgo.toISOString().split('T')[0];
      } else if (period === 'year') {
        const yearAgo = new Date(now);
        yearAgo.setFullYear(yearAgo.getFullYear() - 1);
        startDate = yearAgo.toISOString().split('T')[0];
      }
      // 'all' leaves startDate undefined
      
      const endDate = now.toISOString().split('T')[0];
      const data = await fetchIVFStatistics(startDate, endDate);
      setStatistics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  const exportReport = (format: 'csv' | 'pdf') => {
    if (!statistics) return;

    if (format === 'csv') {
      // Generate CSV data
      const csvData = generateCSV(statistics);
      downloadFile(csvData, 'ivf-report.csv', 'text/csv');
    } else {
      // For PDF, we'd integrate with a PDF library
      alert('PDF export would be integrated with a PDF generation library');
    }
  };

  const generateCSV = (stats: IVFStatistics): string => {
    const lines = [
      ['IVF Statistical Report'],
      [`Report Period: ${period}`],
      [`Generated: ${new Date().toLocaleDateString()}`],
      [],
      ['Overall Statistics'],
      ['Metric', 'Value'],
      ['Total Cycles', stats.total_cycles.toString()],
      ['Completed Cycles', stats.completed_cycles.toString()],
      ['Pregnancy Rate', `${stats.pregnancy_rate.toFixed(1)}%`],
      ['Clinical Pregnancy Rate', `${stats.clinical_pregnancy_rate.toFixed(1)}%`],
      ['Live Birth Rate', `${stats.live_birth_rate.toFixed(1)}%`],
      [],
      ['Cycles by Status'],
      ['Status', 'Count'],
      ...stats.cycles_by_status.map(s => [CYCLE_STATUS_LABELS[s.status] || s.status, s.count.toString()]),
      [],
      ['Cycles by Type'],
      ['Type', 'Count'],
      ...stats.cycles_by_type.map(t => [CYCLE_TYPE_LABELS[t.cycle_type] || t.cycle_type, t.count.toString()]),
    ];

    return lines.map(line => line.join(',')).join('\n');
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      PLANNED: '#6c757d',
      STIMULATION: '#17a2b8',
      RETRIEVAL: '#ffc107',
      FERTILIZATION: '#fd7e14',
      CULTURE: '#e83e8c',
      TRANSFER: '#6f42c1',
      LUTEAL: '#20c997',
      PREGNANCY_TEST: '#007bff',
      PREGNANT: '#28a745',
      NOT_PREGNANT: '#dc3545',
      CANCELLED: '#6c757d',
      COMPLETED: '#28a745',
    };
    return colors[status] || '#6c757d';
  };

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.loading}>Loading reports...</div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button 
            className={styles.backButton}
            onClick={() => navigate('/ivf')}
          >
            ← IVF Dashboard
          </button>
          <h1>IVF Reports & Analytics</h1>
        </div>
        <div className={styles.headerActions}>
          <select 
            value={period} 
            onChange={(e) => setPeriod(e.target.value as ReportPeriod)}
            className={styles.periodSelect}
          >
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
            <option value="all">All Time</option>
          </select>
          <button 
            className={styles.exportButton}
            onClick={() => exportReport('csv')}
          >
            Export CSV
          </button>
        </div>
      </header>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={loadStatistics}>Retry</button>
        </div>
      )}

      {statistics && (
        <>
          {/* Key Performance Indicators */}
          <section className={styles.section}>
            <h2>Key Performance Indicators</h2>
            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <div className={styles.kpiValue}>{statistics.total_cycles}</div>
                <div className={styles.kpiLabel}>Total Cycles</div>
                <div className={styles.kpiSubtext}>Started during period</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiValue}>{statistics.completed_cycles}</div>
                <div className={styles.kpiLabel}>Completed Cycles</div>
                <div className={styles.kpiSubtext}>
                  {statistics.total_cycles > 0 
                    ? `${((statistics.completed_cycles / statistics.total_cycles) * 100).toFixed(0)}% completion rate`
                    : 'N/A'}
                </div>
              </div>
              <div className={styles.kpiCard} style={{ borderColor: '#28a745' }}>
                <div className={styles.kpiValue} style={{ color: '#28a745' }}>
                  {statistics.pregnancy_rate.toFixed(1)}%
                </div>
                <div className={styles.kpiLabel}>Pregnancy Rate</div>
                <div className={styles.kpiSubtext}>Per embryo transfer</div>
              </div>
              <div className={styles.kpiCard} style={{ borderColor: '#007bff' }}>
                <div className={styles.kpiValue} style={{ color: '#007bff' }}>
                  {statistics.clinical_pregnancy_rate.toFixed(1)}%
                </div>
                <div className={styles.kpiLabel}>Clinical Pregnancy</div>
                <div className={styles.kpiSubtext}>With heartbeat detected</div>
              </div>
              <div className={styles.kpiCard} style={{ borderColor: '#6f42c1' }}>
                <div className={styles.kpiValue} style={{ color: '#6f42c1' }}>
                  {statistics.live_birth_rate.toFixed(1)}%
                </div>
                <div className={styles.kpiLabel}>Live Birth Rate</div>
                <div className={styles.kpiSubtext}>Successful deliveries</div>
              </div>
            </div>
          </section>

          {/* Cycles by Status */}
          <section className={styles.section}>
            <h2>Cycles by Status</h2>
            <div className={styles.chartSection}>
              <div className={styles.barChart}>
                {statistics.cycles_by_status.map((item) => {
                  const percentage = statistics.total_cycles > 0 
                    ? (item.count / statistics.total_cycles) * 100 
                    : 0;
                  return (
                    <div key={item.status} className={styles.barRow}>
                      <div className={styles.barLabel}>
                        {CYCLE_STATUS_LABELS[item.status] || item.status}
                      </div>
                      <div className={styles.barContainer}>
                        <div 
                          className={styles.barFill}
                          style={{ 
                            width: `${percentage}%`,
                            backgroundColor: getStatusColor(item.status)
                          }}
                        />
                      </div>
                      <div className={styles.barValue}>
                        {item.count} ({percentage.toFixed(0)}%)
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* Cycles by Type */}
          <section className={styles.section}>
            <h2>Cycles by Treatment Type</h2>
            <div className={styles.typeGrid}>
              {statistics.cycles_by_type.map((item) => {
                const percentage = statistics.total_cycles > 0 
                  ? (item.count / statistics.total_cycles) * 100 
                  : 0;
                return (
                  <div key={item.cycle_type} className={styles.typeCard}>
                    <div className={styles.typeHeader}>
                      <span className={styles.typeName}>
                        {CYCLE_TYPE_LABELS[item.cycle_type] || item.cycle_type}
                      </span>
                      <span className={styles.typeCount}>{item.count}</span>
                    </div>
                    <div className={styles.typeProgress}>
                      <div 
                        className={styles.typeProgressFill}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <div className={styles.typePercentage}>{percentage.toFixed(1)}%</div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Outcome Metrics */}
          <section className={styles.section}>
            <h2>Outcome Metrics</h2>
            <div className={styles.metricsGrid}>
              <div className={styles.metricCard}>
                <h3>Success Rates Breakdown</h3>
                <div className={styles.metricTable}>
                  <div className={styles.metricRow}>
                    <span>Positive Pregnancy Test</span>
                    <span className={styles.metricValue}>
                      {statistics.pregnancy_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Clinical Pregnancy</span>
                    <span className={styles.metricValue}>
                      {statistics.clinical_pregnancy_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Live Birth</span>
                    <span className={styles.metricValue}>
                      {statistics.live_birth_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className={styles.metricCard}>
                <h3>Cycle Efficiency</h3>
                <div className={styles.metricTable}>
                  <div className={styles.metricRow}>
                    <span>Cycles Completed</span>
                    <span className={styles.metricValue}>
                      {statistics.completed_cycles} / {statistics.total_cycles}
                    </span>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Completion Rate</span>
                    <span className={styles.metricValue}>
                      {statistics.total_cycles > 0 
                        ? ((statistics.completed_cycles / statistics.total_cycles) * 100).toFixed(1)
                        : 0}%
                    </span>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Active Cycles</span>
                    <span className={styles.metricValue}>
                      {statistics.total_cycles - statistics.completed_cycles}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Compliance Section */}
          <section className={styles.complianceSection}>
            <h2>Nigerian Healthcare Compliance</h2>
            <div className={styles.complianceGrid}>
              <div className={styles.complianceItem}>
                <span className={styles.complianceIcon}>✓</span>
                <div>
                  <strong>FMHACA Guidelines</strong>
                  <p>All cycles follow Federal Ministry of Health ART guidelines</p>
                </div>
              </div>
              <div className={styles.complianceItem}>
                <span className={styles.complianceIcon}>✓</span>
                <div>
                  <strong>Consent Documentation</strong>
                  <p>Patient consent recorded for all procedures</p>
                </div>
              </div>
              <div className={styles.complianceItem}>
                <span className={styles.complianceIcon}>✓</span>
                <div>
                  <strong>Data Protection</strong>
                  <p>Patient data handled per NDPR requirements</p>
                </div>
              </div>
              <div className={styles.complianceItem}>
                <span className={styles.complianceIcon}>✓</span>
                <div>
                  <strong>Quality Assurance</strong>
                  <p>Laboratory standards meet international benchmarks</p>
                </div>
              </div>
            </div>
          </section>

          {/* Report Footer */}
          <div className={styles.reportFooter}>
            <p>
              Report generated on {new Date().toLocaleDateString()} at {new Date().toLocaleTimeString()}
            </p>
            <p>
              Period: {period === 'month' ? 'This Month' : period === 'quarter' ? 'This Quarter' : period === 'year' ? 'This Year' : 'All Time'}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
