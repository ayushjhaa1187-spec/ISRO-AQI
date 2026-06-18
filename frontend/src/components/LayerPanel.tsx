/**
 * components/LayerPanel.tsx
 * Floating glassmorphism panel on the left side of the map.
 * Controls: layer selection (radio), overlay toggles, current date display.
 * Width ~220px, positioned absolutely over the map.
 */

import React from 'react';
import { useMapStore } from '../store/useMapStore';
import type { LayerName } from '../types';

/* ─── Layer definitions ───────────────────────────────────────────────────────── */
interface LayerOption {
  id:    LayerName;
  label: string;
  color: string;
  unit:  string;
}

const LAYERS: LayerOption[] = [
  { id: 'aqi',  label: 'AQI',          color: '#3b82f6', unit: 'Index' },
  { id: 'no2',  label: 'NO₂',          color: '#a78bfa', unit: 'µg/m³' },
  { id: 'so2',  label: 'SO₂',          color: '#fbbf24', unit: 'µg/m³' },
  { id: 'co',   label: 'CO',           color: '#f87171', unit: 'mg/m³' },
  { id: 'o3',   label: 'O₃ (Ozone)',   color: '#34d399', unit: 'µg/m³' },
  { id: 'hcho', label: 'HCHO',         color: '#f97316', unit: 'µg/m³' },
  { id: 'fire', label: 'Fire Density', color: '#ef4444', unit: 'FRP (MW)' },
];

/* ─── ToggleRow component ─────────────────────────────────────────────────────── */
interface ToggleRowProps {
  label:    string;
  icon:     string;
  checked:  boolean;
  onChange: (val: boolean) => void;
}

const ToggleRow: React.FC<ToggleRowProps> = ({ label, icon, checked, onChange }) => (
  <div
    style={{
      display:       'flex',
      alignItems:    'center',
      justifyContent:'space-between',
      padding:       '7px 0',
      borderTop:     '1px solid rgba(255,255,255,0.05)',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
      <span style={{ fontSize: '14px' }}>{icon}</span>
      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
        {label}
      </span>
    </div>
    <label className="toggle-switch">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="toggle-slider" />
    </label>
  </div>
);

/* ─── LayerPanel ──────────────────────────────────────────────────────────────── */
const LayerPanel: React.FC = () => {
  const selectedLayer  = useMapStore((s) => s.selectedLayer);
  const selectedDate   = useMapStore((s) => s.selectedDate);
  const showStations   = useMapStore((s) => s.showStations);
  const showHotspots   = useMapStore((s) => s.showHotspots);
  const showWind       = useMapStore((s) => s.showWind);
  const setSelectedLayer = useMapStore((s) => s.setSelectedLayer);
  const setShowStations  = useMapStore((s) => s.setShowStations);
  const setShowHotspots  = useMapStore((s) => s.setShowHotspots);
  const setShowWind      = useMapStore((s) => s.setShowWind);

  const formattedDate = new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  return (
    <div
      className="glass-panel anim-slide-in-left"
      style={{
        position:  'absolute',
        top:       '16px',
        left:      '16px',
        width:     '220px',
        padding:   '14px 16px',
        zIndex:    50,
        display:   'flex',
        flexDirection: 'column',
        gap:       '0',
      }}
    >
      {/* ── Title ───────────────────────────────────────────────────────────── */}
      <div
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'space-between',
          marginBottom:   '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <span style={{ fontSize: '14px' }}>🗺️</span>
          <span
            style={{
              fontSize:      '13px',
              fontWeight:    700,
              color:         'var(--text-primary)',
              letterSpacing: '0.02em',
            }}
          >
            Layers
          </span>
        </div>
        {/* Current date chip */}
        <div
          style={{
            fontSize:    '10px',
            color:       'var(--accent-blue)',
            background:  'rgba(59,130,246,0.1)',
            border:      '1px solid rgba(59,130,246,0.2)',
            borderRadius:'12px',
            padding:     '2px 7px',
            fontWeight:  600,
          }}
        >
          {formattedDate}
        </div>
      </div>

      {/* ── Layer radio buttons ─────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginBottom: '8px' }}>
        {LAYERS.map((layer) => {
          const isActive = selectedLayer === layer.id;
          return (
            <label
              key={layer.id}
              className="layer-item"
              style={{
                display:       'flex',
                alignItems:    'center',
                gap:           '9px',
                padding:       '7px 8px',
                borderRadius:  '8px',
                cursor:        'pointer',
                background:    isActive ? 'rgba(59,130,246,0.1)' : 'transparent',
                border:        isActive
                                 ? '1px solid rgba(59,130,246,0.2)'
                                 : '1px solid transparent',
              }}
            >
              {/* Hidden radio */}
              <input
                type="radio"
                name="layer"
                value={layer.id}
                checked={isActive}
                onChange={() => setSelectedLayer(layer.id)}
                style={{ display: 'none' }}
              />

              {/* Color dot indicator */}
              <div
                style={{
                  width:       '9px',
                  height:      '9px',
                  borderRadius:'50%',
                  background:  layer.color,
                  boxShadow:   isActive ? `0 0 8px ${layer.color}` : 'none',
                  flexShrink:  0,
                  transition:  'box-shadow var(--transition-fast)',
                }}
              />

              {/* Label */}
              <span
                style={{
                  fontSize:   '13px',
                  fontWeight: isActive ? 600 : 400,
                  color:      isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  flex:       1,
                }}
              >
                {layer.label}
              </span>

              {/* Unit tag */}
              <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                {layer.unit}
              </span>
            </label>
          );
        })}
      </div>

      {/* ── Overlay toggles ─────────────────────────────────────────────────── */}
      <div style={{ marginTop: '4px' }}>
        <div
          style={{
            fontSize:       '10px',
            fontWeight:     600,
            color:          'var(--text-muted)',
            textTransform:  'uppercase',
            letterSpacing:  '0.1em',
            marginBottom:   '4px',
          }}
        >
          Overlays
        </div>
        <ToggleRow
          label="Show Stations"
          icon="📍"
          checked={showStations}
          onChange={setShowStations}
        />
        <ToggleRow
          label="Show Hotspots"
          icon="🔥"
          checked={showHotspots}
          onChange={setShowHotspots}
        />
        <ToggleRow
          label="Show Wind"
          icon="💨"
          checked={showWind}
          onChange={setShowWind}
        />
      </div>

      {/* ── ISRO attribution ────────────────────────────────────────────────── */}
      <div
        style={{
          marginTop:    '12px',
          paddingTop:   '10px',
          borderTop:    '1px solid rgba(255,255,255,0.06)',
          fontSize:     '10px',
          color:        'var(--text-muted)',
          textAlign:    'center',
          lineHeight:   1.5,
        }}
      >
        Data: ISRO / SAC · SENTINEL-5P · MODIS<br />
        <span style={{ color: 'var(--accent-blue)' }}>Satellite-derived</span> measurements
      </div>
    </div>
  );
};

export default LayerPanel;
