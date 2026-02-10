/**
 * Keyboard Shortcuts Hook
 * 
 * Provides keyboard shortcuts for common actions.
 */
import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      shortcuts.forEach((shortcut) => {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault();
          shortcut.action();
        }
      });
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [shortcuts]);
}

/**
 * Default keyboard shortcuts for the application
 */
export function useDefaultKeyboardShortcuts() {
  const navigate = useNavigate();
  const { user } = useAuth();

  useKeyboardShortcuts([
    {
      key: 'n',
      ctrl: true,
      action: () => {
        if (user?.role === 'RECEPTIONIST') {
          navigate('/visits/new');
        }
      },
      description: 'Create new visit (Receptionist)',
    },
    {
      key: 'v',
      ctrl: true,
      action: () => navigate('/visits'),
      description: 'View visits list',
    },
    {
      key: 'p',
      ctrl: true,
      action: () => navigate('/patients'),
      description: 'View patients',
    },
    {
      key: 'd',
      ctrl: true,
      action: () => {
        const dashboardRoute = user?.role === 'PATIENT' ? '/patient-portal/dashboard' : '/dashboard';
        navigate(dashboardRoute);
      },
      description: 'Go to dashboard',
    },
    {
      key: 'l',
      ctrl: true,
      shift: true,
      action: () => {
        // Logout - handled by auth context
        if (window.confirm('Are you sure you want to logout?')) {
          window.location.href = '/login';
        }
      },
      description: 'Logout',
    },
    {
      key: 'Escape',
      action: () => {
        // Close modals or go back
        if (window.history.length > 1) {
          navigate(-1);
        }
      },
      description: 'Go back',
    },
  ]);
}
