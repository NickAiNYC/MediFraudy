import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

test('renders app without crashing', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
  // The Layout shows "MediFraudy" in the sidebar
  const titleElements = screen.getAllByText(/MediFraudy/i);
  expect(titleElements.length).toBeGreaterThan(0);
});
