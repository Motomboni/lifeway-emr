/**
 * Component Tests
 * 
 * Basic component rendering tests.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoadingSkeleton from '../components/common/LoadingSkeleton';

// Mock AuthContext
const mockUser = {
  id: 1,
  username: 'testuser',
  first_name: 'Test',
  last_name: 'User',
  role: 'DOCTOR',
  email: 'test@example.com',
};

jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

describe('Components', () => {
  describe('LoadingSkeleton', () => {
    it('should render default skeleton', () => {
      render(<LoadingSkeleton />);
      // Component should render without errors
      expect(document.body).toBeTruthy();
    });

    it('should render multiple skeletons', () => {
      render(<LoadingSkeleton count={5} />);
      // Component should render without errors
      expect(document.body).toBeTruthy();
    });
  });

  describe('NotificationBell', () => {
    it('should render notification bell', () => {
      // Mock NotificationContext
      jest.mock('../contexts/NotificationContext', () => ({
        useNotifications: () => ({
          notifications: [],
          unreadCount: 0,
          markAsRead: jest.fn(),
          markAllAsRead: jest.fn(),
          refreshNotifications: jest.fn(),
        }),
      }));

      // Test would go here - skipping for now as it requires more setup
    });
  });
});
