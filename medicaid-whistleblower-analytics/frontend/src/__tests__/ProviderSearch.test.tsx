import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProviderSearch from '../components/ProviderSearch';

test('renders provider search heading', () => {
  render(
    <BrowserRouter>
      <ProviderSearch />
    </BrowserRouter>
  );
  expect(screen.getByText(/Provider Search/i)).toBeInTheDocument();
});

test('renders search input', () => {
  render(
    <BrowserRouter>
      <ProviderSearch />
    </BrowserRouter>
  );
  expect(screen.getByLabelText(/Search by name or NPI/i)).toBeInTheDocument();
});
