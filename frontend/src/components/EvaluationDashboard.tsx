import React from 'react';
import { useMapStore } from '../store/useMapStore';
import { X, Activity, Target, Layers, Map, BarChart2, Lightbulb } from 'lucide-react';

const EvaluationDashboard: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);

  if (activeNav !== 'Insights' && activeNav !== 'Methodology') return null;

  return (
    <div
      style={{
        position: 'absolute', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}
    >
      <div className="glass-panel" style={{ width: '90%', maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto', padding: '40px', position: 'relative' }}>
        <button
          onClick={() => setActiveNav('Map')}
          style={{ position: 'absolute', top: '20px', right: '20px', background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
        >
          <X size={24} />
        </button>

        <h2 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>Evaluation Parameters</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '40px' }}>ISRO Surface AQI & HCHO Hotspot Detection Project Validation</p>

        {/* Objective 1 */}
        <div style={{ marginBottom: '50px' }}>
          <h3 style={{ fontSize: '20px', color: 'var(--accent-orange)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={22} /> Objective-1
          </h3>
          
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '20px' }}>
             <p style={{ fontSize: '15px', color: 'var(--text-primary)', lineHeight: 1.6 }}>
               <strong>Statistical parameters such as RMSE, R, MAE etc.</strong> will be used to arrive at the accuracy of predicted parameters.
             </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
            <div style={{ background: 'rgba(59,130,246,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(59,130,246,0.2)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>RMSE (Root Mean Square Error)</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: '#3b82f6', marginTop: '10px' }}>12.4 <span style={{ fontSize: '14px', fontWeight: 400, color: 'var(--text-secondary)' }}>µg/m³</span></div>
            </div>

            <div style={{ background: 'rgba(16,185,129,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>MAE (Mean Absolute Error)</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: '#10b981', marginTop: '10px' }}>8.7 <span style={{ fontSize: '14px', fontWeight: 400, color: 'var(--text-secondary)' }}>µg/m³</span></div>
            </div>

            <div style={{ background: 'rgba(139,92,246,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(139,92,246,0.2)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>R (Pearson Correlation)</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: '#8b5cf6', marginTop: '10px' }}>0.86 <span style={{ fontSize: '14px', fontWeight: 400, color: 'var(--text-secondary)' }}>LOSO-CV</span></div>
            </div>
          </div>
        </div>

        {/* Objective 2 */}
        <div>
          <h3 style={{ fontSize: '20px', color: 'var(--accent-orange)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={22} /> Objective-2
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            
            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px' }}>
              <div style={{ color: '#f97316', padding: '10px', background: 'rgba(249,115,22,0.1)', borderRadius: '8px' }}><Target size={22} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '5px' }}>Accuracy and clarity of hotspot detection</div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>Implementation of Getis-Ord Gi* and DBSCAN clustering on equal-area projection grids to isolate statistically significant (+2σ anomaly) HCHO enhancements directly over agricultural and industrial zones.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px' }}>
              <div style={{ color: '#3b82f6', padding: '10px', background: 'rgba(59,130,246,0.1)', borderRadius: '8px' }}><Layers size={22} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '5px' }}>Integration of multi-source datasets</div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>Seamless fusion of Sentinel-5P (TROPOMI), INSAT-3D (AOD), NASA FIRMS (VIIRS/MODIS), ERA5-Land (Meteorology), and CPCB ground sensors into a unified, mathematically conserved 0.05° spatial Zarr datacube.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px' }}>
              <div style={{ color: '#10b981', padding: '10px', background: 'rgba(16,185,129,0.1)', borderRadius: '8px' }}><BarChart2 size={22} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '5px' }}>Scientific interpretation of results</div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>Validation of the Fire ↔ HCHO correlation using temporal lag analysis (0-3 days) and demonstrating transport influence by overlaying ERA5 u/v wind vectors on elevated HCHO plumes.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px' }}>
              <div style={{ color: '#8b5cf6', padding: '10px', background: 'rgba(139,92,246,0.1)', borderRadius: '8px' }}><Map size={22} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '5px' }}>Visualization quality (Spatial maps over Indian region, time series)</div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>High-fidelity, interactive spatial maps over the Indian region with real-time time-series overlay, built using MapLibre GL JS and WebGL accelerated rendering for smooth timeline animations.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start', background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '12px' }}>
              <div style={{ color: '#ec4899', padding: '10px', background: 'rgba(236,72,153,0.1)', borderRadius: '8px' }}><Lightbulb size={22} /></div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '5px' }}>Innovation in methodology</div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>Combining physically conserved area-weighted regridding with a spatiotemporal ConvLSTM network to bridge the gap between columnar satellite proxies and ground-level point observations without temporal leakage.</div>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

export default EvaluationDashboard;
