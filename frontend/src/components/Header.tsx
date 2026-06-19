/**
 * components/Header.tsx
 * Slim 48px glassmorphism header for the ISRO AQI & HCHO Monitor Platform.
 * Contains: ISRO branding (left), navigation links (right).
 * Uses glass-header CSS class for backdrop blur effect.
 */

import React from 'react';
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

        {/* ISRO satellite data tag */}
        <div
          style={{
            marginLeft: '10px',
            padding: '4px 10px',
            background: 'rgba(249,115,22,0.1)',
            border: '1px solid rgba(249,115,22,0.25)',
            borderRadius: '6px',
            fontSize: '10px',
            color: 'var(--accent-orange)',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          Satellite Data
        </div>
      </nav>
    </header>
  );
};

export default Header;
