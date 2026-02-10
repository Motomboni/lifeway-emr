/**
 * Integration tests for Consultation workflow
 * 
 * Tests the complete consultation creation and editing flow.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ConsultationPage from '../../pages/ConsultationPage';

// Mock API calls
jest.mock('../../api/consultation', () => ({
  fetchConsultation: jest.fn(),
  createConsultation: jest.fn(),
  updateConsultation: jest.fn(),
}));

jest.mock('../../api/visits', () => ({
  fetchVisitDetails: jest.fn(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      role: 'DOCTOR',
      first_name: 'Dr.',
      last_name: 'Test',
    },
    isAuthenticated: true,
  }),
}));

describe('Consultation Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should load consultation form for new visit', async () => {
    const { fetchVisitDetails, fetchConsultation } = require('../../api/visits');
    const { fetchConsultation: fetchConsult } = require('../../api/consultation');
    
    fetchVisitDetails.mockResolvedValue({
      id: 1,
      patient: { name: 'Test Patient' },
      status: 'OPEN',
      payment_status: 'CLEARED',
    });
    
    fetchConsult.mockResolvedValue(null);

    render(
      <BrowserRouter>
        <ConsultationPage visitId="1" />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Test Patient/i)).toBeInTheDocument();
    });
  });

  it('should save consultation successfully', async () => {
    const { createConsultation } = require('../../api/consultation');
    const { fetchVisitDetails } = require('../../api/visits');
    
    fetchVisitDetails.mockResolvedValue({
      id: 1,
      patient: { name: 'Test Patient' },
      status: 'OPEN',
      payment_status: 'CLEARED',
    });
    
    createConsultation.mockResolvedValue({
      id: 1,
      history: 'Test history',
      examination: 'Test examination',
      diagnosis: 'Test diagnosis',
      clinical_notes: 'Test notes',
    });

    render(
      <BrowserRouter>
        <ConsultationPage visitId="1" />
      </BrowserRouter>
    );

    // Wait for form to load
    await waitFor(() => {
      expect(screen.getByText(/Test Patient/i)).toBeInTheDocument();
    });

    // Fill form and submit
    const historyInput = screen.getByLabelText(/history/i);
    fireEvent.change(historyInput, { target: { value: 'Test history' } });

    const saveButton = screen.getByText(/save/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(createConsultation).toHaveBeenCalled();
    });
  });
});
