/**
 * Visit Timeline Component
 * 
 * Displays a chronological vertical timeline of all events for a visit.
 * Read-only, visit-scoped, with expandable items and sticky header.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchTimelineEvents, TimelineEvent } from '../../api/timeline';
import { getVisit } from '../../api/visits';
import { getPatient } from '../../api/patient';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';
import { useToast } from '../../hooks/useToast';
import LoadingSkeleton from '../common/LoadingSkeleton';
import {
  FaCalendarPlus,
  FaUserMd,
  FaTimesCircle,
  FaFlask,
  FaVial,
  FaXRay,
  FaFileMedical,
  FaPills,
  FaMoneyBillWave,
  FaProcedures,
  FaBed,
  FaNotesMedical,
  FaSyringe,
  FaMicroscope,
  FaFileUpload,
  FaShareSquare,
  FaFileAlt,
  FaHeartbeat,
  FaChevronDown,
  FaChevronUp,
  FaExternalLinkAlt,
} from 'react-icons/fa';
import styles from './VisitTimeline.module.css';

interface VisitTimelineProps {
  visitId: number;
  showHeader?: boolean;
  onEventClick?: (event: TimelineEvent) => void;
}

// Event type configurations
const EVENT_CONFIG: Record<string, {
  icon: JSX.Element;
  color: string;
  department: string;
  label: string;
}> = {
  VISIT_CREATED: {
    icon: <FaCalendarPlus size={16} />,
    color: '#4CAF50',
    department: 'GENERAL',
    label: 'Visit Created',
  },
  CONSULTATION_STARTED: {
    icon: <FaUserMd size={16} />,
    color: '#2196F3',
    department: 'GOPD',
    label: 'Consultation Started',
  },
  CONSULTATION_CLOSED: {
    icon: <FaTimesCircle size={16} />,
    color: '#F44336',
    department: 'GOPD',
    label: 'Consultation Closed',
  },
  SERVICE_SELECTED: {
    icon: <FaFileMedical size={16} />,
    color: '#FFC107',
    department: 'BILLING',
    label: 'Service Selected',
  },
  LAB_ORDERED: {
    icon: <FaFlask size={16} />,
    color: '#9C27B0',
    department: 'LAB',
    label: 'Lab Ordered',
  },
  LAB_RESULT_POSTED: {
    icon: <FaVial size={16} />,
    color: '#673AB7',
    department: 'LAB',
    label: 'Lab Result Posted',
  },
  RADIOLOGY_ORDERED: {
    icon: <FaXRay size={16} />,
    color: '#00BCD4',
    department: 'RADIOLOGY',
    label: 'Radiology Ordered',
  },
  RADIOLOGY_REPORT_POSTED: {
    icon: <FaFileMedical size={16} />,
    color: '#0097A7',
    department: 'RADIOLOGY',
    label: 'Radiology Report Posted',
  },
  DRUG_DISPENSED: {
    icon: <FaPills size={16} />,
    color: '#FF5722',
    department: 'PHARMACY',
    label: 'Drug Dispensed',
  },
  PAYMENT_CONFIRMED: {
    icon: <FaMoneyBillWave size={16} />,
    color: '#8BC34A',
    department: 'BILLING',
    label: 'Payment Confirmed',
  },
  PROCEDURE_ORDERED: {
    icon: <FaProcedures size={16} />,
    color: '#607D8B',
    department: 'CLINICAL',
    label: 'Procedure Ordered',
  },
  PROCEDURE_COMPLETED: {
    icon: <FaProcedures size={16} />,
    color: '#455A64',
    department: 'CLINICAL',
    label: 'Procedure Completed',
  },
  ADMISSION_CREATED: {
    icon: <FaBed size={16} />,
    color: '#795548',
    department: 'INPATIENT',
    label: 'Admission Created',
  },
  ADMISSION_DISCHARGED: {
    icon: <FaBed size={16} />,
    color: '#5D4037',
    department: 'INPATIENT',
    label: 'Admission Discharged',
  },
  ADMISSION_TRANSFERRED: {
    icon: <FaBed size={16} />,
    color: '#BCAAA4',
    department: 'INPATIENT',
    label: 'Admission Transferred',
  },
  VITAL_SIGNS_RECORDED: {
    icon: <FaHeartbeat size={16} />,
    color: '#E91E63',
    department: 'NURSING',
    label: 'Vital Signs Recorded',
  },
  NURSING_NOTE_ADDED: {
    icon: <FaNotesMedical size={16} />,
    color: '#607D8B',
    department: 'NURSING',
    label: 'Nursing Note Added',
  },
  MEDICATION_ADMINISTERED: {
    icon: <FaSyringe size={16} />,
    color: '#3F51B5',
    department: 'NURSING',
    label: 'Medication Administered',
  },
  LAB_SAMPLE_COLLECTED: {
    icon: <FaMicroscope size={16} />,
    color: '#7CB342',
    department: 'NURSING',
    label: 'Lab Sample Collected',
  },
  DOCUMENT_UPLOADED: {
    icon: <FaFileUpload size={16} />,
    color: '#757575',
    department: 'DOCUMENTS',
    label: 'Document Uploaded',
  },
  REFERRAL_CREATED: {
    icon: <FaShareSquare size={16} />,
    color: '#FF9800',
    department: 'REFERRALS',
    label: 'Referral Created',
  },
  DISCHARGE_SUMMARY_CREATED: {
    icon: <FaFileAlt size={16} />,
    color: '#CDDC39',
    department: 'DISCHARGE',
    label: 'Discharge Summary Created',
  },
};

// Department color mapping
const DEPARTMENT_COLORS: Record<string, string> = {
  GENERAL: '#4CAF50',
  GOPD: '#2196F3',
  LAB: '#9C27B0',
  RADIOLOGY: '#00BCD4',
  PHARMACY: '#FF5722',
  BILLING: '#8BC34A',
  CLINICAL: '#607D8B',
  INPATIENT: '#795548',
  NURSING: '#E91E63',
  DOCUMENTS: '#757575',
  REFERRALS: '#FF9800',
  DISCHARGE: '#CDDC39',
};

export default function VisitTimeline({ 
  visitId, 
  showHeader = true,
  onEventClick 
}: VisitTimelineProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [visit, setVisit] = useState<Visit | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());
  const { showError } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        const [eventsData, visitData] = await Promise.all([
          fetchTimelineEvents(visitId),
          getVisit(visitId),
        ]);
        
        setEvents(eventsData);
        setVisit(visitData);
        
        if (visitData.patient) {
          const patientData = await getPatient(visitData.patient);
          setPatient(patientData);
        }
      } catch (error) {
        showError('Failed to load timeline data.');
        console.error('Error loading timeline:', error);
      } finally {
        setLoading(false);
      }
    };

    if (visitId) {
      loadData();
    }
  }, [visitId, showError]);

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-NG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-NG', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const toggleExpand = (eventId: number) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedEvents(newExpanded);
  };

  const handleEventClick = (event: TimelineEvent) => {
    if (onEventClick) {
      onEventClick(event);
    } else if (event.source_object_url) {
      navigate(event.source_object_url);
    }
  };

  if (loading) {
    return (
      <div className={styles.timelineContainer}>
        {showHeader && (
          <div className={styles.header}>
            <LoadingSkeleton />
          </div>
        )}
        <LoadingSkeleton />
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className={styles.timelineContainer}>
        {showHeader && visit && patient && (
          <div className={styles.header}>
            <div className={styles.headerContent}>
              <div>
                <h2>{patient.first_name} {patient.last_name}</h2>
                <p className={styles.visitId}>Visit #{visit.id}</p>
              </div>
            </div>
          </div>
        )}
        <div className={styles.emptyState}>
          <p>No timeline events recorded yet.</p>
        </div>
      </div>
    );
  }

  const config = EVENT_CONFIG[events[0]?.event_type] || {
    icon: <FaCalendarPlus size={16} />,
    color: '#9E9E9E',
    department: 'GENERAL',
    label: 'Event',
  };

  return (
    <div className={styles.timelineContainer}>
      {/* Sticky Header */}
      {showHeader && visit && patient && (
        <div className={styles.header}>
          <div className={styles.headerContent}>
            <div className={styles.patientInfo}>
              <h2>{patient.first_name} {patient.last_name}</h2>
              <p className={styles.visitId}>Visit #{visit.id}</p>
            </div>
            <div className={styles.visitInfo}>
              <span className={styles.visitType}>{visit.visit_type}</span>
              <span className={`${styles.visitStatus} ${styles[visit.status.toLowerCase()]}`}>
                {visit.status}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className={styles.timeline}>
        {events.map((event, index) => {
          const eventConfig = EVENT_CONFIG[event.event_type] || {
            icon: <FaCalendarPlus size={16} />,
            color: '#9E9E9E',
            department: 'GENERAL',
            label: event.event_type_display || event.event_type,
          };
          
          const isExpanded = expandedEvents.has(event.id);
          const departmentColor = DEPARTMENT_COLORS[eventConfig.department] || eventConfig.color;

          return (
            <div key={event.id} className={styles.timelineItem}>
              {/* Timeline Line */}
              {index < events.length - 1 && (
                <div 
                  className={styles.timelineLine}
                  style={{ backgroundColor: departmentColor }}
                />
              )}

              {/* Timeline Dot */}
              <div
                className={styles.timelineDot}
                style={{ 
                  backgroundColor: departmentColor,
                  borderColor: departmentColor,
                }}
                onClick={() => toggleExpand(event.id)}
              >
                {eventConfig.icon}
              </div>

              {/* Timeline Content */}
              <div className={styles.timelineContent}>
                <div 
                  className={styles.timelineCard}
                  onClick={() => toggleExpand(event.id)}
                >
                  <div className={styles.timelineCardHeader}>
                    <div className={styles.timelineCardLeft}>
                      <div className={styles.eventType}>
                        <span 
                          className={styles.eventTypeLabel}
                          style={{ color: departmentColor }}
                        >
                          {eventConfig.label}
                        </span>
                        <span className={styles.eventDepartment}>
                          {eventConfig.department}
                        </span>
                      </div>
                      <div className={styles.eventDescription}>
                        {event.description}
                      </div>
                    </div>
                    <div className={styles.timelineCardRight}>
                      <div className={styles.eventTime}>
                        {formatTime(event.timestamp)}
                      </div>
                      <div className={styles.eventDate}>
                        {new Date(event.timestamp).toLocaleDateString('en-NG', {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </div>
                    </div>
                  </div>

                  {event.actor_full_name && (
                    <div className={styles.eventActor}>
                      <span className={styles.actorLabel}>By:</span>
                      <span className={styles.actorName}>{event.actor_full_name}</span>
                      {event.actor_role && (
                        <span className={styles.actorRole}>({event.actor_role})</span>
                      )}
                    </div>
                  )}

                  {/* Expand/Collapse Indicator */}
                  <div className={styles.expandIndicator}>
                    {isExpanded ? (
                      <FaChevronUp className={styles.expandIcon} size={14} />
                    ) : (
                      <FaChevronDown className={styles.expandIcon} size={14} />
                    )}
                    <span className={styles.expandText}>
                      {isExpanded ? 'Less details' : 'More details'}
                    </span>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className={styles.expandedDetails}>
                    <div className={styles.detailSection}>
                      <h4>Event Information</h4>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>Event Type:</span>
                        <span className={styles.detailValue}>{eventConfig.label}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>Department:</span>
                        <span className={styles.detailValue}>{eventConfig.department}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>Timestamp:</span>
                        <span className={styles.detailValue}>
                          {formatTimestamp(event.timestamp)}
                        </span>
                      </div>
                      {event.actor_full_name && (
                        <div className={styles.detailRow}>
                          <span className={styles.detailLabel}>Performed By:</span>
                          <span className={styles.detailValue}>
                            {event.actor_full_name} ({event.actor_role})
                          </span>
                        </div>
                      )}
                    </div>

                    {event.metadata && Object.keys(event.metadata).length > 0 && (
                      <div className={styles.detailSection}>
                        <h4>Additional Details</h4>
                        <div className={styles.metadataGrid}>
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <div key={key} className={styles.metadataItem}>
                              <span className={styles.metadataKey}>
                                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                              </span>
                              <span className={styles.metadataValue}>
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {event.source_object_url && (
                      <div className={styles.detailSection}>
                        <button
                          className={styles.viewDetailsButton}
                          onClick={() => handleEventClick(event)}
                        >
                          <FaExternalLinkAlt size={14} /> View Source Details
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
