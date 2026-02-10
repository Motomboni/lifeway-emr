/**
 * Reports & Analytics Page
 * 
 * Enhanced reporting with charts, trends, and visualizations.
 * Admin only access.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { getReportsSummary, ReportSummary } from '../api/reports';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  FaChartLine,
  FaChartBar,
  FaChartPie,
  FaDollarSign,
  FaUsers,
  FaFileMedical,
} from 'react-icons/fa';
import styles from '../styles/ReportsPage.module.css';

export default function ReportsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setMonth(new Date().getMonth() - 1)).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    if (!user || user.role !== 'ADMIN') {
      navigate('/dashboard');
      return;
    }
    loadReportData();
  }, [user, dateRange]);

  const loadReportData = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const data = await getReportsSummary(dateRange.start, dateRange.end);
      setSummary(data);
    } catch (error: any) {
      const message = error instanceof Error ? error.message : 'Failed to load report data';
      setSummary(null);
      setLoadError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (!user || user.role !== 'ADMIN') {
    return null;
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <LoadingSkeleton count={10} />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <div className={styles.emptyState}>
          {loadError ? loadError : 'No report data available'}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      
      <header className={styles.header}>
        <h1>Reports & Analytics</h1>
        <div className={styles.dateRangeSelector}>
          <label>
            Start Date:
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
            />
          </label>
          <label>
            End Date:
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
            />
          </label>
        </div>
      </header>

      {/* Summary Cards */}
      <div className={styles.summaryCards}>
        <div className={styles.summaryCard}>
          <div className={styles.cardIcon} style={{ backgroundColor: '#4caf50' }}>
            <FaDollarSign />
          </div>
          <div className={styles.cardContent}>
            <h3>Total Revenue</h3>
            <p className={styles.cardValue}>{formatCurrency(summary.total_revenue)}</p>
          </div>
        </div>

        <div className={styles.summaryCard}>
          <div className={styles.cardIcon} style={{ backgroundColor: '#2196f3' }}>
            <FaFileMedical size={24} />
          </div>
          <div className={styles.cardContent}>
            <h3>Total Visits</h3>
            <p className={styles.cardValue}>{summary.total_visits}</p>
          </div>
        </div>

        <div className={styles.summaryCard}>
          <div className={styles.cardIcon} style={{ backgroundColor: '#ff9800' }}>
            <FaUsers size={24} />
          </div>
          <div className={styles.cardContent}>
            <h3>Total Patients</h3>
            <p className={styles.cardValue}>{summary.total_patients}</p>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className={styles.chartsSection}>
        <div className={styles.chartCard}>
          <h2>Revenue by Payment Method</h2>
          <div className={styles.chartPlaceholder}>
            <FaChartPie size={48} />
            <p>Pie Chart: Revenue by Payment Method</p>
            <div className={styles.chartLegend}>
              {Object.entries(summary.revenue_by_method).map(([method, amount]) => (
                <div key={method} className={styles.legendItem}>
                  <span className={styles.legendColor}></span>
                  <span>{method}: {formatCurrency(amount)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.chartCard}>
          <h2>Revenue Trend</h2>
          <div className={styles.chartPlaceholder}>
            <FaChartLine size={48} />
            <p>Line Chart: Revenue Trend Over Time</p>
            <div className={styles.trendData}>
              {summary.revenue_trend.map((item, index) => (
                <div key={index} className={styles.trendItem}>
                  <span>{new Date(item.date).toLocaleDateString()}</span>
                  <span>{formatCurrency(item.revenue)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.chartCard}>
          <h2>Visits by Status</h2>
          <div className={styles.chartPlaceholder}>
            <FaChartBar size={48} />
            <p>Bar Chart: Visits by Status</p>
            <div className={styles.barChart}>
              {Object.entries(summary.visits_by_status).map(([status, count]) => (
                <div key={status} className={styles.barItem}>
                  <div className={styles.barLabel}>{status}</div>
                  <div className={styles.barContainer}>
                    <div
                      className={styles.barFill}
                      style={{
                        width: `${(count / summary.total_visits) * 100}%`,
                      }}
                    >
                      {count}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
