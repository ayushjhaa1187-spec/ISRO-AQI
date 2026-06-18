/**
 * components/AQIPopup.tsx
 * MapLibre popup rendered as a React portal OR returned as an HTML string.
 * Displays: AQI value, category badge, dominant pollutant, health advice,
 *           observation date, and Observed vs Predicted label.
 */

import React from 'react';
import type { AQIResponse, AQICategory } from '../types';

/* ─── AQI Category → color mapping ───────────────────────────────────────────── */
export const AQI_CATEGORY_COLOR: Record<AQICategory, string> = {
  'Good':        'var(--aqi-good)',
  'Satisfactory':'var(--aqi-satisfactory)',
  'Moderate':    'var(--aqi-moderate)',
  'Poor':        'var(--aqi-poor)',
  'Very Poor':   'var(--aqi-very-poor)',
  'Severe':      'var(--aqi-severe)',
};

/* ─── Helper: category text color (some need dark text) ─────────────────────── */
export const categoryTextColor = (cat: AQICategory): string =>
  cat === 'Good' || cat === 'Satisfactory' ? '#111827' : '#ffffff';

/* ─── AQI Popup React Component ──────────────────────────────────────────────── */
interface AQIPopupProps {
  data: AQIResponse;
  coordLabel?: string;
}

const AQIPopup: React.FC<AQIPopupProps> = ({ data, coordLabel }) => {
  const bgColor   = AQI_CATEGORY_COLOR[data.category] ?? '#888';
  const textColor = categoryTextColor(data.category);

  const formattedDate = new Date(data.date + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  return (
    <div style={{ fontFamily: 'var(--font-family)', minWidth: '240px', padding: '0' }}>
      {/* ── Header strip ──────────────────────────────────────────────────── */}
      <div
        style={{
          background: bgColor,
          borderRadius: '10px 10px 0 0',
          padding: '14px 16px 10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', color: textColor, opacity: 0.75, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Air Quality Index
          </div>
          <div style={{ fontSize: '38px', fontWeight: 800, color: textColor, lineHeight: 1.1, letterSpacing: '-1px' }}>
            {Math.round(data.aqi)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div
            style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '20px',
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: 700,
              color: textColor,
              letterSpacing: '0.03em',
              marginBottom: '4px',
            }}
          >
            {data.category}
          </div>
          <div
            style={{
              fontSize: '10px',
              color: textColor,
              opacity: 0.8,
              fontWeight: 500,
              background: data.is_predicted ? 'rgba(0,0,0,0.2)' : 'transparent',
              borderRadius: '4px',
              padding: data.is_predicted ? '2px 6px' : '0',
            }}
          >
            {data.is_predicted ? '🔮 Predicted' : '📡 Observed'}
          </div>
        </div>
      </div>

      {/* ── Body ──────────────────────────────────────────────────────────── */}
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {/* Pollutant row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>
            Dominant Pollutant
          </span>
          <span
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--accent-orange)',
              background: 'rgba(249,115,22,0.12)',
              borderRadius: '6px',
              padding: '2px 8px',
            }}
          >
            {data.dominant_pollutant}
          </span>
        </div>

        {/* Health advice */}
        <div
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            padding: '10px 12px',
          }}
        >
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
            Health Advice
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {data.health_advice}
          </div>
        </div>

        {/* Pollutant grid */}
        {data.pollutants && Object.keys(data.pollutants).length > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '6px',
            }}
          >
            {Object.entries(data.pollutants)
              .filter(([, v]) => v !== null && v !== undefined)
              .slice(0, 6)
              .map(([key, val]) => (
                <div
                  key={key}
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: '6px',
                    padding: '6px 8px',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {key.toUpperCase()}
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {typeof val === 'number' ? val.toFixed(1) : '—'}
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            📅 {formattedDate}
          </div>
          {coordLabel && (
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              {coordLabel}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AQIPopup;

/* ─── HTML string generator (for MapLibre popup.setHTML) ─────────────────────── */
export function buildAQIPopupHTML(data: AQIResponse, coordLabel?: string): string {
  const bgColor   = AQI_CATEGORY_COLOR[data.category] ?? '#888';
  const textColor = categoryTextColor(data.category);
  const formattedDate = new Date(data.date + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  const pollutantCells = data.pollutants
    ? Object.entries(data.pollutants)
        .filter(([, v]) => v !== null && v !== undefined)
        .slice(0, 6)
        .map(
          ([key, val]) => `
          <div style="background:rgba(255,255,255,0.04);border-radius:6px;padding:6px 8px;text-align:center;">
            <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:0.06em;">${key.toUpperCase()}</div>
            <div style="font-size:13px;font-weight:600;color:#f1f5f9;">${typeof val === 'number' ? val.toFixed(1) : '—'}</div>
          </div>`
        )
        .join('')
    : '';

  return `
<div style="font-family:'Inter',sans-serif;min-width:240px;">
  <div style="background:${bgColor};border-radius:10px 10px 0 0;padding:14px 16px 10px;display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="font-size:11px;color:${textColor};opacity:0.75;font-weight:500;text-transform:uppercase;letter-spacing:0.08em;">Air Quality Index</div>
      <div style="font-size:38px;font-weight:800;color:${textColor};line-height:1.1;letter-spacing:-1px;">${Math.round(data.aqi)}</div>
    </div>
    <div style="text-align:right;">
      <div style="background:rgba(0,0,0,0.2);border-radius:20px;padding:4px 10px;font-size:12px;font-weight:700;color:${textColor};margin-bottom:4px;">${data.category}</div>
      <div style="font-size:10px;color:${textColor};opacity:0.8;font-weight:500;">${data.is_predicted ? '🔮 Predicted' : '📡 Observed'}</div>
    </div>
  </div>
  <div style="padding:14px 16px;display:flex;flex-direction:column;gap:10px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <span style="font-size:12px;color:#475569;font-weight:500;">Dominant Pollutant</span>
      <span style="font-size:13px;font-weight:700;color:#f97316;background:rgba(249,115,22,0.12);border-radius:6px;padding:2px 8px;">${data.dominant_pollutant}</span>
    </div>
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:10px 12px;">
      <div style="font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">Health Advice</div>
      <div style="font-size:12px;color:#94a3b8;line-height:1.5;">${data.health_advice}</div>
    </div>
    ${pollutantCells ? `<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">${pollutantCells}</div>` : ''}
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:2px;">
      <div style="font-size:11px;color:#475569;">📅 ${formattedDate}</div>
      ${coordLabel ? `<div style="font-size:10px;color:#475569;font-family:monospace;">${coordLabel}</div>` : ''}
    </div>
  </div>
</div>`;
}
