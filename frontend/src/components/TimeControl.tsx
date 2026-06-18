/**
 * components/TimeControl.tsx
 * Floating bottom-center glassmorphism time animation control panel.
 * Features:
 *  - Date range slider
 *  - Formatted current date label
 *  - Play/Pause button with animated icon swap
 *  - Animation speed selector (0.5x, 1x, 2x)
 *  - Prev/Next day arrow buttons
 *  - Auto-advance via setInterval when playing
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { useMapStore } from '../store/useMapStore';

/* ─── Speed options ───────────────────────────────────────────────────────────── */
const SPEED_OPTIONS = [0.5, 1, 2] as const;

/* ─── Format date for display ────────────────────────────────────────────────── */
const formatDate = (dateStr: string): string => {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
};

/* ─── PlayIcon ────────────────────────────────────────────────────────────────── */
const PlayIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M3 2.5l11 5.5-11 5.5V2.5z" />
  </svg>
);

/* ─── PauseIcon ──────────────────────────────────────────────────────────────── */
const PauseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <rect x="3" y="2" width="4" height="12" rx="1" />
    <rect x="9" y="2" width="4" height="12" rx="1" />
  </svg>
);

/* ─── ChevronLeft / Right ─────────────────────────────────────────────────────── */
const ChevronLeft = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="9,2 4,7 9,12" />
  </svg>
);

const ChevronRight = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="5,2 10,7 5,12" />
  </svg>
);

/* ─── TimeControl ─────────────────────────────────────────────────────────────── */
const TimeControl: React.FC = () => {
  const selectedDate   = useMapStore((s) => s.selectedDate);
  const isAnimating    = useMapStore((s) => s.isAnimating);
  const animationSpeed = useMapStore((s) => s.animationSpeed);
  const availableDates = useMapStore((s) => s.availableDates);
  const setSelectedDate  = useMapStore((s) => s.setSelectedDate);
  const setAnimating     = useMapStore((s) => s.setAnimating);
  const setAnimationSpeed = useMapStore((s) => s.setAnimationSpeed);
  const stepDate         = useMapStore((s) => s.stepDate);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── Slider helpers ─────────────────────────────────────────────────────── */
  const dates    = availableDates.length > 0 ? availableDates : [selectedDate];
  const minIdx   = 0;
  const maxIdx   = dates.length - 1;
  const curIdx   = dates.indexOf(selectedDate);
  const sliderVal = curIdx >= 0 ? curIdx : maxIdx;

  const onSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const idx = parseInt(e.target.value, 10);
      if (dates[idx]) setSelectedDate(dates[idx]);
    },
    [dates, setSelectedDate]
  );

  /* ── Auto-advance when animating ────────────────────────────────────────── */
  useEffect(() => {
    if (isAnimating) {
      intervalRef.current = setInterval(() => {
        const store = useMapStore.getState();
        const dts   = store.availableDates.length > 0
          ? store.availableDates
          : [store.selectedDate];
        const idx   = dts.indexOf(store.selectedDate);
        if (idx < dts.length - 1) {
          store.setSelectedDate(dts[idx + 1]);
        } else {
          // Loop back to start
          store.setSelectedDate(dts[0]);
        }
      }, 1000 / animationSpeed);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isAnimating, animationSpeed]);

  const togglePlay = () => setAnimating(!isAnimating);

  return (
    <div
      className="glass-panel anim-fade-in-up"
      style={{
        position:       'absolute',
        bottom:         '32px',
        left:           '50%',
        transform:      'translateX(-50%)',
        width:          'min(600px, calc(100vw - 280px))',
        padding:        '14px 20px',
        zIndex:         50,
        display:        'flex',
        flexDirection:  'column',
        gap:            '10px',
      }}
    >
      {/* ── Top row: date label + speed selector ────────────────────────────── */}
      <div
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Date display */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>📅</span>
          <span
            style={{
              fontSize:   '15px',
              fontWeight: 700,
              color:      'var(--text-primary)',
              letterSpacing: '-0.2px',
            }}
          >
            {formatDate(selectedDate)}
          </span>
          {availableDates.length > 0 && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              ({sliderVal + 1} / {dates.length})
            </span>
          )}
        </div>

        {/* Speed selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginRight: '4px' }}>Speed</span>
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setAnimationSpeed(s)}
              style={{
                background:   animationSpeed === s ? 'var(--accent-blue)' : 'rgba(255,255,255,0.06)',
                border:       animationSpeed === s
                                ? '1px solid var(--accent-blue)'
                                : '1px solid rgba(255,255,255,0.1)',
                borderRadius: '6px',
                color:        animationSpeed === s ? 'white' : 'var(--text-secondary)',
                fontSize:     '11px',
                fontWeight:   600,
                padding:      '3px 8px',
                cursor:       'pointer',
                fontFamily:   'var(--font-family)',
                transition:   'all var(--transition-fast)',
              }}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* ── Date slider ─────────────────────────────────────────────────────── */}
      <div style={{ position: 'relative' }}>
        <input
          type="range"
          min={minIdx}
          max={maxIdx}
          value={sliderVal}
          onChange={onSliderChange}
          style={{
            width:       '100%',
            accentColor: 'var(--accent-blue)',
          }}
        />
        {/* Gradient track overlay */}
        {availableDates.length > 1 && (
          <div
            style={{
              position:       'absolute',
              bottom:         '6px',
              left:           0,
              width:          `${((sliderVal / maxIdx) * 100).toFixed(1)}%`,
              height:         '4px',
              background:     'linear-gradient(90deg, var(--accent-blue), rgba(59,130,246,0.5))',
              borderRadius:   '2px',
              pointerEvents:  'none',
              transition:     'width 0.1s',
            }}
          />
        )}
      </div>

      {/* ── Bottom row: prev / play-pause / next ────────────────────────────── */}
      <div
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          gap:            '10px',
        }}
      >
        {/* Prev */}
        <button
          className="btn btn-icon"
          onClick={() => stepDate(-1)}
          title="Previous day"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <ChevronLeft />
        </button>

        {/* Play / Pause */}
        <button
          onClick={togglePlay}
          title={isAnimating ? 'Pause' : 'Play animation'}
          style={{
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'center',
            gap:            '6px',
            background:     isAnimating
                              ? 'rgba(249,115,22,0.15)'
                              : 'var(--accent-blue)',
            border:         isAnimating
                              ? '1px solid rgba(249,115,22,0.4)'
                              : '1px solid var(--accent-blue)',
            borderRadius:   '50%',
            width:          '42px',
            height:         '42px',
            color:          isAnimating ? 'var(--accent-orange)' : 'white',
            cursor:         'pointer',
            transition:     'all var(--transition-normal)',
            boxShadow:      isAnimating
                              ? '0 0 20px rgba(249,115,22,0.3)'
                              : '0 0 20px rgba(59,130,246,0.4)',
          }}
        >
          {isAnimating ? <PauseIcon /> : <PlayIcon />}
        </button>

        {/* Next */}
        <button
          className="btn btn-icon"
          onClick={() => stepDate(1)}
          title="Next day"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <ChevronRight />
        </button>
      </div>
    </div>
  );
};

export default TimeControl;
