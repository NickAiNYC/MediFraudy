import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import AnomalyTable from '../components/AnomalyTable';
import { anomalyApi } from '../services/api';

// Mock the named export
jest.mock('../services/api');
const mockList = anomalyApi.list as jest.Mock;

beforeEach(() => {
  mockList.mockResolvedValue({ anomalies: [], count: 0 });
});

test('renders anomaly table heading', async () => {
  await act(async () => {
    render(<AnomalyTable />);
  });
  expect(screen.getByText(/Billing Anomalies/i)).toBeInTheDocument();
});

test('renders z-score threshold slider', async () => {
  await act(async () => {
    render(<AnomalyTable />);
  });
  expect(screen.getByText(/Z-Score Threshold/i)).toBeInTheDocument();
});
