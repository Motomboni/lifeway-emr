/**
 * Dashboard Page
 * 
 * Main landing page after login.
 * Role-based dashboard showing relevant information with real data.
 */
import React, { useState, useEffect, useCallback, useRef, memo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { Visit } from '../types/visit';
import { getPendingVerificationPatients } from '../api/patient';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import NotificationBell from '../components/common/NotificationBell';
import ThemeToggle from '../components/common/ThemeToggle';
import Logo from '../components/common/Logo';
import { useDefaultKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import styles from '../styles/Dashboard.module.css';

// Visit Search Component for Nurse Dashboard
interface VisitSearchSectionProps {
  onVisitSelect: (visitId: number) => void;
  loading: boolean;
}

const VisitSearchSection = memo(function VisitSearchSection({ onVisitSelect, loading }: VisitSearchSectionProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [allVisits, setAllVisits] = useState<Visit[]>([]);
  const [searchResults, setSearchResults] = useState<Visit[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const { showError } = useToast();

  // Load all visits on mount for client-side filtering
  useEffect(() => {
    const loadAllVisits = async () => {
      try {
        setIsSearching(true);
        const results = await fetchVisits({
          page_size: 100, // Get more visits for better filtering
        });
        const visits = Array.isArray(results) ? results : results.results;
        setAllVisits(visits);
      } catch (error: any) {
        showError(error.message || 'Failed to load visits');
      } finally {
        setIsSearching(false);
      }
    };
    loadAllVisits();
  }, [showError]);

  const filterVisits = useCallback((query: string, visits: Visit[]): Visit[] => {
    if (!query.trim()) {
      return [];
    }

    const searchLower = query.toLowerCase().trim();
    return visits.filter((visit) => {
      // Search by patient name
      const patientName = (visit.patient_name || '').toLowerCase();
      if (patientName.includes(searchLower)) return true;

      // Search by visit ID
      if (visit.id.toString().includes(searchLower)) return true;

      // Search by patient ID
      const patientId = (visit.patient_id || '').toLowerCase();
      if (patientId.includes(searchLower)) return true;

      return false;
    });
  }, []);

  const performSearch = useCallback((query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    
    // Use setTimeout to allow UI to update
    setTimeout(() => {
      const filtered = filterVisits(query, allVisits);
      setSearchResults(filtered.slice(0, 10)); // Limit to 10 results
      setShowResults(true);
      setIsSearching(false);
    }, 50); // Small delay for smooth UI update
  }, [allVisits, filterVisits]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);

    // Debounce search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (value.trim()) {
      searchTimeoutRef.current = setTimeout(() => {
        performSearch(value);
      }, 300);
    } else {
      setSearchResults([]);
      setShowResults(false);
    }
  };

  const handleVisitClick = (visit: Visit) => {
    if (visit.status === 'OPEN') {
      onVisitSelect(visit.id);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowResults(false);
  };

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    if (showResults) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showResults]);

  return (
    <div className={styles.searchContainer} ref={searchContainerRef}>
      <div className={styles.searchInputWrapper}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search by patient name, visit ID, or patient ID..."
          value={searchQuery}
          onChange={handleSearchChange}
          onFocus={() => searchQuery.trim() && setShowResults(true)}
        />
        {searchQuery && (
          <button
            type="button"
            className={styles.clearSearchButton}
            onClick={handleClearSearch}
            aria-label="Clear search"
          >
            ×
          </button>
        )}
        {isSearching && allVisits.length === 0 && <span className={styles.searchSpinner}>🔍</span>}
      </div>

      {showResults && (
        <div className={styles.searchResults}>
          {searchResults.length === 0 ? (
            <div className={styles.noResults}>
              <p>No visits found matching "{searchQuery}"</p>
            </div>
          ) : (
            <div className={styles.searchResultsList}>
              {searchResults.map((visit) => (
                <div
                  key={visit.id}
                  className={`${styles.searchResultItem} ${visit.status === 'OPEN' ? styles.clickable : ''}`}
                  onClick={() => handleVisitClick(visit)}
                >
                  <div className={styles.searchResultInfo}>
                    <h4>Visit #{visit.id} - {visit.patient_name || 'Unknown'}</h4>
                    <p>
                      {visit.patient_id && `Patient ID: ${visit.patient_id} • `}
                      {new Date(visit.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className={styles.searchResultBadges}>
                    <span className={visit.status === 'OPEN' ? styles.badgeOpen : styles.badgeClosed}>
                      {visit.status}
                    </span>
                    <span className={visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED' ? styles.badgeCleared : styles.badgePending}>
                      {visit.payment_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!searchQuery && (
        <div className={styles.searchHint}>
          <p>💡 Tip: Search by patient name, visit ID, or patient ID to quickly find visits</p>
        </div>
      )}
    </div>
  );
});

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showError } = useToast();
  const lastLoadTimeRef = useRef<number>(0);

  const [recentVisits, setRecentVisits] = useState<Visit[]>([]);
  const [stats, setStats] = useState({
    totalVisits: 0,
    openVisits: 0,
    pendingPayments: 0,
    pendingVerifications: 0,
  });
  const [loading, setLoading] = useState(true);

  // Enable keyboard shortcuts
  useDefaultKeyboardShortcuts();

  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchVisits();
      const allVisits = Array.isArray(response) ? response : (response as PaginatedResponse<Visit>).results;

      const openVisits = allVisits.filter((v: Visit) => v.status === 'OPEN');
      const pendingPayments = allVisits.filter((v: Visit) => v.payment_status === 'UNPAID' || v.payment_status === 'PARTIALLY_PAID' || v.payment_status === 'INSURANCE_PENDING');

      // Fetch pending verifications for receptionists
      let pendingVerifications = 0;
      if (user?.role === 'RECEPTIONIST') {
        try {
          const pendingPatients = await getPendingVerificationPatients();
          pendingVerifications = pendingPatients.length;
        } catch (error) {
          // Silently fail - don't block dashboard loading
          console.warn('Failed to fetch pending verifications:', error);
        }
      }

      const newStats = {
        totalVisits: allVisits.length,
        openVisits: openVisits.length,
        pendingPayments: pendingPayments.length,
        pendingVerifications,
      };
      setStats(newStats);

      // Get 5 most recent visits
      const recent = allVisits
        .sort((a: Visit, b: Visit) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5);
      setRecentVisits(recent);
    } catch (error) {
      console.error('📊 Dashboard: Error loading data:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load dashboard data';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [showError, user?.role]);

  // Simple and reliable: Always reload when on dashboard route (with debounce)
  // This is the most reliable approach - no complex tracking needed
  useEffect(() => {
    // Only proceed if we're on the dashboard route
    if (location.pathname !== '/dashboard') {
      return;
    }

    const now = Date.now();
    const lastLoadTime = lastLoadTimeRef.current;
    const timeSinceLastLoad = lastLoadTime === 0 ? Infinity : now - lastLoadTime;
    
    // Reload if it's been more than 500ms since last load (prevents rapid duplicate calls)
    // This ensures fresh data on every navigation to dashboard
    if (timeSinceLastLoad > 500) {
      // Reset loading state
      setLoading(true);
      // Reset stats and visits to show loading state
      setStats({
        totalVisits: 0,
        openVisits: 0,
        pendingPayments: 0,
        pendingVerifications: 0,
      });
      setRecentVisits([]);
      
      // Load data
      loadDashboardData();
      lastLoadTimeRef.current = now;
    }
  }, [loadDashboardData, location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getRoleDashboard = () => {
    switch (user?.role) {
      case 'DOCTOR':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Doctor Dashboard</h2>
              <p>Welcome back, Dr. {user?.first_name} {user?.last_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>📋</div>
                <div className={styles.statInfo}>
                  <h3>{stats.openVisits}</h3>
                  <p>Open Visits</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>✅</div>
                <div className={styles.statInfo}>
                  <h3>{stats.totalVisits}</h3>
                  <p>Total Visits</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits')}
                >
                  <h3>View All Visits</h3>
                  <p>View and manage patient visits</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/inpatients')}
                >
                  <h3>Inpatients</h3>
                  <p>View all currently admitted patients</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/appointments')}
                >
                  <h3>My Appointments</h3>
                  <p>View and manage your appointments</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/telemedicine')}
                >
                  <h3>📹 Telemedicine</h3>
                  <p>Video consultations with patients</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits/new')}
                >
                  <h3>New Visit</h3>
                  <p>Create a new patient visit</p>
                </div>
                {user?.is_superuser && (
                  <>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/audit-logs')}
                    >
                      <h3>Audit Logs</h3>
                      <p>View system activity logs</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/health')}
                    >
                      <h3>System Health</h3>
                      <p>Monitor system status and health</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/reports')}
                    >
                      <h3>Reports & Analytics</h3>
                      <p>View comprehensive reports and analytics</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/backups')}
                    >
                      <h3>Backup & Restore</h3>
                      <p>Manage data backups and restores</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/service-catalog')}
                    >
                      <h3>Service Catalog</h3>
                      <p>Add and manage billable services (e.g. Telemedicine)</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/reconciliation')}
                    >
                      <h3>End-of-Day Reconciliation</h3>
                      <p>Daily revenue reconciliation and closure</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Recent Visits</h3>
                <button 
                  className={styles.viewAllButton}
                  onClick={() => navigate('/visits')}
                >
                  View All
                </button>
              </div>
              {loading ? (
                <LoadingSkeleton count={3} />
              ) : recentVisits.length === 0 ? (
                <p className={styles.emptyMessage}>No recent visits</p>
              ) : (
                <div className={styles.recentList}>
                  {recentVisits.map((visit) => (
                    <div
                      key={visit.id}
                      className={styles.recentItem}
                      onClick={() => navigate(`/visits/${visit.id}`)}
                    >
                      <div className={styles.recentItemInfo}>
                        <h4>Visit #{visit.id} - {visit.patient_name || 'Unknown'}</h4>
                        <p>{new Date(visit.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className={styles.recentItemBadges}>
                        <span className={visit.status === 'OPEN' ? styles.badgeOpen : styles.badgeClosed}>
                          {visit.status}
                        </span>
                        <span className={visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED' ? styles.badgeCleared : styles.badgePending}>
                          {visit.payment_status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      case 'NURSE':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Nurse Dashboard</h2>
              <p>Welcome back, {user?.first_name} {user?.last_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>📋</div>
                <div className={styles.statInfo}>
                  <h3>{stats.openVisits}</h3>
                  <p>Open Visits</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>✅</div>
                <div className={styles.statInfo}>
                  <h3>{stats.totalVisits}</h3>
                  <p>Total Visits</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits')}
                >
                  <h3>📋 View All Visits</h3>
                  <p>Browse and access all patient visits</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits?status=OPEN&payment_status=CLEARED')}
                >
                  <h3>🏥 Active Visits</h3>
                  <p>View open visits ready for nursing care</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Nursing Care Features</h3>
              </div>
              <div className={styles.infoBox}>
                <p><strong>As a Nurse, you can:</strong></p>
                <ul>
                  <li>📊 Record vital signs (temperature, BP, heart rate, etc.)</li>
                  <li>📝 Create nursing notes (admission, shift handover, procedures, etc.)</li>
                  <li>💊 Administer medications from existing prescriptions</li>
                  <li>🧪 Collect lab samples from existing lab orders</li>
                  <li>📚 Provide patient education</li>
                </ul>
                <p className={styles.helpText}>
                  <strong>Note:</strong> You can only perform actions on visits that are <strong>OPEN</strong> and have <strong>payment CLEARED</strong>. 
                  Click on any open visit to access the nursing care interface.
                </p>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Search Visits</h3>
              </div>
              <VisitSearchSection 
                onVisitSelect={(visitId) => navigate(`/visits/${visitId}/nursing`)}
                loading={loading}
              />
            </div>
          </div>
        );
      case 'RECEPTIONIST':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Receptionist Dashboard</h2>
              <p>Welcome back, {user?.first_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>👥</div>
                <div className={styles.statInfo}>
                  <h3>{stats.totalVisits}</h3>
                  <p>Total Visits</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>💰</div>
                <div className={styles.statInfo}>
                  <h3>{stats.pendingPayments}</h3>
                  <p>Pending Payments</p>
                </div>
              </div>
              {stats.pendingVerifications > 0 && (
                <div className={styles.statCard}>
                  <div className={styles.statIcon}>✓</div>
                  <div className={styles.statInfo}>
                    <h3>{stats.pendingVerifications}</h3>
                    <p>Pending Verifications</p>
                  </div>
                </div>
              )}
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patients/register')}
                >
                  <h3>Patient Registration</h3>
                  <p>Register new patients</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patients')}
                >
                  <h3>Patient Management</h3>
                  <p>Search and manage patients</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/appointments')}
                >
                  <h3>Appointments</h3>
                  <p>Schedule and manage appointments</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits/new')}
                >
                  <h3>Create Visit</h3>
                  <p>Create a new visit for a patient</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/visits')}
                >
                  <h3>Billing & Payments</h3>
                  <p>Access visit-scoped billing from visit details</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/billing/pending-queue')}
                >
                  <h3>Pending Queue</h3>
                  <p>Central billing queue – collect post-consultation payments</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patients/verification')}
                >
                  <h3>
                    Patient Verification
                    {stats.pendingVerifications > 0 && (
                      <span className={styles.badge}>{stats.pendingVerifications}</span>
                    )}
                  </h3>
                  <p>Verify patient portal accounts</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/reconciliation')}
                >
                  <h3>End-of-Day Reconciliation</h3>
                  <p>Daily revenue reconciliation and closure</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Recent Visits</h3>
              </div>
              {loading ? (
                <LoadingSkeleton count={3} />
              ) : recentVisits.length === 0 ? (
                <p className={styles.emptyMessage}>No recent visits</p>
              ) : (
                <div className={styles.recentList}>
                  {recentVisits.map((visit) => (
                    <div key={visit.id} className={styles.recentItem}>
                      <div className={styles.recentItemInfo}>
                        <h4>Visit #{visit.id} - {visit.patient_name || 'Unknown'}</h4>
                        <p>{new Date(visit.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className={styles.recentItemBadges}>
                        <span className={visit.status === 'OPEN' ? styles.badgeOpen : styles.badgeClosed}>
                          {visit.status}
                        </span>
                        <span className={visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED' ? styles.badgeCleared : styles.badgePending}>
                          {visit.payment_status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      case 'LAB_TECH':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Lab Technician Dashboard</h2>
              <p>Welcome back, {user?.first_name}</p>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/lab-orders')}
                >
                  <h3>Lab Orders</h3>
                  <p>View and process lab orders</p>
                </div>
              </div>
            </div>
          </div>
        );
      case 'RADIOLOGY_TECH':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Radiology Technician Dashboard</h2>
              <p>Welcome back, {user?.first_name}</p>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/radiology-orders')}
                >
                  <h3>Radiology Orders</h3>
                  <p>View and process radiology orders</p>
                </div>
              </div>
            </div>
          </div>
        );
      case 'PHARMACIST':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Pharmacist Dashboard</h2>
              <p>Welcome back, {user?.first_name}</p>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/prescriptions')}
                >
                  <h3>Prescriptions</h3>
                  <p>View and dispense prescriptions</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/drugs')}
                >
                  <h3>Drug Catalog</h3>
                  <p>Manage drugs and medications</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/inventory')}
                >
                  <h3>Inventory Management</h3>
                  <p>Track stock levels and manage inventory</p>
                </div>
              </div>
            </div>
          </div>
        );
      case 'PATIENT':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Patient Portal</h2>
              <p>Welcome back, {user?.first_name}</p>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patient-portal')}
                >
                  <h3>My Health Records</h3>
                  <p>View your medical history and records</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patient-portal/appointments')}
                >
                  <h3>My Appointments</h3>
                  <p>View and manage your appointments</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patient-portal/prescriptions')}
                >
                  <h3>My Prescriptions</h3>
                  <p>View your prescriptions</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patient-portal/lab-results')}
                >
                  <h3>Lab Results</h3>
                  <p>View your lab test results</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/wallet')}
                >
                  <h3>💰 My Wallet</h3>
                  <p>View balance and top up wallet</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patient-portal/telemedicine')}
                >
                  <h3>📹 Telemedicine</h3>
                  <p>Join video consultations</p>
                </div>
              </div>
            </div>
          </div>
        );
      case 'ADMIN':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Admin Dashboard</h2>
              <p>Welcome back, {user?.first_name} {user?.last_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>👥</div>
                <div className={styles.statInfo}>
                  <h3>{stats.totalVisits}</h3>
                  <p>Total Visits</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>📋</div>
                <div className={styles.statInfo}>
                  <h3>{stats.openVisits}</h3>
                  <p>Open Visits</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>💰</div>
                <div className={styles.statInfo}>
                  <h3>{stats.pendingPayments}</h3>
                  <p>Pending Payments</p>
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>✅</div>
                <div className={styles.statInfo}>
                  <h3>{stats.totalVisits - stats.openVisits}</h3>
                  <p>Closed Visits</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
                <div className={styles.actionCards}>
                  <div 
                    className={styles.actionCard}
                    onClick={() => navigate('/patients/register')}
                  >
                    <h3>Patient Registration</h3>
                    <p>Register new patients</p>
                  </div>
                  <div 
                    className={styles.actionCard}
                    onClick={() => navigate('/patients')}
                  >
                    <h3>Patient Management</h3>
                    <p>View and manage all patients</p>
                  </div>
                  <div 
                    className={styles.actionCard}
                    onClick={() => navigate('/visits')}
                  >
                    <h3>Visit Management</h3>
                    <p>View and manage all visits</p>
                  </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/reports')}
                >
                  <h3>Reports & Analytics</h3>
                  <p>View comprehensive reports and analytics</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/billing/revenue-leaks')}
                >
                  <h3>Revenue Leak Detection</h3>
                  <p>Monitor and resolve revenue leaks</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/reconciliation')}
                >
                  <h3>End-of-Day Reconciliation</h3>
                  <p>Daily revenue reconciliation and closure</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/service-catalog')}
                >
                  <h3>Service Catalog</h3>
                  <p>Add and manage billable services (e.g. Telemedicine)</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/radiology/upload-status')}
                >
                  <h3>Radiology Upload Status</h3>
                  <p>Monitor radiology image uploads</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/appointments')}
                >
                  <h3>Appointments</h3>
                  <p>Schedule and manage appointments</p>
                </div>
                {user?.is_superuser && (
                  <>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/audit-logs')}
                    >
                      <h3>Audit Logs</h3>
                      <p>View system activity logs</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/backups')}
                    >
                      <h3>Backup & Restore</h3>
                      <p>Manage data backups and restores</p>
                    </div>
                    <div 
                      className={styles.actionCard}
                      onClick={() => navigate('/health')}
                    >
                      <h3>System Health</h3>
                      <p>Monitor system status and health</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Recent Visits</h3>
              </div>
              {loading ? (
                <LoadingSkeleton count={3} />
              ) : recentVisits.length === 0 ? (
                <p className={styles.emptyMessage}>No recent visits</p>
              ) : (
                <div className={styles.recentList}>
                  {recentVisits.map((visit) => (
                    <div key={visit.id} className={styles.recentItem}>
                      <div className={styles.recentItemInfo}>
                        <h4>Visit #{visit.id} - {visit.patient_name || 'Unknown'}</h4>
                        <p>{new Date(visit.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className={styles.recentItemBadges}>
                        <span className={visit.status === 'OPEN' ? styles.badgeOpen : styles.badgeClosed}>
                          {visit.status}
                        </span>
                      </div>
                      <button
                        className={styles.viewButton}
                        onClick={() => navigate(`/visits/${visit.id}`)}
                      >
                        View Details
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case 'IVF_SPECIALIST':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>IVF Specialist Dashboard</h2>
              <p>Welcome back, Dr. {user?.first_name} {user?.last_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>🔬</div>
                <div className={styles.statInfo}>
                  <h3>IVF Center</h3>
                  <p>Reproductive Medicine</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf')}
                >
                  <h3>🔬 IVF Dashboard</h3>
                  <p>View IVF cycles and statistics</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf/cycles')}
                >
                  <h3>📋 All IVF Cycles</h3>
                  <p>Manage patient IVF cycles</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf/cycles/new')}
                >
                  <h3>➕ New IVF Cycle</h3>
                  <p>Start a new IVF treatment cycle</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf/visits')}
                >
                  <h3>📅 IVF Patient Visits</h3>
                  <p>View visits for IVF patients only</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf/patients')}
                >
                  <h3>👥 IVF Patients</h3>
                  <p>Patients with at least one IVF cycle</p>
                </div>
              </div>
            </div>
          </div>
        );

      case 'EMBRYOLOGIST':
        return (
          <div className={styles.dashboardContent}>
            <div className={styles.dashboardHeader}>
              <h2>Embryologist Dashboard</h2>
              <p>Welcome back, {user?.first_name} {user?.last_name}</p>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}>🧬</div>
                <div className={styles.statInfo}>
                  <h3>Lab</h3>
                  <p>Embryology Laboratory</p>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h3>Quick Actions</h3>
              </div>
              <div className={styles.actionCards}>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf')}
                >
                  <h3>🔬 IVF Dashboard</h3>
                  <p>View IVF cycles and statistics</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/ivf/cycles')}
                >
                  <h3>🧬 Active Cycles</h3>
                  <p>View cycles requiring lab work</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/patients')}
                >
                  <h3>👥 Patient Management</h3>
                  <p>View and manage patients</p>
                </div>
                <div 
                  className={styles.actionCard}
                  onClick={() => navigate('/lab-orders')}
                >
                  <h3>🧪 Lab Orders</h3>
                  <p>View laboratory orders</p>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className={styles.dashboardContent}>
            <h2>Dashboard</h2>
            <p>Welcome to Lifeway Medical Centre Ltd</p>
          </div>
        );
    }
  };

  return (
    <div className={styles.dashboard}>
      <header className={styles.dashboardHeader}>
        <div className={styles.headerContent}>
          <Logo size="medium" showText={false} />
          <h1>Lifeway Medical Centre Ltd</h1>
          <div className={styles.userInfo}>
            <ThemeToggle />
            <NotificationBell />
            <span>{user?.first_name} {user?.last_name} ({user?.role})</span>
            <button onClick={handleLogout} className={styles.logoutButton}>
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className={styles.dashboardMain}>
        {getRoleDashboard()}
      </main>
    </div>
  );
}
