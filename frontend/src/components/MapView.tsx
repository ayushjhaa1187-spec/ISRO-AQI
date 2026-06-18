/**
 * components/MapView.tsx
 * Full-screen MapLibre GL map component for the ISRO AQI & HCHO Monitor.
 * Features:
 *  - Dark basemap (CartoDB Dark Matter)
 *  - India boundary GeoJSON outline layer
 *  - AQI raster tile overlay (swappable by date/layer)
 *  - Station markers (circle layer, AQI-colored)
 *  - Hotspot polygon layer (significance-colored)
 *  - Click-to-popup with AQI data via API
 *  - "No data" overlay when tiles 404
 *  - Reactive to Zustand store (selectedDate, selectedLayer, toggles)
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl, { Map, Popup, GeoJSONSource } from 'maplibre-gl';
import { useMapStore } from '../store/useMapStore';
import { useStations, useHotspots, useAvailableDates } from '../api/hooks';
import { apiClient } from '../api/client';
import { buildAQIPopupHTML, AQI_CATEGORY_COLOR } from './AQIPopup';
import type { AQIResponse, AQICategory, StationSummary } from '../types';

/* ─── India boundary GeoJSON URL (public domain) ─────────────────────────────── */
const INDIA_BOUNDARY_URL =
  'https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson';

/* ─── Tile URL builder ────────────────────────────────────────────────────────── */
const tileURL = (layer: string, date: string) =>
  `http://localhost:8001/tiles/${layer}/{z}/{x}/{y}.png?date=${date}`;

/* ─── AQI category → hex (for station markers) ───────────────────────────────── */
const CAT_COLORS: Record<AQICategory, string> = AQI_CATEGORY_COLOR;

const MapView: React.FC = () => {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef       = useRef<Map | null>(null);
  const popupRef     = useRef<Popup | null>(null);

  const selectedDate  = useMapStore((s) => s.selectedDate);
  const selectedLayer = useMapStore((s) => s.selectedLayer);
  const showStations  = useMapStore((s) => s.showStations);
  const showHotspots  = useMapStore((s) => s.showHotspots);
  const setAvailableDates = useMapStore((s) => s.setAvailableDates);

  const [noData, setNoData] = useState(false);
  const [mapLoaded, setMapLoaded] = useState(false);

  /* ─── Data hooks ──────────────────────────────────────────────────────────── */
  const { data: stationsData }  = useStations();
  const { data: hotspotsData }  = useHotspots(selectedDate, selectedDate);
  const { data: datesData }     = useAvailableDates(selectedLayer);

  /* ─── Sync available dates to store ──────────────────────────────────────── */
  useEffect(() => {
    if (datesData?.dates) setAvailableDates(datesData.dates);
  }, [datesData, setAvailableDates]);

  /* ─── Initialise map ──────────────────────────────────────────────────────── */
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [82.5, 22.5],
      zoom: 4.5,
      minZoom: 3,
      maxZoom: 14,
      attributionControl: true,
    });

    mapRef.current = map;

    /* ── Navigation controls ──────────────────────────────────────────────── */
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');

    map.on('load', () => {
      /* ── India boundary ─────────────────────────────────────────────────── */
      map.addSource('india-boundary', {
        type: 'geojson',
        data: INDIA_BOUNDARY_URL,
      });

      map.addLayer({
        id:     'india-boundary-fill',
        type:   'fill',
        source: 'india-boundary',
        paint: {
          'fill-color':   '#3b82f6',
          'fill-opacity': 0.03,
        },
      });

      map.addLayer({
        id:     'india-boundary-line',
        type:   'line',
        source: 'india-boundary',
        paint: {
          'line-color':   '#3b82f6',
          'line-width':   0.5,
          'line-opacity': 0.6,
        },
      });

      /* ── AQI raster tile overlay ──────────────────────────────────────── */
      map.addSource('aqi-tiles', {
        type:   'raster',
        tiles:  [tileURL(selectedLayer, selectedDate)],
        tileSize: 256,
      });

      map.addLayer({
        id:      'aqi-raster',
        type:    'raster',
        source:  'aqi-tiles',
        paint: {
          'raster-opacity':   0.75,
          'raster-fade-duration': 300,
        },
      });

      /* ── Hotspot source (empty initially) ────────────────────────────── */
      map.addSource('hotspots', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id:     'hotspots-fill',
        type:   'fill',
        source: 'hotspots',
        paint: {
          'fill-color': [
            'interpolate', ['linear'],
            ['get', 'significance'],
            0,   '#fbbf24',
            0.5, '#f97316',
            1,   '#ef4444',
          ],
          'fill-opacity': 0.4,
        },
      });

      map.addLayer({
        id:     'hotspots-outline',
        type:   'line',
        source: 'hotspots',
        paint: {
          'line-color':   '#f97316',
          'line-width':   1.5,
          'line-opacity': 0.8,
        },
      });

      /* ── Station markers source (empty initially) ─────────────────────── */
      map.addSource('stations', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id:     'stations-outer',
        type:   'circle',
        source: 'stations',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 5, 10, 9],
          'circle-color':  ['get', 'color'],
          'circle-opacity': 0.25,
        },
      });

      map.addLayer({
        id:     'stations-circle',
        type:   'circle',
        source: 'stations',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 7],
          'circle-color':  ['get', 'color'],
          'circle-stroke-width': 1.5,
          'circle-stroke-color': 'rgba(255,255,255,0.4)',
        },
      });

      /* ── Hover: station tooltip ───────────────────────────────────────── */
      const hoverPopup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 10,
      });

      map.on('mouseenter', 'stations-circle', (e) => {
        map.getCanvas().style.cursor = 'pointer';
        const feat = e.features?.[0];
        if (!feat) return;
        const { name, city, aqi, category } = feat.properties as {
          name: string; city: string; aqi: number | null; category: string;
        };
        hoverPopup
          .setLngLat(e.lngLat)
          .setHTML(`
            <div style="font-family:'Inter',sans-serif;padding:10px 12px;min-width:160px;">
              <div style="font-weight:600;font-size:13px;color:#f1f5f9;margin-bottom:2px;">${name}</div>
              <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">${city}</div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="font-size:18px;font-weight:700;color:#f1f5f9;">${aqi != null ? Math.round(aqi) : 'N/A'}</span>
                <span style="font-size:11px;font-weight:600;color:#94a3b8;">${category ?? ''}</span>
              </div>
            </div>
          `)
          .addTo(map);
      });

      map.on('mouseleave', 'stations-circle', () => {
        map.getCanvas().style.cursor = '';
        hoverPopup.remove();
      });

      /* ── Click: fetch AQI and show detailed popup ─────────────────────── */
      map.on('click', async (e) => {
        const { lng, lat } = e.lngLat;
        const coordLabel   = `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`;

        // Close existing popup
        popupRef.current?.remove();

        // Loading popup
        const loadingPopup = new maplibregl.Popup({
          closeButton: true,
          maxWidth:    '280px',
          offset: 12,
        })
          .setLngLat(e.lngLat)
          .setHTML(`
            <div style="padding:20px;text-align:center;font-family:'Inter',sans-serif;">
              <div style="width:24px;height:24px;border:3px solid rgba(59,130,246,0.3);border-top-color:#3b82f6;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 10px;"></div>
              <div style="font-size:12px;color:#94a3b8;">Fetching AQI data…</div>
              <div style="font-size:10px;color:#475569;margin-top:4px;font-family:monospace;">${coordLabel}</div>
            </div>
          `)
          .addTo(map);
        popupRef.current = loadingPopup;

        try {
          const { data } = await apiClient.get<AQIResponse>('/aqi/point', {
            params: { lat, lon: lng, date: selectedDate },
          });

          loadingPopup.remove();

          const detailPopup = new maplibregl.Popup({
            closeButton: true,
            maxWidth:    '300px',
            offset: 12,
          })
            .setLngLat(e.lngLat)
            .setHTML(buildAQIPopupHTML(data, coordLabel))
            .addTo(map);
          popupRef.current = detailPopup;

        } catch {
          loadingPopup.setHTML(`
            <div style="padding:16px;font-family:'Inter',sans-serif;">
              <div style="font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:6px;">No Data Available</div>
              <div style="font-size:12px;color:#94a3b8;">No AQI data for this location on ${selectedDate}.</div>
              <div style="font-size:10px;color:#475569;margin-top:8px;font-family:monospace;">${coordLabel}</div>
            </div>
          `);
        }
      });

      /* ── Raster tile error detection ──────────────────────────────────── */
      map.on('error', (e) => {
        if (e.error?.message?.includes('404') || (e as any).tile) {
          setNoData(true);
          setTimeout(() => setNoData(false), 4000);
        }
      });

      setMapLoaded(true);
    });

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ─── Swap tile source when date/layer changes ────────────────────────────── */
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    const src  = map.getSource('aqi-tiles') as maplibregl.RasterTileSource | undefined;
    if (src) {
      src.setTiles([tileURL(selectedLayer, selectedDate)]);
      setNoData(false);
    }
  }, [selectedDate, selectedLayer, mapLoaded]);

  /* ─── Update station markers ──────────────────────────────────────────────── */
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !stationsData) return;
    const map = mapRef.current;
    const src  = map.getSource('stations') as GeoJSONSource | undefined;
    if (!src) return;

    const features = stationsData.stations.map((s: StationSummary) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [s.longitude, s.latitude] },
      properties: {
        id:       s.id,
        name:     s.name,
        city:     s.city,
        aqi:      s.aqi,
        category: s.category,
        color:    s.category ? CAT_COLORS[s.category] ?? '#888' : '#888',
      },
    }));
    src.setData({ type: 'FeatureCollection', features });
  }, [stationsData, mapLoaded]);

  /* ─── Update hotspot polygons ─────────────────────────────────────────────── */
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    const src  = map.getSource('hotspots') as GeoJSONSource | undefined;
    if (!src) return;

    if (hotspotsData) {
      src.setData(hotspotsData as any);
    } else {
      src.setData({ type: 'FeatureCollection', features: [] });
    }
  }, [hotspotsData, mapLoaded]);

  /* ─── Toggle station visibility ───────────────────────────────────────────── */
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    const vis  = showStations ? 'visible' : 'none';
    if (map.getLayer('stations-circle')) map.setLayoutProperty('stations-circle', 'visibility', vis);
    if (map.getLayer('stations-outer'))  map.setLayoutProperty('stations-outer',  'visibility', vis);
  }, [showStations, mapLoaded]);

  /* ─── Toggle hotspot visibility ───────────────────────────────────────────── */
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    const vis  = showHotspots ? 'visible' : 'none';
    if (map.getLayer('hotspots-fill'))    map.setLayoutProperty('hotspots-fill',    'visibility', vis);
    if (map.getLayer('hotspots-outline')) map.setLayoutProperty('hotspots-outline', 'visibility', vis);
  }, [showHotspots, mapLoaded]);

  /* ─── Resize map on window resize ────────────────────────────────────────── */
  const handleResize = useCallback(() => {
    mapRef.current?.resize();
  }, []);

  useEffect(() => {
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

  /* ─── Render ──────────────────────────────────────────────────────────────── */
  return (
    <div
      className="map-container"
      style={{ width: '100%', height: '100%', position: 'absolute', inset: 0 }}
    >
      {/* MapLibre GL target */}
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* "No data" overlay */}
      {noData && (
        <div className="no-data-overlay">
          ⚠️ No tile data available for this date
        </div>
      )}
    </div>
  );
};

export default MapView;
