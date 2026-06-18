/**
 * main.tsx
 * Application entry point for the ISRO AQI & HCHO Monitor Platform.
 * Wraps the app with React Query provider for data fetching.
 * Note: Zustand stores are singleton — no context provider required.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';
import App from './App';

/* ─── React Query Client ──────────────────────────────────────────────────────── */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,    // Scientific data — no surprise refetches
      refetchOnMount: true,
      retry: 1,
      staleTime: 5 * 60 * 1_000,     // 5 minutes default staleness
    },
  },
});

/* ─── Mount ───────────────────────────────────────────────────────────────────── */
const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element not found');

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);
