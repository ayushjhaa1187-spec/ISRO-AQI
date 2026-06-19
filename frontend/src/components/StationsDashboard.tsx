import React from 'react';
import { useMapStore } from '../store/useMapStore';
import { X, MapPin } from 'lucide-react';
import { useStations } from '../api/hooks';
import type { StationSummary } from '../types';

const StationsDashboard: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);
  const { data: stationsData, isLoading } = useStations();

  if (activeNav !== 'Stations') return null;

  return (
    <div
      style={{
        position: 'absolute', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}
    >
      <div className="glass-panel" style={{ width: '90%', maxWidth: '800px', maxHeight: '80vh', overflowY: 'auto', padding: '40px', position: 'relative' }}>
        <button
          onClick={() => setActiveNav('Map')}
          style={{ position: 'absolute', top: '20px', right: '20px', background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
        >
          <X size={24} />
        </button>

        <h2 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>Ground Stations</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>CPCB Ground Monitoring Sensors</p>

        {isLoading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading stations...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
            {stationsData?.stations.map((station: StationSummary) => (
              <div key={station.id} style={{ background: 'rgba(255,255,255,0.05)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <MapPin size={16} color="var(--accent-blue)" />
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{station.name}</span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{station.city}</div>
                <div style={{ marginTop: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  AQI: <span style={{ fontWeight: 600, color: station.category ? 'var(--aqi-' + station.category.toLowerCase().replace(' ', '-') + ')' : '#fff' }}>{station.aqi ? Math.round(station.aqi) : 'N/A'}</span> ({station.category || 'Unknown'})
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StationsDashboard;
