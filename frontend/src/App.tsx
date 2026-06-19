/**
 * App.tsx
 * Root application layout for the ISRO AQI & HCHO Monitor Platform.
 * Map-first design: the map fills the entire viewport.
 * Floating panels (Header, LayerPanel, TimeControl, Legend) overlay the map.
 */

import React from 'react';
import Header from './components/Header';
import MapView from './components/MapView';
import LayerPanel from './components/LayerPanel';
import TimeControl from './components/TimeControl';
import Legend from './components/Legend';
import EvaluationDashboard from './components/EvaluationDashboard';
import StationsDashboard from './components/StationsDashboard';
import ExploreDashboard from './components/ExploreDashboard';

const App: React.FC = () => {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-base)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* ── Slim header bar ─────────────────────────────────────────────────── */}
      <Header />

      {/* ── Map fills remaining space ────────────────────────────────────────── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MapView />

        {/* ── Floating: Layer panel (left side) ─────────────────────────────── */}
        <LayerPanel />

        {/* ── Floating: Legend (bottom-left) ────────────────────────────────── */}
        <Legend />

        {/* ── Floating: Time control (bottom-center) ────────────────────────── */}
        <TimeControl />

        {/* ── Floating: Evaluation Dashboard (modal) ────────────────────────── */}
        <EvaluationDashboard />
        
        {/* ── Floating: Stations Dashboard (modal) ────────────────────────── */}
        <StationsDashboard />
        
        {/* ── Floating: Explore Dashboard (modal) ────────────────────────── */}
        <ExploreDashboard />
      </div>
    </div>
  );
};

export default App;
