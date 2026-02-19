/**
 * ServiceSearchInput Component
 * 
 * Autocomplete/search input for selecting services from the service catalog.
 * Used in billing to search and add services to bills.
 */
import React, { useState, useEffect, useRef } from 'react';
import { searchServices, Service } from '../../api/billing';
import { formatCurrency } from '../../utils/currency';
import { useAuth } from '../../contexts/AuthContext';
import styles from './ServiceSearchInput.module.css';

/** Format expiry date for display */
function formatExpiryDate(isoDate: string | null | undefined): string {
  if (!isoDate) return '—';
  try {
    const d = new Date(isoDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    d.setHours(0, 0, 0, 0);
    if (d < today) return `Expired ${d.toLocaleDateString()}`;
    return d.toLocaleDateString();
  } catch {
    return '—';
  }
}

interface ServiceSearchInputProps {
  onServiceSelect: (service: Service) => void;
  department?: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  placeholder?: string;
  disabled?: boolean;
}

const DEPARTMENT_LABELS: Record<string, string> = {
  LAB: 'Lab',
  PHARMACY: 'Pharmacy',
  RADIOLOGY: 'Radiology',
  PROCEDURE: 'Procedure',
};

export default function ServiceSearchInput({
  onServiceSelect,
  department,
  placeholder = 'Search services (e.g., consultation, dental, vaccine)...',
  disabled = false,
}: ServiceSearchInputProps) {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Service[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Check if a service is a registration service
  const isRegistrationService = (service: Service): boolean => {
    const serviceCode = (service.service_code || '').toUpperCase();
    const serviceName = (service.service_name || service.name || '').toUpperCase();
    const description = (service.description || '').toUpperCase();
    
    return (
      serviceCode.startsWith('REG-') ||
      serviceName.includes('REGISTRATION') ||
      description.includes('REGISTRATION')
    );
  };
  
  // Check if a service is a consultation service
  // Check by workflow_type, department, service_code pattern, or name
  const isConsultationService = (service: Service): boolean => {
    const serviceCode = (service.service_code || '').toUpperCase();
    const serviceName = (service.service_name || service.name || '').toUpperCase();
    const department = (service.department || '').toUpperCase();
    
    return (
      service.workflow_type === 'GOPD_CONSULT' ||
      department === 'CONSULTATION' ||
      serviceCode.startsWith('CONS-') ||
      serviceName.includes('FOLLOW UP') ||
      serviceName.includes('FOLLOW-UP') ||
      serviceName.includes('FOLLOWUP') ||
      serviceName.includes('CONSULTATION') ||
      serviceName.includes('CONSULT')
    );
  };
  
  // Check if user can order a service based on allowed_roles
  const canOrderService = (service: Service): boolean => {
    if (!service.allowed_roles || service.allowed_roles.length === 0) {
      // If no allowed_roles specified, allow all authenticated users
      return true;
    }
    
    const userRole = user?.role;
    if (!userRole) {
      return false;
    }
    
    // Special handling for RECEPTIONIST: They can add services to bills
    // even if not explicitly in allowed_roles (billing workflow vs clinical workflow)
    // However, backend will still validate, so we show all but indicate restrictions
    if (userRole === 'RECEPTIONIST') {
      // Receptionists can order registration and consultation services
      if (isRegistrationService(service) || isConsultationService(service)) {
        return true;
      }
      // For other services, show all but backend will validate
      return true; // Show all services, backend will validate
    }
    
    // For other roles, check if user's role is in the allowed_roles list
    return service.allowed_roles.includes(userRole);
  };
  
  // Check if service is actually orderable by user (for visual indicators)
  const isServiceOrderable = (service: Service): boolean => {
    if (!service.allowed_roles || service.allowed_roles.length === 0) {
      return true;
    }
    
    const userRole = user?.role;
    if (!userRole) {
      return false;
    }
    
    // Receptionists can always order registration and consultation services (backend allows this)
    if (userRole === 'RECEPTIONIST' && (isRegistrationService(service) || isConsultationService(service))) {
      return true;
    }
    
    return service.allowed_roles.includes(userRole);
  };

  // Search services when query changes
  useEffect(() => {
    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (searchQuery.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    // Debounce search
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const response = await searchServices({
          q: searchQuery.trim(),
          department,
          limit: 20,
        });
        
        // Filter services based on user's role
        // For receptionists, show all services (they can add to bills)
        // For other roles, filter by allowed_roles
        const userRole = user?.role;
        const filteredResults = userRole === 'RECEPTIONIST'
          ? response.results // Show all services for receptionists
          : response.results.filter(service => canOrderService(service));
        
        setSuggestions(filteredResults);
        setShowSuggestions(filteredResults.length > 0);
        setSelectedIndex(-1);
      } catch (error) {
        console.error('Error searching services:', error);
        setSuggestions([]);
        setShowSuggestions(false);
      } finally {
        setLoading(false);
      }
    }, 300); // 300ms debounce

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery, department, user]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setSearchQuery(newValue);
    setShowSuggestions(true);
  };

  const handleServiceSelect = (service: Service) => {
    // Check if user can order this service
    if (!canOrderService(service)) {
      // This shouldn't happen if filtering works correctly, but add safety check
      return;
    }
    
    // Prevent blur from hiding suggestions before click is processed
    setShowSuggestions(false);
    setSelectedIndex(-1);
    setSearchQuery('');
    
    // Call the parent handler
    onServiceSelect(service);
    
    // Refocus input after a short delay to allow the click to complete
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }, 100);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === 'Enter') {
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleServiceSelect(suggestions[selectedIndex]);
        } else if (suggestions.length === 1) {
          handleServiceSelect(suggestions[0]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    // Check if the blur is due to clicking on a suggestion
    // If so, don't hide suggestions immediately
    const relatedTarget = e.relatedTarget as HTMLElement;
    if (relatedTarget && relatedTarget.closest(`.${styles.suggestionsList}`)) {
      // User clicked on a suggestion, don't hide yet
      return;
    }
    
    // Delay hiding suggestions to allow click events
    setTimeout(() => {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }, 200);
  };

  const handleFocus = () => {
    if (searchQuery.trim().length >= 2 && suggestions.length > 0) {
      setShowSuggestions(true);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.inputWrapper}>
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          onFocus={handleFocus}
          placeholder={placeholder}
          disabled={disabled}
          className={styles.input}
          autoComplete="off"
        />
        {loading && (
          <div className={styles.loadingIndicator}>
            <div className={styles.spinner}></div>
          </div>
        )}
        {!loading && searchQuery.trim().length >= 2 && (
          <div className={styles.resultCount}>
            {suggestions.length} {suggestions.length === 1 ? 'result' : 'results'}
          </div>
        )}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className={styles.suggestionsList}
        >
          {suggestions.map((service, index) => {
            const canOrder = canOrderService(service);
            const isOrderable = isServiceOrderable(service);
            return (
              <div
                key={`${service.department}-${service.service_code}`}
                className={`${styles.suggestionItem} ${index === selectedIndex ? styles.suggestionItemSelected : ''} ${!isOrderable ? styles.suggestionItemDisabled : ''}`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  // Allow clicking even if not orderable - backend will validate
                  handleServiceSelect(service);
                }}
                onMouseDown={(e) => {
                  // Prevent input blur when clicking on suggestion
                  e.preventDefault();
                }}
                onMouseEnter={() => setSelectedIndex(index)}
                title={!isOrderable ? `This service may require a doctor to order. Allowed roles: ${service.allowed_roles?.join(', ') || 'N/A'}` : undefined}
              >
                <div className={styles.suggestionContent}>
                  <div className={styles.suggestionLeft}>
                    <div className={styles.suggestionHeader}>
                      <span className={styles.departmentBadge}>
                        {DEPARTMENT_LABELS[service.department] || service.department}
                      </span>
                      <span className={styles.suggestionName}>
                        {service.service_name || service.name}
                      </span>
                      {!isOrderable && (
                        <span className={styles.restrictedBadge} title={`May require: ${service.allowed_roles?.join(', ') || 'N/A'}`}>
                          ⚠️ Check Permissions
                        </span>
                      )}
                    </div>
                    {service.service_code && (
                      <div className={styles.suggestionCode}>
                        Code: {service.service_code}
                      </div>
                    )}
                    {service.department === 'PHARMACY' && (
                      <div className={styles.drugStockInfo}>
                        <span className={service.is_out_of_stock ? styles.stockOutOfStock : styles.stockAvailable}>
                          Stock: {service.drug_availability != null
                            ? (service.is_out_of_stock ? 'Out of stock' : `${service.drug_availability} ${service.drug_unit || 'units'}`)
                            : 'No inventory'}
                        </span>
                        <span className={styles.stockExpiry}>
                          Expiry: {formatExpiryDate(service.drug_expiry_date ?? undefined)}
                        </span>
                        {service.is_low_stock && !service.is_out_of_stock && (
                          <span className={styles.lowStockBadge}>Low stock</span>
                        )}
                      </div>
                    )}
                    {service.description && (
                      <div className={styles.suggestionDescription}>
                        {service.description}
                      </div>
                    )}
                  </div>
                  <div className={styles.suggestionAmount}>
                    {formatCurrency(service.amount)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showSuggestions && searchQuery.trim().length >= 2 && suggestions.length === 0 && !loading && (
        <div className={styles.noResults}>
          No services found matching "{searchQuery}"
        </div>
      )}
    </div>
  );
}

