import React, { useState, useMemo } from 'react';
import { useMapStore } from '../store/useMapStore';
import { useStations, useStationTimeseries } from '../api/hooks';
import { X, Activity, Target, Layers, Map, BarChart2, Lightbulb, Loader2, Info } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend as RechartsLegend
} from 'recharts';

const EvaluationDashboard: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);

  // Station selection state (defaults to DL001 - Anand Vihar)
  const [stationId, setStationId] = useState<string>('DL001');

  // Fetch CPCB stations list
  const { data: stationsData, isLoading: loadingStations } = useStations();

  // Fetch historical observed vs predicted timeseries for the station
  const { data: timeseriesData, isLoading: loadingTimeseries } = useStationTimeseries(stationId, '30d');

  // Compute validation statistics dynamically
  const stats = useMemo(() => {
    if (!timeseriesData || !timeseriesData.data || timeseriesData.data.length === 0) {
      return { rmse: 0, mae: 0, r: 0, count: 0 };
    }

    const points = timeseriesData.data.filter(
      (p) => p.observed !== null && p.predicted !== null
    ) as { datetime: string; observed: number; predicted: number }[];

    if (points.length === 0) {
      return { rmse: 0, mae: 0, r: 0, count: 0 };
    }

    const n = points.length;

    // RMSE = sqrt( sum( (obs - pred)^2 ) / n )
    const sumSqError = points.reduce((sum, p) => sum + Math.pow(p.observed - p.predicted, 2), 0);
    const rmse = Math.sqrt(sumSqError / n);

    // MAE = sum( |obs - pred| ) / n
    const sumAbsError = points.reduce((sum, p) => sum + Math.abs(p.observed - p.predicted), 0);
    const mae = sumAbsError / n;

    // Pearson Correlation (R)
    const meanObs = points.reduce((sum, p) => sum + p.observed, 0) / n;
    const meanPred = points.reduce((sum, p) => sum + p.predicted, 0) / n;

    let num = 0;
    let denObs = 0;
    let denPred = 0;

    for (let i = 0; i < n; i++) {
      const diffObs = points[i].observed - meanObs;
      const diffPred = points[i].predicted - meanPred;
      num += diffObs * diffPred;
      denObs += Math.pow(diffObs, 2);
      denPred += Math.pow(diffPred, 2);
    }

    const r = denObs > 0 && denPred > 0 ? num / Math.sqrt(denObs * denPred) : 0;

    return {
      rmse: parseFloat(rmse.toFixed(2)),
      mae: parseFloat(mae.toFixed(2)),
      r: parseFloat(r.toFixed(3)),
      count: n
    };
  }, [timeseriesData]);

  // Format Recharts data (convert UTC ISO string to localized day label)
  const chartData = useMemo(() => {
    if (!timeseriesData || !timeseriesData.data) return [];
    return timeseriesData.data.map((p) => {
      const d = new Date(p.datetime);
      return {
        dateLabel: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
        Observed: p.observed ? Math.round(p.observed) : null,
        Predicted: p.predicted ? Math.round(p.predicted) : null,
      };
    });
  }, [timeseriesData]);

  if (activeNav !== 'Insights' && activeNav !== 'Methodology') return null;

  const currentStationName =
    stationsData?.stations.find((s) => s.id === stationId)?.name || 'Select Station';

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 200,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        className="glass-panel anim-fade-in-up"
        style={{
          width: '90%',
          maxWidth: '960px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '36px',
          position: 'relative',
          border: '1px solid rgba(255,255,255,0.12)',
        }}
      >
        {/* Close Button */}
        <button
          onClick={() => setActiveNav('Map')}
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
          <X size={24} />
        </button>

        <h2 style={{ fontSize: '26px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
          Scientific Evaluation & Insights
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '32px' }}>
          ISRO Surface AQI & HCHO Hotspot Detection Validation Platform
        </p>

        {/* ── Objective 1: Surface AQI Model Validation ────────────────────── */}
        <div style={{ marginBottom: '44px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              paddingBottom: '12px',
              marginBottom: '20px',
            }}
          >
            <h3
              style={{
                fontSize: '18px',
                color: 'var(--accent-orange)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                margin: 0,
              }}
            >
              <Activity size={22} /> Objective-1: Surface AQI Validation
            </h3>

            {/* Station Selector Dropdown */}
            {!loadingStations && stationsData && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Station:</span>
                <select
                  value={stationId}
                  onChange={(e) => setStationId(e.target.value)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '6px',
                    padding: '5px 12px',
                    color: 'white',
                    fontSize: '12px',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  {stationsData.stations.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.city})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '20px' }}>
            Validation of the ConvLSTM surface estimation model compared with CPCB ground observations over a 30-day moving window. Statistics are calculated dynamically based on real station coordinates.
          </p>

          {/* Statistics Cards Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '16px',
              marginBottom: '24px',
            }}
          >
            {/* RMSE */}
            <div
              style={{
                background: 'rgba(59,130,246,0.04)',
                padding: '16px 20px',
                borderRadius: '10px',
                border: '1px solid rgba(59,130,246,0.2)',
              }}
            >
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                RMSE (Root Mean Square Error)
              </div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#3b82f6', marginTop: '6px' }}>
                {loadingTimeseries ? '…' : stats.rmse}{' '}
                <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)' }}>AQI Index</span>
              </div>
            </div>

            {/* MAE */}
            <div
              style={{
                background: 'rgba(16,185,129,0.04)',
                padding: '16px 20px',
                borderRadius: '10px',
                border: '1px solid rgba(16,185,129,0.2)',
              }}
            >
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                MAE (Mean Absolute Error)
              </div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#10b981', marginTop: '6px' }}>
                {loadingTimeseries ? '…' : stats.mae}{' '}
                <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)' }}>AQI Index</span>
              </div>
            </div>

            {/* Pearson R */}
            <div
              style={{
                background: 'rgba(139,92,246,0.04)',
                padding: '16px 20px',
                borderRadius: '10px',
                border: '1px solid rgba(139,92,246,0.2)',
              }}
            >
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                R (Pearson Correlation)
              </div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#8b5cf6', marginTop: '6px' }}>
                {loadingTimeseries ? '…' : stats.r}{' '}
                <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-muted)' }}>
                  ({stats.count} days)
                </span>
              </div>
            </div>
          </div>

          {/* Time Series Chart */}
          <div
            style={{
              background: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '12px',
              padding: '20px',
              height: '320px',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {loadingTimeseries ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <Loader2 className="animate-spin" size={24} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Loading station timeseries…</span>
              </div>
            ) : chartData.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={16} /> No comparison data available for {currentStationName}.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="dateLabel" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(17, 24, 39, 0.95)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <RechartsLegend verticalAlign="top" height={36} iconSize={10} wrapperStyle={{ fontSize: '12px' }} />
                  <Line
                    type="monotone"
                    dataKey="Observed"
                    name="Observed (Ground)"
                    stroke="var(--accent-blue)"
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 5 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="Predicted"
                    name="Predicted (ConvLSTM Model)"
                    stroke="var(--accent-orange)"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={{ r: 2 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Objective 2: Multi-source Fusion & Hotspot Quality ──────────────── */}
        <div>
          <h3
            style={{
              fontSize: '18px',
              color: 'var(--accent-orange)',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              paddingBottom: '12px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Target size={22} /> Objective-2: HCHO Hotspots & Transport Validation
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.04)' }}>
              <div style={{ color: '#f97316', padding: '10px', background: 'rgba(249,115,22,0.08)', borderRadius: '8px' }}><Target size={20} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Hotspot Clustered Delineation
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Utilizes localized spatial Getis-Ord Gi* statististics to identify clusters of statistically significant formaldehyde (+2σ anomalies) over crop-residue burning zones (e.g. Punjab) and heavy industrial sectors.
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.04)' }}>
              <div style={{ color: '#3b82f6', padding: '10px', background: 'rgba(59,130,246,0.08)', borderRadius: '8px' }}><Layers size={20} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Multi-Source Satellite Fusion
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Fuses Sentinel-5P (HCHO), MODIS/VIIRS (Fire Radiative Power), and ground-level CPCB monitoring sensor data. The grids are dynamically combined to calculate fire-to-plume lag correlation profiles.
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.04)' }}>
              <div style={{ color: '#10b981', padding: '10px', background: 'rgba(16,185,129,0.08)', borderRadius: '8px' }}><BarChart2 size={20} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Temporal Correlation & Lag
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Performs a daily Pearson and Spearman rank correlation mapping with a 0-to-3-day lag coefficient to identify transport-induced column enhancements over downwind regions (e.g. advection towards New Delhi).
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvaluationDashboard;
