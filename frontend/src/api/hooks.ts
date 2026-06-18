/**
 * api/hooks.ts
 * React Query hooks for all backend API endpoints.
 * Each hook is fully typed, handles loading/error states,
 * and uses smart caching to minimise redundant requests.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  AQIResponse,
  HotspotCollection,
  StationsResponse,
  TimeseriesResponse,
  AvailableDatesResponse,
  FireResponse,
  LayerName,
} from '../types';

/* ─── Query Key Factory ───────────────────────────────────────────────────────── */
export const queryKeys = {
  aqiPoint:          (lat: number, lon: number, date: string) =>
                       ['aqi', 'point', lat, lon, date] as const,
  hotspots:          (start: string, end: string) =>
                       ['hotspots', start, end] as const,
  stations:          () => ['stations'] as const,
  stationTimeseries: (id: string, range: string) =>
                       ['stations', id, 'timeseries', range] as const,
  availableDates:    (layer: LayerName) =>
                       ['dates', layer] as const,
  firePoints:        (date: string) =>
                       ['fire', 'points', date] as const,
};

/* ─── useAQIPoint ─────────────────────────────────────────────────────────────── */
/**
 * Fetches AQI and pollutant concentrations for a given lat/lon and date.
 * Used when the user clicks on the map.
 */
export function useAQIPoint(
  lat: number | null,
  lon: number | null,
  date: string
) {
  return useQuery<AQIResponse>({
    queryKey: queryKeys.aqiPoint(lat ?? 0, lon ?? 0, date),
    queryFn: async () => {
      const { data } = await apiClient.get<AQIResponse>('/aqi/point', {
        params: { lat, lon, date },
      });
      return data;
    },
    enabled: lat !== null && lon !== null && !!date,
    staleTime: 5 * 60 * 1_000,   // 5 minutes
    retry: 1,
  });
}

/* ─── useHotspots ─────────────────────────────────────────────────────────────── */
/**
 * Fetches HCHO / pollutant hotspot GeoJSON features for a date range.
 */
export function useHotspots(start: string, end: string) {
  return useQuery<HotspotCollection>({
    queryKey: queryKeys.hotspots(start, end),
    queryFn: async () => {
      const { data } = await apiClient.get<HotspotCollection>('/hotspots', {
        params: { start, end },
      });
      return data;
    },
    enabled: !!start && !!end,
    staleTime: 10 * 60 * 1_000,  // 10 minutes
    retry: 1,
  });
}

/* ─── useStations ─────────────────────────────────────────────────────────────── */
/**
 * Fetches the list of all monitoring stations with their current AQI.
 */
export function useStations() {
  return useQuery<StationsResponse>({
    queryKey: queryKeys.stations(),
    queryFn: async () => {
      const { data } = await apiClient.get<StationsResponse>('/stations');
      return data;
    },
    staleTime: 5 * 60 * 1_000,
    retry: 2,
  });
}

/* ─── useStationTimeseries ────────────────────────────────────────────────────── */
/**
 * Fetches hourly/daily timeseries data for a specific station.
 * `range` can be "7d" | "30d" | "90d" etc.
 */
export function useStationTimeseries(id: string, range: string) {
  return useQuery<TimeseriesResponse>({
    queryKey: queryKeys.stationTimeseries(id, range),
    queryFn: async () => {
      const { data } = await apiClient.get<TimeseriesResponse>(
        `/stations/${id}/timeseries`,
        { params: { range } }
      );
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1_000,
    retry: 1,
  });
}

/* ─── useAvailableDates ───────────────────────────────────────────────────────── */
/**
 * Fetches the list of dates for which raster tiles exist for a given layer.
 */
export function useAvailableDates(layer: LayerName) {
  return useQuery<AvailableDatesResponse>({
    queryKey: queryKeys.availableDates(layer),
    queryFn: async () => {
      const { data } = await apiClient.get<AvailableDatesResponse>(
        '/tiles/dates',
        { params: { layer } }
      );
      return data;
    },
    enabled: !!layer,
    staleTime: 30 * 60 * 1_000,  // 30 minutes — tile dates don't change often
    retry: 1,
  });
}

/* ─── useFirePoints ───────────────────────────────────────────────────────────── */
/**
 * Fetches active fire / hotspot points from MODIS/VIIRS for a given date.
 */
export function useFirePoints(date: string) {
  return useQuery<FireResponse>({
    queryKey: queryKeys.firePoints(date),
    queryFn: async () => {
      const { data } = await apiClient.get<FireResponse>('/fire/points', {
        params: { date },
      });
      return data;
    },
    enabled: !!date,
    staleTime: 10 * 60 * 1_000,
    retry: 1,
  });
}
