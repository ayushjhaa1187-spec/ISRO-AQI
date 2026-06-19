/**
 * store/useMapStore.ts
 * Zustand global state store for the ISRO AQI & HCHO Monitor Platform.
 * Manages map layer selection, date/animation state, and overlay toggles.
 */

import { create } from 'zustand';
import { LayerName } from '../types';

/* ─── State Shape ─────────────────────────────────────────────────────────────── */
interface MapState {
  selectedDate: string;            // "YYYY-MM-DD"
  selectedLayer: LayerName;
  isAnimating: boolean;
  animationSpeed: number;          // 0.5 | 1 | 2
  showStations: boolean;
  showHotspots: boolean;
  showWind: boolean;
  availableDates: string[];        // sorted list populated from API
  activeNav: string;

  // Actions
  setSelectedDate: (date: string) => void;
  setSelectedLayer: (layer: LayerName) => void;
  setAnimating: (val: boolean) => void;
  setAnimationSpeed: (speed: number) => void;
  setShowStations: (val: boolean) => void;
  setShowHotspots: (val: boolean) => void;
  setShowWind: (val: boolean) => void;
  setAvailableDates: (dates: string[]) => void;
  setActiveNav: (nav: string) => void;

  /** Advance date by `delta` days (respects availableDates bounds) */
  stepDate: (delta: 1 | -1) => void;
}

/* ─── Default date: today or fallback ────────────────────────────────────────── */
const todayISO = (): string => {
  const d = new Date();
  return d.toISOString().split('T')[0];
};

/* ─── Store ───────────────────────────────────────────────────────────────────── */
export const useMapStore = create<MapState>((set, get) => ({
  selectedDate:   todayISO(),
  selectedLayer:  'aqi',
  isAnimating:    false,
  animationSpeed: 1,
  showStations:   true,
  showHotspots:   true,
  showWind:       false,
  availableDates: [],
  activeNav:      'Map',

  setSelectedDate:   (date)  => set({ selectedDate: date }),
  setSelectedLayer:  (layer) => set({ selectedLayer: layer }),
  setAnimating:      (val)   => set({ isAnimating: val }),
  setAnimationSpeed: (speed) => set({ animationSpeed: speed }),
  setShowStations:   (val)   => set({ showStations: val }),
  setShowHotspots:   (val)   => set({ showHotspots: val }),
  setShowWind:       (val)   => set({ showWind: val }),
  setAvailableDates: (dates) => set({ availableDates: dates }),
  setActiveNav:      (nav)   => set({ activeNav: nav }),

  stepDate: (delta) => {
    const { selectedDate, availableDates } = get();
    if (availableDates.length === 0) {
      // No known dates — shift by `delta` calendar days
      const d = new Date(selectedDate);
      d.setDate(d.getDate() + delta);
      set({ selectedDate: d.toISOString().split('T')[0] });
      return;
    }
    const idx = availableDates.indexOf(selectedDate);
    const next = idx + delta;
    if (next >= 0 && next < availableDates.length) {
      set({ selectedDate: availableDates[next] });
    }
  },
}));

/* ─── Selector helpers ────────────────────────────────────────────────────────── */
export const selectDate  = (s: MapState) => s.selectedDate;
export const selectLayer = (s: MapState) => s.selectedLayer;
