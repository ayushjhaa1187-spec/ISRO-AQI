/**
 * components/Legend.tsx
 * Floating bottom-left glassmorphism legend panel.
 * Dynamically shows the correct color scale based on the selected layer:
 *  - AQI: 6 CPCB categories with µg/m³ breakpoints
 *  - HCHO: blue → red gradient scale
 *  - Fire: orange → deep-red density scale
 *  - Other gases: custom continuous gradients
 */

import React from 'react';
import { useMapStore } from '../store/useMapStore';
import type { LayerName } from '../types';

/* ─── AQI Scale ───────────────────────────────────────────────────────────────── */
const AQI_SCALE = [
  { label: 'Good',       color: '#00e400', range: '0–50' },
  { label: 'Satisfactory', color: '#ffff00', range: '51–100' },
  { label: 'Moderate',   color: '#ff7e00', range: '101–200' },
  { label: 'Poor',       color: '#ff0000', range: '201–300' },
  { label: 'Very Poor',  color: '#8f3f97', range: '301–400' },
  { label: 'Severe',     color: '#7e0023', range: '401+' },
];

/* ─── Gradient scales for gas layers ─────────────────────────────────────────── */
interface GradientScale {
  label:    string;
  gradient: string;
  min:      string;
  max:      string;
  unit:     string;
}

const GRADIENT_SCALES: Partial<Record<LayerName, GradientScale>> = {
  hcho: {
    label:    'HCHO Concentration',
    gradient: 'linear-gradient(to right, #0ea5e9, #6366f1, #f97316, #ef4444)',
    min:      '0',
    max:      '50+',
    unit:     'µg/m³',
  },
  no2: {
    label:    'NO₂ Concentration',
    gradient: 'linear-gradient(to right, #1e3a5f, #3b82f6, #a78bfa, #ef4444)',
    min:      '0',
    max:      '200+',
    unit:     'µg/m³',
  },
  so2: {
    label:    'SO₂ Concentration',
    gradient: 'linear-gradient(to right, #1e3a5f, #fbbf24, #f97316, #ef4444)',
    min:      '0',
    max:      '350+',
    unit:     'µg/m³',
  },
  co: {
    label:    'CO Concentration',
    gradient: 'linear-gradient(to right, #064e3b, #10b981, #f59e0b, #ef4444)',
    min:      '0',
    max:      '10+',
    unit:     'mg/m³',
  },
  o3: {
    label:    'O₃ Concentration',
    gradient: 'linear-gradient(to right, #083344, #34d399, #fbbf24, #ef4444)',
    min:      '0',
    max:      '180+',
    unit:     'µg/m³',
  },
  fire: {
    label:    'Fire Radiative Power',
    gradient: 'linear-gradient(to right, #fef08a, #fb923c, #ef4444, #7e0023)',
    min:      'Low',
    max:      'High',
    unit:     'FRP (MW)',
  },
};

/* ─── Legend Component ────────────────────────────────────────────────────────── */
const Legend: React.FC = () => {
  const selectedLayer = useMapStore((s) => s.selectedLayer);

  const isAQI     = selectedLayer === 'aqi';
  const gradient  = GRADIENT_SCALES[selectedLayer];

  return (
    <div
      className="glass-panel-sm anim-fade-in"
      style={{
        width:     '100%',
        padding:   '12px 14px',
      }}
    >
      {/* ── Title ───────────────────────────────────────────────────────────── */}
      <div
        style={{
          fontSize:      '10px',
          fontWeight:    700,
          color:         'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom:  '10px',
        }}
      >
        {isAQI ? 'AQI Scale (CPCB)' : gradient?.label ?? 'Legend'}
      </div>

      {/* ── AQI Categorical Scale ────────────────────────────────────────────── */}
      {isAQI && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {AQI_SCALE.map((item) => (
            <div
              key={item.label}
              style={{
                display:    'flex',
                alignItems: 'center',
                gap:        '8px',
              }}
            >
              {/* Color swatch */}
              <div
                style={{
                  width:        '14px',
                  height:       '14px',
                  borderRadius: '3px',
                  background:   item.color,
                  flexShrink:   0,
                  boxShadow:    `0 0 6px ${item.color}55`,
                }}
              />
              {/* Label */}
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', flex: 1 }}>
                {item.label}
              </span>
              {/* Range */}
              <span
                style={{
                  fontSize:    '10px',
                  color:       'var(--text-muted)',
                  fontFamily:  'monospace',
                  whiteSpace:  'nowrap',
                }}
              >
                {item.range}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ── Gradient Scale (for gas layers / fire) ───────────────────────────── */}
      {!isAQI && gradient && (
        <div>
          {/* Gradient bar */}
          <div
            style={{
              height:       '10px',
              borderRadius: '5px',
              background:   gradient.gradient,
              marginBottom: '6px',
              boxShadow:    '0 2px 8px rgba(0,0,0,0.4)',
            }}
          />
          {/* Min / Max labels */}
          <div
            style={{
              display:        'flex',
              justifyContent: 'space-between',
              alignItems:     'center',
            }}
          >
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              {gradient.min}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center' }}>
              {gradient.unit}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              {gradient.max}
            </span>
          </div>
        </div>
      )}

      {/* ── Hotspot indicator ────────────────────────────────────────────────── */}
      <div
        style={{
          marginTop:  '10px',
          paddingTop: '8px',
          borderTop:  '1px solid rgba(255,255,255,0.06)',
          display:    'flex',
          alignItems: 'center',
          gap:        '6px',
        }}
      >
        <div
          style={{
            width:        '14px',
            height:       '10px',
            border:       '1.5px solid #f97316',
            background:   'rgba(249,115,22,0.25)',
            borderRadius: '2px',
            flexShrink:   0,
          }}
        />
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          HCHO Hotspot
        </span>
      </div>

      {/* Station legend */}
      <div
        style={{
          marginTop:  '6px',
          display:    'flex',
          alignItems: 'center',
          gap:        '6px',
        }}
      >
        <div
          style={{
            width:        '10px',
            height:       '10px',
            borderRadius: '50%',
            background:   'var(--accent-blue)',
            border:       '1.5px solid rgba(255,255,255,0.4)',
            flexShrink:   0,
          }}
        />
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Monitoring Station
        </span>
      </div>
    </div>
  );
};

export default Legend;
