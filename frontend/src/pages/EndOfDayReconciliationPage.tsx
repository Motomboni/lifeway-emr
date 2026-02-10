/**
 * End-of-Day Reconciliation Page
 * 
 * Provides daily reconciliation interface for Admin and Receptionist.
 * Shows revenue summary, outstanding items, and staff sign-off.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  createReconciliation,
  getTodayReconciliation,
  finalizeReconciliation,
  refreshReconciliation,
  EndOfDayReconciliation,
} from '../api/reconciliation';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import { logger } from '../utils/logger';
import {
  FaMoneyBillWave,
  FaCashRegister,
  FaCreditCard,
  FaWallet,
  FaHospital,
  FaExclamationTriangle,
  FaCheckCircle,
  FaPrint,
  FaLock,
  FaSync,
  FaCalendarCheck,
} from 'react-icons/fa';
import styles from '../styles/EndOfDayReconciliation.module.css';

export default function EndOfDayReconciliationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  
  const [reconciliation, setReconciliation] = useState<EndOfDayReconciliation | null>(null);
  const [loading, setLoading] = useState(true);
  const [finalizing, setFinalizing] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmationChecked, setConfirmationChecked] = useState(false);
  const [staffName, setStaffName] = useState('');
  const [notes, setNotes] = useState('');
  
  // Check access
  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    
    if (user.role !== 'ADMIN' && user.role !== 'RECEPTIONIST') {
      showError('Access denied. This page is only available to Admin and Receptionist.');
      navigate('/dashboard');
      return;
    }
    
    if (user) {
      // Get user's full name
      const fullName = user.first_name && user.last_name
        ? `${user.first_name} ${user.last_name}`
        : user.username || 'User';
      setStaffName(fullName);
    }
  }, [user, navigate, showError]);
  
  // Load today's reconciliation
  useEffect(() => {
    if (!user || (user.role !== 'ADMIN' && user.role !== 'RECEPTIONIST')) {
      return;
    }
    
    loadReconciliation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);
  
  const loadReconciliation = async (forceCreate: boolean = false) => {
    try {
      setLoading(true);
      
      if (!forceCreate) {
        // Try to get today's reconciliation first
        const today = await getTodayReconciliation();
        if (today) {
          setReconciliation(today);
          return;
        }
      }
      
      // Create new reconciliation for today
      const newReconciliation = await createReconciliation({
        reconciliation_date: new Date().toISOString().split('T')[0],
        close_active_visits: true,
      });
      setReconciliation(newReconciliation);
      showSuccess('Reconciliation created successfully.');
    } catch (error: any) {
      const errorMessage = error.message || error.data?.error || 'Failed to load reconciliation data.';
      showError(errorMessage);
      logger.error('Error loading reconciliation:', error);
      // Don't set reconciliation to null on error - keep existing if any
    } finally {
      setLoading(false);
    }
  };
  
  const handleRefresh = async () => {
    if (!reconciliation) return;
    
    try {
      const refreshed = await refreshReconciliation(reconciliation.id);
      setReconciliation(refreshed);
      showSuccess('Reconciliation data refreshed.');
    } catch (error: any) {
      const errorMessage = error.message || error.data?.error || 'Failed to refresh reconciliation.';
      showError(errorMessage);
      logger.error('Error refreshing reconciliation:', error);
    }
  };
  
  const handleFinalize = async () => {
    if (!reconciliation || !confirmationChecked) {
      return;
    }
    
    try {
      setFinalizing(true);
      const finalized = await finalizeReconciliation(reconciliation.id, notes);
      setReconciliation(finalized);
      setShowConfirmDialog(false);
      setConfirmationChecked(false);
      showSuccess('Reconciliation finalized successfully.');
    } catch (error: any) {
      const errorMessage = error.message || error.data?.error || 'Failed to finalize reconciliation.';
      showError(errorMessage);
      logger.error('Error finalizing reconciliation:', error);
    } finally {
      setFinalizing(false);
    }
  };
  
  const handlePrint = () => {
    window.print();
  };
  
  const formatCurrency = (amount: string | number): string => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 2,
    }).format(numAmount);
  };
  
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-NG', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };
  
  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-NG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  const isFinalized = reconciliation?.status === 'FINALIZED';
  const canEdit = !isFinalized;
  
  if (!user || (user.role !== 'ADMIN' && user.role !== 'RECEPTIONIST')) {
    return null;
  }
  
  if (loading) {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <LoadingSkeleton />
      </div>
    );
  }
  
  if (!reconciliation) {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <div className={styles.emptyState}>
          <p>No reconciliation found for today.</p>
          <button 
            onClick={() => loadReconciliation(true)} 
            className={styles.createButton}
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Reconciliation'}
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className={styles.page}>
      <BackToDashboard />
      
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1>End-of-Day Reconciliation</h1>
          <p className={styles.subtitle}>
            {formatDate(reconciliation.reconciliation_date)}
          </p>
        </div>
        <div className={styles.headerRight}>
          {canEdit && (
            <button
              onClick={handleRefresh}
              className={styles.refreshButton}
              title="Refresh calculations"
            >
              <FaSync size={16} /> Refresh
            </button>
          )}
          <button
            onClick={handlePrint}
            className={styles.printButton}
            title="Print summary"
          >
            <FaPrint size={16} /> Print
          </button>
          {isFinalized && (
            <div className={styles.finalizedBadge}>
              <FaLock size={16} /> Finalized
            </div>
          )}
        </div>
      </div>
      
      {/* Status Banner */}
      {isFinalized && (
        <div className={styles.finalizedBanner}>
          <FaCheckCircle size={20} />
          <div>
            <strong>This reconciliation has been finalized</strong>
            <p>
              Finalized by {reconciliation.finalized_by_name} on{' '}
              {reconciliation.finalized_at && formatDateTime(reconciliation.finalized_at)}
            </p>
          </div>
        </div>
      )}
      
      {/* Summary Cards */}
      <div className={styles.summarySection}>
        <h2>Revenue Summary</h2>
        <div className={styles.summaryCards}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#4caf50' }}>
              <FaMoneyBillWave size={24} />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Total Revenue</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(reconciliation.total_revenue)}
              </div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#2196f3' }}>
              <FaCashRegister size={24} />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Cash</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(reconciliation.total_cash)}
              </div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#9c27b0' }}>
              <FaCreditCard size={24} />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Paystack</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(reconciliation.total_paystack)}
              </div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#ff9800' }}>
              <FaWallet size={24} />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Wallet</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(reconciliation.total_wallet)}
              </div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#00bcd4' }}>
              <FaHospital size={24} />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>HMO</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(reconciliation.total_hmo)}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Outstanding Items */}
      <div className={styles.outstandingSection}>
        <h2>Outstanding Items</h2>
        
        <div className={styles.outstandingCards}>
          <div className={styles.outstandingCard}>
            <div className={styles.outstandingCardHeader}>
              <FaExclamationTriangle className={styles.warningIcon} size={20} />
              <h3>Unpaid Services</h3>
            </div>
            <div className={styles.outstandingCardContent}>
              <div className={styles.outstandingAmount}>
                {formatCurrency(reconciliation.total_outstanding)}
              </div>
              <div className={styles.outstandingCount}>
                {reconciliation.outstanding_visits_count} visit(s) with outstanding balances
              </div>
            </div>
          </div>
          
          <div className={styles.outstandingCard}>
            <div className={styles.outstandingCardHeader}>
              <FaExclamationTriangle className={styles.warningIcon} size={20} />
              <h3>Revenue Leaks</h3>
            </div>
            <div className={styles.outstandingCardContent}>
              <div className={styles.outstandingAmount}>
                {formatCurrency(reconciliation.revenue_leaks_amount)}
              </div>
              <div className={styles.outstandingCount}>
                {reconciliation.revenue_leaks_detected} leak(s) detected
              </div>
            </div>
          </div>
        </div>
        
        {/* Detailed Outstanding Items Table */}
        {reconciliation.reconciliation_details?.outstanding?.items && 
         reconciliation.reconciliation_details.outstanding.items.length > 0 && (
          <div style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '15px', color: '#212121', fontSize: '16px', fontWeight: '600' }}>
              Outstanding Items Breakdown
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', minWidth: '1000px', color: '#212121' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f5f5f5' }}>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Visit ID</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Patient</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>MRN</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Visit Status</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Service</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Service Code</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Amount</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Paid</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Outstanding</th>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {reconciliation.reconciliation_details.outstanding.items.map((visitOutstanding: any, visitIndex: number) => (
                    visitOutstanding.items.map((item: any, itemIndex: number) => (
                      <tr 
                        key={`${visitOutstanding.visit_id}-${item.id}`}
                        style={{ 
                          backgroundColor: (visitIndex + itemIndex) % 2 === 0 ? '#fff' : '#fafafa',
                          borderTop: itemIndex === 0 ? '2px solid #ddd' : 'none'
                        }}
                      >
                        {itemIndex === 0 && (
                          <>
                            <td 
                              rowSpan={visitOutstanding.items.length}
                              style={{ 
                                padding: '10px', 
                                border: '1px solid #ddd', 
                                color: '#212121',
                                fontWeight: '600',
                                verticalAlign: 'top'
                              }}
                            >
                              {visitOutstanding.visit_id}
                            </td>
                            <td 
                              rowSpan={visitOutstanding.items.length}
                              style={{ 
                                padding: '10px', 
                                border: '1px solid #ddd', 
                                color: '#212121',
                                verticalAlign: 'top'
                              }}
                            >
                              {visitOutstanding.patient?.name || <span style={{ color: '#999' }}>N/A</span>}
                            </td>
                            <td 
                              rowSpan={visitOutstanding.items.length}
                              style={{ 
                                padding: '10px', 
                                border: '1px solid #ddd', 
                                fontFamily: 'monospace',
                                fontSize: '12px',
                                color: '#424242',
                                verticalAlign: 'top'
                              }}
                            >
                              {visitOutstanding.patient?.mrn || <span style={{ color: '#999' }}>N/A</span>}
                            </td>
                            <td 
                              rowSpan={visitOutstanding.items.length}
                              style={{ 
                                padding: '10px', 
                                border: '1px solid #ddd', 
                                color: '#212121',
                                verticalAlign: 'top'
                              }}
                            >
                              {visitOutstanding.visit_status || <span style={{ color: '#999' }}>N/A</span>}
                            </td>
                          </>
                        )}
                        <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                          {item.service_name}
                        </td>
                        <td style={{ padding: '10px', border: '1px solid #ddd', fontFamily: 'monospace', fontSize: '11px', color: '#424242' }}>
                          {item.service_code}
                        </td>
                        <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                          {formatCurrency(item.amount)}
                        </td>
                        <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                          {formatCurrency(item.amount_paid)}
                        </td>
                        <td style={{ padding: '10px', border: '1px solid #ddd', fontWeight: '600', color: '#d32f2f' }}>
                          {formatCurrency(item.outstanding_amount)}
                        </td>
                        <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            backgroundColor: item.bill_status === 'PARTIALLY_PAID' ? '#fff3e0' : '#ffebee',
                            color: item.bill_status === 'PARTIALLY_PAID' ? '#e65100' : '#c62828',
                          }}>
                            {item.bill_status}
                          </span>
                        </td>
                      </tr>
                    ))
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ backgroundColor: '#fff3e0', fontWeight: '600' }}>
                    <td colSpan={6} style={{ padding: '12px', border: '1px solid #ddd', textAlign: 'right', color: '#212121' }}>
                      Total Outstanding:
                    </td>
                    <td colSpan={4} style={{ padding: '12px', border: '1px solid #ddd', color: '#d32f2f', fontSize: '14px' }}>
                      {formatCurrency(reconciliation.total_outstanding)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </div>
      
      {/* Visit Statistics */}
      <div className={styles.statsSection}>
        <h2>Visit Statistics</h2>
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>Total Visits</span>
            <span className={styles.statValue}>{reconciliation.total_visits}</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>Active Visits Closed</span>
            <span className={styles.statValue}>{reconciliation.active_visits_closed}</span>
          </div>
          {reconciliation.reconciliation_details?.visits?.by_status && (
            <>
              {Object.entries(reconciliation.reconciliation_details.visits.by_status).map(([status, count]: [string, any]) => (
                <div key={status} className={styles.statItem}>
                  <span className={styles.statLabel}>{status} Visits</span>
                  <span className={styles.statValue}>{count}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
      
      {/* Comprehensive Payment Details Section */}
      {reconciliation.reconciliation_details?.payments && (
        <div className={styles.statsSection}>
          <h2>Payment Transactions</h2>
          <p style={{ marginBottom: '15px', color: '#666', fontSize: '14px' }}>
            {reconciliation.reconciliation_details.payments.count} payment(s) totaling{' '}
            <strong>{formatCurrency(reconciliation.reconciliation_details.payments.total_sum)}</strong>
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', minWidth: '1200px', color: '#212121' }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5' }}>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Payment ID</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Amount</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Method</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Status</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Patient</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>MRN</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Visit ID</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Visit Status</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Services</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Processed By</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Reference</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd', fontWeight: '600', color: '#212121' }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {reconciliation.reconciliation_details.payments.items.map((payment: any, index: number) => (
                  <tr key={payment.id} style={{ backgroundColor: index % 2 === 0 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>{payment.id}</td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', fontWeight: '600', color: '#2e7d32' }}>
                      {formatCurrency(payment.amount)}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>{payment.payment_method}</td>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '600',
                        backgroundColor: payment.status === 'CLEARED' ? '#e8f5e9' : '#fff3e0',
                        color: payment.status === 'CLEARED' ? '#1b5e20' : '#e65100',
                      }}>
                        {payment.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                      {payment.patient?.name || <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', fontFamily: 'monospace', fontSize: '12px', color: '#424242' }}>
                      {payment.patient?.mrn || <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                      {payment.visit?.id || <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', color: '#212121' }}>
                      {payment.visit?.status || <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', maxWidth: '200px' }}>
                      {payment.billing_items && payment.billing_items.length > 0 ? (
                        <div style={{ fontSize: '11px' }}>
                          <div style={{ marginBottom: '4px', fontWeight: '600', color: '#212121' }}>
                            {payment.billing_items_count} item(s)
                          </div>
                          <div style={{ maxHeight: '100px', overflowY: 'auto' }}>
                            {payment.billing_items.slice(0, 3).map((item: any, idx: number) => (
                              <div key={idx} style={{ marginBottom: '2px', color: '#424242' }}>
                                • {item.service_name} ({formatCurrency(item.amount)})
                              </div>
                            ))}
                            {payment.billing_items.length > 3 && (
                              <div style={{ color: '#757575', fontStyle: 'italic' }}>
                                +{payment.billing_items.length - 3} more...
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>No items</span>
                      )}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', fontSize: '12px', color: '#212121' }}>
                      {payment.processed_by?.name || payment.processed_by?.username || <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', fontFamily: 'monospace', fontSize: '11px', color: '#424242' }}>
                      {payment.transaction_reference || <span style={{ color: '#999' }}>-</span>}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd', fontSize: '12px', color: '#212121' }}>
                      {payment.created_at ? formatDateTime(payment.created_at) : <span style={{ color: '#999' }}>N/A</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {reconciliation.reconciliation_details.payments.items.length === 0 && (
            <p style={{ padding: '20px', textAlign: 'center', color: '#999' }}>
              No payments found for this date.
            </p>
          )}
        </div>
      )}
      
      {/* Staff Sign-off Section */}
      <div className={styles.signoffSection}>
        <h2>Staff Sign-off</h2>
        
        <div className={styles.signoffCard}>
          <div className={styles.signoffRow}>
            <div className={styles.signoffItem}>
              <span className={styles.signoffLabel}>Prepared By:</span>
              <span className={styles.signoffValue}>
                {reconciliation.prepared_by_name || 'N/A'}
              </span>
              {reconciliation.prepared_at && (
                <span className={styles.signoffTime}>
                  {formatDateTime(reconciliation.prepared_at)}
                </span>
              )}
            </div>
            
            {reconciliation.reviewed_by_name && (
              <div className={styles.signoffItem}>
                <span className={styles.signoffLabel}>Reviewed By:</span>
                <span className={styles.signoffValue}>
                  {reconciliation.reviewed_by_name}
                </span>
                {reconciliation.reviewed_at && (
                  <span className={styles.signoffTime}>
                    {formatDateTime(reconciliation.reviewed_at)}
                  </span>
                )}
              </div>
            )}
            
            {reconciliation.finalized_by_name && (
              <div className={styles.signoffItem}>
                <span className={styles.signoffLabel}>Finalized By:</span>
                <span className={styles.signoffValue}>
                  {reconciliation.finalized_by_name}
                </span>
                {reconciliation.finalized_at && (
                  <span className={styles.signoffTime}>
                    {formatDateTime(reconciliation.finalized_at)}
                  </span>
                )}
              </div>
            )}
          </div>
          
          {canEdit && (
            <div className={styles.signoffForm}>
              <div className={styles.formGroup}>
                <label htmlFor="staffName">Your Name:</label>
                <input
                  id="staffName"
                  type="text"
                  value={staffName}
                  onChange={(e) => setStaffName(e.target.value)}
                  className={styles.formInput}
                  disabled={isFinalized}
                />
              </div>
              
              <div className={styles.formGroup}>
                <label htmlFor="notes">Notes (Optional):</label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className={styles.formTextarea}
                  rows={3}
                  placeholder="Add any notes about this reconciliation..."
                  disabled={isFinalized}
                />
              </div>
              
              <div className={styles.confirmationCheckbox}>
                <input
                  type="checkbox"
                  id="confirmation"
                  checked={confirmationChecked}
                  onChange={(e) => setConfirmationChecked(e.target.checked)}
                  disabled={isFinalized}
                />
                <label htmlFor="confirmation">
                  I confirm that all revenue has been reconciled and verified for{' '}
                  {formatDate(reconciliation.reconciliation_date)}
                </label>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Finalize Button */}
      {canEdit && (
        <div className={styles.actionsSection}>
          <button
            onClick={() => setShowConfirmDialog(true)}
            className={styles.finalizeButton}
            disabled={!confirmationChecked}
          >
            <FaCalendarCheck size={16} /> Finalize Day
          </button>
        </div>
      )}
      
      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className={styles.modalOverlay} onClick={() => setShowConfirmDialog(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Finalize Reconciliation</h2>
              <button
                onClick={() => setShowConfirmDialog(false)}
                className={styles.modalClose}
              >
                ×
              </button>
            </div>
            <div className={styles.modalContent}>
              <div className={styles.warningBox}>
                <FaExclamationTriangle size={24} />
                <div>
                  <strong>Warning: This action cannot be undone</strong>
                  <p>
                    Once finalized, this reconciliation cannot be edited. 
                    Please ensure all data is correct before proceeding.
                  </p>
                </div>
              </div>
              
              <div className={styles.confirmationSummary}>
                <h3>Reconciliation Summary</h3>
                <div className={styles.summaryRow}>
                  <span>Total Revenue:</span>
                  <strong>{formatCurrency(reconciliation.total_revenue)}</strong>
                </div>
                <div className={styles.summaryRow}>
                  <span>Outstanding:</span>
                  <strong>{formatCurrency(reconciliation.total_outstanding)}</strong>
                </div>
                <div className={styles.summaryRow}>
                  <span>Revenue Leaks:</span>
                  <strong>{formatCurrency(reconciliation.revenue_leaks_amount)}</strong>
                </div>
              </div>
              
              <div className={styles.modalActions}>
                <button
                  onClick={() => setShowConfirmDialog(false)}
                  className={styles.cancelButton}
                  disabled={finalizing}
                >
                  Cancel
                </button>
                <button
                  onClick={handleFinalize}
                  className={styles.confirmButton}
                  disabled={!confirmationChecked || finalizing}
                >
                  {finalizing ? 'Finalizing...' : 'Confirm Finalization'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Print Styles */}
      <style>{`
        @media print {
          .${styles.headerRight},
          .${styles.actionsSection},
          .${styles.modalOverlay} {
            display: none !important;
          }
          
          .${styles.page} {
            padding: 20px;
          }
          
          .${styles.summaryCards},
          .${styles.outstandingCards} {
            page-break-inside: avoid;
          }
        }
      `}</style>
    </div>
  );
}

