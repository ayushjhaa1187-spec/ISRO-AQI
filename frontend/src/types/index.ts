/**
 * types/index.ts
 * TypeScript interfaces matching the backend Pydantic schemas for the
 * ISRO AQI & HCHO Monitor Platform.
 */

/* ─── AQI Categories ──────────────────────────────────────────────────────────── */
export type AQICategory =
  | 'Good'
  | 'Satisfactory'
  | 'Moderate'
  | 'Poor'
  | 'Very Poor'
  | 'Severe';

/* ─── Pollutant Layer Names ───────────────────────────────────────────────────── */
export type LayerName = 'aqi' | 'no2' | 'so2' | 'co' | 'o3' | 'hcho' | 'fire';

/* ─── AQI Point Response ──────────────────────────────────────────────────────── */
export interface AQIResponse {
  latitude: number;
  longitude: number;
  date: string;                    // ISO date string "YYYY-MM-DD"
  aqi: number;
  category: AQICategory;
  dominant_pollutant: string;      // e.g. "PM2.5", "HCHO", "NO2"
  health_advice: string;
  is_predicted: boolean;
  pollutants: Record<string, number | null>; // { pm25: 45.2, no2: 30.1, ... }
}

/* ─── Hotspot GeoJSON Feature ─────────────────────────────────────────────────── */
export interface HotspotProperties {
  id: string;
  date: string;
  significance: number;            // 0–1 score
  pollutant: string;               // "hcho" | "no2" | ...
  peak_value: number;
  area_km2: number;
  source_type: string;             // "industrial" | "agricultural" | "natural"
}

export interface HotspotFeature {
  type: 'Feature';
  geometry: {
    type: 'Polygon' | 'MultiPolygon';
    coordinates: number[][][] | number[][][][];
  };
  properties: HotspotProperties;
}

export interface HotspotCollection {
  type: 'FeatureCollection';
  features: HotspotFeature[];
  total: number;
  date_range: { start: string; end: string };
}

/* ─── Station Summary ─────────────────────────────────────────────────────────── */
export interface StationSummary {
  id: string;
  name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  aqi: number | null;
  category: AQICategory | null;
  dominant_pollutant: string | null;
  last_updated: string;            // ISO datetime string
  is_active: boolean;
}

export interface StationsResponse {
  stations: StationSummary[];
  total: number;
}

/* ─── Timeseries Point ────────────────────────────────────────────────────────── */
export interface TimeseriesPoint {
  datetime: string;               // ISO datetime string
  observed: number | null;        // Observed AQI value
  predicted: number | null;       // ML-predicted AQI value
  pollutant: string;              // e.g. "AQI"
}

export interface TimeseriesResponse {
  station_id: string;
  station_name: string;
  range_days: number;
  data: TimeseriesPoint[];
}

/* ─── Fire Point ──────────────────────────────────────────────────────────────── */
export interface FirePoint {
  latitude: number;
  longitude: number;
  date: string;
  brightness: number;              // Kelvin
  confidence: number;              // 0–100
  frp: number;                     // Fire Radiative Power (MW)
  satellite: string;               // "MODIS" | "VIIRS"
}

export interface FireResponse {
  date: string;
  points: FirePoint[];
  total: number;
}

/* ─── Available Dates ─────────────────────────────────────────────────────────── */
export interface AvailableDatesResponse {
  layer: LayerName;
  dates: string[];                 // sorted array of "YYYY-MM-DD"
}

/* ─── Generic API Error ───────────────────────────────────────────────────────── */
export interface APIError {
  status: number;
  message: string;
  detail?: string;
}
