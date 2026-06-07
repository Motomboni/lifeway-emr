/**
 * Current clinic (tenant) branding — loaded once per session.
 */
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { getCurrentOrganization, Organization } from '../api/organizations';

interface OrganizationContextValue {
  organization: Organization | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextValue>({
  organization: null,
  loading: true,
  refresh: async () => {},
});

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!isAuthenticated || user?.role === 'PATIENT') {
      setOrganization(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const org = await getCurrentOrganization();
      setOrganization(org);
    } catch {
      setOrganization(null);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user?.role]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <OrganizationContext.Provider value={{ organization, loading, refresh }}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  return useContext(OrganizationContext);
}
