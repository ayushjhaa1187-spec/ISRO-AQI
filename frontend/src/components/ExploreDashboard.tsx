import React from 'react';
import { useMapStore } from '../store/useMapStore';
import { X, Compass } from 'lucide-react';

const ExploreDashboard: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);

  if (activeNav !== 'Explore') return null;

  return (
    <div
      style={{
        position: 'absolute', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}
    >
      <div className="glass-panel" style={{ width: '90%', maxWidth: '700px', padding: '40px', position: 'relative' }}>
        <button
          onClick={() => setActiveNav('Map')}
          style={{ position: 'absolute', top: '20px', right: '20px', background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
        >
          <X size={24} />
        </button>

        <h2 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Compass size={28} color="var(--accent-blue)" /> Explore Data
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>
          Interactive Data Exploration Tools
        </p>

        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
          <p style={{ color: 'var(--text-primary)', lineHeight: 1.6 }}>
            The Explore tool allows you to interactively query the Zarr datacube and visualize cross-sections of the Spatio-Temporal datasets.
          </p>
          <p style={{ color: 'var(--text-muted)', marginTop: '20px', fontStyle: 'italic' }}>
            Interactive charts and historical data exports will be available in the next platform update. For now, please use the <strong>Map</strong> to visualize the current spatial distributions.
          </p>
          
          <div style={{ display: 'flex', gap: '15px', marginTop: '30px' }}>
            <button 
              onClick={() => setActiveNav('Map')}
              className="btn btn-primary" 
            >
              Return to Map
            </button>

            <button 
              onClick={() => alert("PDF Export will be available in v2.")}
              className="btn btn-icon"
              style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-blue)', border: '1px solid var(--accent-blue)' }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Export Report (PDF)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExploreDashboard;
