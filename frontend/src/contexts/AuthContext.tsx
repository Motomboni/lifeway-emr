/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, AuthTokens } from '../types/auth';
import { loginUser, logoutUser, refreshAccessToken as refreshTokenAPI, getCurrentUser, isAccessTokenExpired } from '../api/auth';

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load auth state from localStorage on mount
  useEffect(() => {
    const loadAuthState = async () => {
      const storedTokens = localStorage.getItem('auth_tokens');
      const storedUser = localStorage.getItem('auth_user');
      
      if (storedTokens && storedUser) {
        try {
          const parsedTokens = JSON.parse(storedTokens);
          const parsedUser = JSON.parse(storedUser);
          
          setTokens(parsedTokens);
          setUser(parsedUser);

          const access = parsedTokens?.access;
          if (!access || isAccessTokenExpired(access)) {
            setTokens(null);
            setUser(null);
            localStorage.removeItem('auth_tokens');
            localStorage.removeItem('auth_user');
            localStorage.removeItem('auth_token');
          } else {
            try {
              const currentUser = await getCurrentUser();
              setUser(currentUser);
            } catch {
              setTokens(null);
              setUser(null);
              localStorage.removeItem('auth_tokens');
              localStorage.removeItem('auth_user');
              localStorage.removeItem('auth_token');
            }
          }
        } catch (error) {
          // Invalid stored data, clear it
          localStorage.removeItem('auth_tokens');
          localStorage.removeItem('auth_user');
          localStorage.removeItem('auth_token'); // Legacy
        }
      }
      
      setIsLoading(false);
    };

    loadAuthState();
  }, []);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!tokens) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshAccessToken();
      } catch (error) {
        // Refresh failed, logout user
        await logout();
      }
    }, 14 * 60 * 1000); // Refresh every 14 minutes (access token expires in 15)

    return () => clearInterval(refreshInterval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokens]);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await loginUser(username, password);
      
      setUser(response.user);
      setTokens({
        access: response.access,
        refresh: response.refresh,
      });
      
      // Store in localStorage
      localStorage.setItem('auth_tokens', JSON.stringify({
        access: response.access,
        refresh: response.refresh,
      }));
      localStorage.setItem('auth_user', JSON.stringify(response.user));
      localStorage.setItem('auth_token', response.access); // Legacy support
    } catch (error) {
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (tokens?.refresh) {
        await logoutUser(tokens.refresh);
      }
    } catch (error) {
      // Continue with logout even if API call fails
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setTokens(null);
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_token');
    }
  }, [tokens]);

  const refreshAccessToken = useCallback(async () => {
    if (!tokens?.refresh) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await refreshTokenAPI(tokens.refresh);
      
      const newTokens = {
        access: response.access,
        refresh: response.refresh,
      };
      
      setTokens(newTokens);
      localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
      localStorage.setItem('auth_token', response.access); // Legacy support
    } catch (error) {
      // Refresh failed, clear auth state
      setUser(null);
      setTokens(null);
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_token');
      throw error;
    }
  }, [tokens]);

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated: !!user && !!tokens,
    isLoading,
    login,
    logout,
    refreshAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
