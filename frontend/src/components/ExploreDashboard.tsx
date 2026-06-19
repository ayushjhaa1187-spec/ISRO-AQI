import React, { useState, useEffect } from 'react';
import { useMapStore } from '../store/useMapStore';
import { X, Compass, Download, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { apiClient } from '../api/client';

interface ExportJobResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  layer: string;
  start: string;
  end: string;
  format: 'geotiff' | 'csv' | 'pdf';
  progress_pct: number;
  download_url: string | null;
  error_message: string | null;
}

const ExploreDashboard: React.FC = () => {
  const activeNav = useMapStore((s) => s.activeNav);
  const setActiveNav = useMapStore((s) => s.setActiveNav);
  const selectedDate = useMapStore((s) => s.selectedDate);
  const availableDates = useMapStore((s) => s.availableDates);

  // Form State
  const [layer, setLayer] = useState<string>('aqi');
  const [format, setFormat] = useState<'geotiff' | 'csv' | 'pdf'>('geotiff');
  const [startDate, setStartDate] = useState<string>(selectedDate);
  const [endDate, setEndDate] = useState<string>(selectedDate);

  // Job Polling State
  const [exporting, setExporting] = useState<boolean>(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Set default dates when availableDates is loaded
  useEffect(() => {
    if (availableDates.length > 0) {
      setStartDate(availableDates[0]);
      setEndDate(availableDates[availableDates.length - 1]);
    } else {
      setStartDate(selectedDate);
      setEndDate(selectedDate);
    }
  }, [availableDates, selectedDate]);

  // Cleanup polling on unmount
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    
    if (exporting && jobId) {
      interval = setInterval(async () => {
        try {
          const { data } = await apiClient.get<ExportJobResponse>(`/export/${jobId}`);
          setProgress(data.progress_pct);
          setJobStatus(data.status);
          
          if (data.status === 'completed') {
            setExporting(false);
            // Construct full URL since backend returns relative download path
            const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
            const host = base.replace(/\/api\/v1$/, '');
            setDownloadUrl(data.download_url ? `${host}${data.download_url}` : null);
            clearInterval(interval);
          } else if (data.status === 'failed') {
            setExporting(false);
            setErrorMsg(data.error_message || 'Export job failed on server.');
            clearInterval(interval);
          }
        } catch (err: any) {
          console.error('Error polling export job:', err);
          setExporting(false);
          setErrorMsg('Failed to fetch export job status. Connection lost.');
          clearInterval(interval);
        }
      }, 800); // Poll every 800ms
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [exporting, jobId]);

  const handleStartExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setExporting(true);
    setJobId(null);
    setProgress(0);
    setJobStatus('submitting');
    setDownloadUrl(null);
    setErrorMsg(null);

    try {
      const { data } = await apiClient.post<ExportJobResponse>('/export', {
        layer,
        start: startDate,
        end: endDate,
        format,
      });

      setJobId(data.job_id);
      setJobStatus(data.status);
      setProgress(data.progress_pct);
    } catch (err: any) {
      console.error('Error submitting export job:', err);
      setExporting(false);
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Failed to submit export job. Please check dates and layer selection.');
    }
  };

  if (activeNav !== 'Explore') return null;

  return (
    <div
      style={{
        position: 'absolute', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        className="glass-panel anim-fade-in-up"
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '32px',
          position: 'relative',
          border: '1px solid rgba(255,255,255,0.12)',
        }}
      >
        {/* Close Button */}
        <button
          onClick={() => setActiveNav('Map')}
          style={{
            position: 'absolute', top: '20px', right: '20px',
            background: 'transparent', border: 'none', color: 'var(--text-secondary)',
            cursor: 'pointer', transition: 'color var(--transition-fast)'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
        >
          <X size={24} />
        </button>

        <h2 style={{ fontSize: '26px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Compass size={28} color="var(--accent-blue)" /> Explore & Export Datasets
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '28px' }}>
          Query, filter, and extract Spatio-Temporal satellite-derived data for India.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          {/* Main Info */}
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <p style={{ color: 'var(--text-primary)', fontSize: '13px', lineHeight: 1.6 }}>
              This portal allows you to export grid-level raster files and time-series reports. Grids are reprojected to the canonical <strong>0.05° spatial resolution (EPSG:4326)</strong>.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleStartExport} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              
              {/* Layer Selection */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Target Variable / Layer
                </label>
                <select
                  value={layer}
                  onChange={(e) => setLayer(e.target.value)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                >
                  <option value="aqi">Composite AQI Index</option>
                  <option value="hcho">HCHO Column Density</option>
                  <option value="fire">Fire Density (FRP)</option>
                  <option value="pm25">PM2.5 Particulates</option>
                  <option value="pm10">PM10 Particulates</option>
                </select>
              </div>

              {/* Format Selection */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Output Format
                </label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value as any)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                >
                  <option value="geotiff">GeoTIFF (Raster Grid)</option>
                  <option value="csv">CSV (Pixel Values)</option>
                  <option value="pdf">PDF (Full Map Report)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              
              {/* Start Date */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '6px',
                    padding: '7px 12px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              {/* End Date */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '6px',
                    padding: '7px 12px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            {/* Actions / Export Progress */}
            <div style={{ marginTop: '12px' }}>
              {!exporting && !jobId && !errorMsg && !downloadUrl && (
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ display: 'flex', gap: '8px', alignItems: 'center', width: '100%', padding: '12px 20px', justifyContent: 'center' }}
                >
                  <Download size={16} /> Request Dataset Export
                </button>
              )}

              {/* Loader / Polling details */}
              {exporting && (
                <div style={{ background: 'rgba(59,130,246,0.05)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: 'white', fontWeight: 600 }}>
                      <Loader2 className="animate-spin" size={16} color="var(--accent-blue)" style={{ animation: 'spin 1s linear infinite' }} />
                      <span>Processing Export Job...</span>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: 700 }}>{progress}%</span>
                  </div>
                  {/* Progress track */}
                  <div style={{ height: '6px', background: 'var(--bg-elevated)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${progress}%`, background: 'var(--accent-blue)', transition: 'width 0.2s' }}></div>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', fontFamily: 'monospace' }}>
                    Job ID: {jobId || 'Allocating...'} | Status: {jobStatus}
                  </div>
                </div>
              )}

              {/* Complete State */}
              {downloadUrl && !exporting && (
                <div style={{ background: 'rgba(16,185,129,0.06)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(16,185,129,0.25)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <CheckCircle2 color="#10b981" size={20} />
                    <span style={{ fontSize: '14px', fontWeight: 600, color: 'white' }}>Data Export Complete!</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Your customized data file is compiled and ready for download.
                  </p>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <a
                      href={downloadUrl}
                      download
                      className="btn btn-primary"
                      style={{ background: '#10b981', display: 'inline-flex', gap: '8px', textDecoration: 'none' }}
                    >
                      <Download size={16} /> Download File
                    </a>
                    <button
                      type="button"
                      onClick={() => { setJobId(null); setDownloadUrl(null); }}
                      className="btn"
                      style={{ background: 'rgba(255,255,255,0.06)', color: 'white', border: '1px solid rgba(255,255,255,0.1)' }}
                    >
                      Export Another
                    </button>
                  </div>
                </div>
              )}

              {/* Failed State / Errors */}
              {errorMsg && (
                <div style={{ background: 'rgba(239,68,68,0.06)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.25)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <AlertCircle color="#ef4444" size={20} />
                    <span style={{ fontSize: '14px', fontWeight: 600, color: 'white' }}>Export Request Failed</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Error: {errorMsg}
                  </p>
                  <button
                    type="button"
                    onClick={() => { setErrorMsg(null); setJobId(null); }}
                    className="btn"
                    style={{ alignSelf: 'flex-start', background: 'rgba(255,255,255,0.06)', color: 'white', border: '1px solid rgba(255,255,255,0.1)' }}
                  >
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ExploreDashboard;
