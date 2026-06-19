/**
 * components/Header.tsx
 * Slim 48px glassmorphism header for the ISRO AQI & HCHO Monitor Platform.
 * Contains: ISRO branding (left), navigation links (right).
 * Uses glass-header CSS class for backdrop blur effect.
 */

import React, { useState } from 'react';
import { useMapStore } from '../store/useMapStore';

interface NavItem {
  label: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Map',         href: '#map' },
  { label: 'Explore',     href: '#explore' },
  { label: 'Stations',    href: '#stations' },
  { label: 'Insights',    href: '#insights' },
  { label: 'Methodology', href: '#methodology' },
];

const Header: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);
  const [isSatModalOpen, setIsSatModalOpen] = useState(false);

  return (
    <header
      className="glass-header"
      style={{
        height: '48px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        zIndex: 100,
        position: 'relative',
        flexShrink: 0,
      }}
    >
      {/* ── Branding ─────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span
          style={{
            fontSize: '22px',
            filter: 'drop-shadow(0 0 8px rgba(59,130,246,0.6))',
            lineHeight: 1,
          }}
          role="img"
          aria-label="Satellite"
        >
          🛰️
        </span>
        <div>
          <span
            style={{
              fontWeight: 700,
              fontSize: '14px',
              color: 'var(--text-primary)',
              letterSpacing: '0.02em',
            }}
          >
            ISRO{' '}
            <span style={{ color: 'var(--accent-blue)' }}>AQI</span>
            {' & '}
            <span style={{ color: 'var(--accent-orange)' }}>HCHO</span>
            {' '}Monitor
          </span>
          <div
            style={{
              fontSize: '9px',
              color: 'var(--text-muted)',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              marginTop: '-2px',
            }}
          >
            India Surface Air Quality Platform
          </div>
        </div>

        {/* Live badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            background: 'rgba(0,228,64,0.1)',
            border: '1px solid rgba(0,228,64,0.25)',
            borderRadius: '20px',
            padding: '2px 8px',
            marginLeft: '8px',
          }}
          className="hide-mobile"
        >
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--aqi-good)',
              boxShadow: '0 0 6px var(--aqi-good)',
              animation: 'pulse-dot 2s ease-in-out infinite',
            }}
          />
          <span style={{ fontSize: '10px', color: 'var(--aqi-good)', fontWeight: 600, letterSpacing: '0.05em' }}>
            LIVE
          </span>
        </div>
      </div>

      {/* ── Navigation ───────────────────────────────────────────────────────── */}
      <nav
        style={{ display: 'flex', alignItems: 'center', gap: '2px' }}
        className="hide-mobile"
      >
        {NAV_ITEMS.map((item) => (
          <a
            key={item.label}
            href={item.href}
            onClick={(e) => { e.preventDefault(); setActiveNav(item.label); }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '5px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: activeNav === item.label ? 600 : 400,
              color: activeNav === item.label ? 'var(--accent-blue)' : 'var(--text-secondary)',
              background: activeNav === item.label ? 'rgba(59,130,246,0.1)' : 'transparent',
              border: activeNav === item.label ? '1px solid rgba(59,130,246,0.2)' : '1px solid transparent',
              textDecoration: 'none',
              transition: 'all var(--transition-fast)',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              if (activeNav !== item.label) {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
              }
            }}
            onMouseLeave={(e) => {
              if (activeNav !== item.label) {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                (e.currentTarget as HTMLElement).style.background = 'transparent';
              }
            }}
          >
            {item.label}
          </a>
        ))}

        {/* ISRO satellite data interactive button */}
        <button
          onClick={() => setIsSatModalOpen(true)}
          style={{
            marginLeft: '10px',
            padding: '5px 12px',
            background: 'rgba(249,115,22,0.15)',
            border: '1px solid rgba(249,115,22,0.4)',
            borderRadius: '6px',
            fontSize: '11px',
            color: 'var(--accent-orange)',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
            fontFamily: 'var(--font-family)',
            boxShadow: '0 0 10px rgba(249,115,22,0.1)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(249,115,22,0.25)';
            e.currentTarget.style.boxShadow = '0 0 15px rgba(249,115,22,0.25)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(249,115,22,0.15)';
            e.currentTarget.style.boxShadow = '0 0 10px rgba(249,115,22,0.1)';
          }}
        >
          🛰️ Satellite Data
        </button>
      </nav>

      {/* ── Satellite Info Modal ────────────────────────────────────────────── */}
      {isSatModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(0,0,0,0.65)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            animation: 'fadeIn 0.25s ease',
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '90%',
              maxWidth: '650px',
              padding: '30px',
              position: 'relative',
              boxShadow: '0 10px 40px rgba(0,0,0,0.6)',
              border: '1px solid rgba(255,255,255,0.12)',
            }}
          >
            {/* Close button */}
            <button
              onClick={() => setIsSatModalOpen(false)}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>

            <h3
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <span style={{ fontSize: '26px' }}>🛰️</span> Satellite Observers & Payloads
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '24px' }}>
              Details and status of active sensors supplying space-based measurements.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              {/* TROPOMI */}
              <div
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--accent-blue)', fontSize: '14px' }}>
                    TROPOMI (Sentinel-5 Precursor)
                  </span>
                  <span
                    style={{
                      background: 'rgba(0,228,64,0.1)',
                      border: '1px solid rgba(0,228,64,0.25)',
                      borderRadius: '12px',
                      padding: '1px 8px',
                      fontSize: '9px',
                      color: 'var(--aqi-good)',
                      fontWeight: 600,
                    }}
                  >
                    OPERATIONAL
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong>Role:</strong> Column trace gas densities (HCHO, NO₂, SO₂, CO, O₃).<br />
                  <strong>Resolution:</strong> 3.5 km × 5.5 km · <strong>Revisit Time:</strong> Daily (global coverage).
                </div>
              </div>

              {/* MODIS & VIIRS */}
              <div
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--accent-orange)', fontSize: '14px' }}>
                    VIIRS (Suomi NPP) & MODIS (Terra/Aqua)
                  </span>
                  <span
                    style={{
                      background: 'rgba(0,228,64,0.1)',
                      border: '1px solid rgba(0,228,64,0.25)',
                      borderRadius: '12px',
                      padding: '1px 8px',
                      fontSize: '9px',
                      color: 'var(--aqi-good)',
                      fontWeight: 600,
                    }}
                  >
                    OPERATIONAL
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong>Role:</strong> Thermal anomalies & active fire count (FIRMS FRP measurements).<br />
                  <strong>Resolution:</strong> 375m (VIIRS), 1km (MODIS) · <strong>Revisit:</strong> Sub-daily passes.
                </div>
              </div>

              {/* INSAT-3D */}
              <div
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 600, color: '#10b981', fontSize: '14px' }}>
                    INSAT-3D / 3DR (ISRO Geostationary)
                  </span>
                  <span
                    style={{
                      background: 'rgba(0,228,64,0.1)',
                      border: '1px solid rgba(0,228,64,0.25)',
                      borderRadius: '12px',
                      padding: '1px 8px',
                      fontSize: '9px',
                      color: 'var(--aqi-good)',
                      fontWeight: 600,
                    }}
                  >
                    OPERATIONAL
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong>Role:</strong> Aerosol Optical Depth (AOD) & meteorological profiles.<br />
                  <strong>Resolution:</strong> 4 km · <strong>Temporal Revisit:</strong> Continuous 15-min scans over India.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
