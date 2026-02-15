import React from 'react';
import { render, screen } from '@testing-library/react';
import AnomalyTable from '../components/AnomalyTable';

jest.mock('../services/api', () => ({
  listAnomalies: jest.fn().mockResolvedValue({ data: { anomalies: [] } }),
}));

test('renders anomaly table heading', () => {
  render(<AnomalyTable />);
  expect(screen.getByText(/Billing Anomalies/i)).toBeInTheDocument();
});

test('renders z-score threshold slider', () => {
  render(<AnomalyTable />);
  expect(screen.getByText(/Z-Score Threshold/i)).toBeInTheDocument();
});
