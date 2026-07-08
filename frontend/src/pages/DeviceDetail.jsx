import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar, Line, Area, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ZAxis,
} from 'recharts';
import { AlertTriangle, TrendingUp, Lightbulb, RefreshCw, Download, FileText, Zap } from 'lucide-react';
import api from '../api/client';
import { Panel, Button, EmptyState, SeverityBadge, PriorityBadge } from '../components/ui';
import StatCard from '../components/StatCard';

const HORIZONS = [
  { value: '24h', label: 'Next 24 hours' },
  { value: '7d', label: 'Next 7 days' },
  { value: '30d', label: 'Next 30 days' },
];
const MODELS = [
  { value: 'prophet', label: 'Prophet' },
  { value: 'arima', label: 'ARIMA' },
  { value: 'regression', label: 'Regression (baseline)' },
];
const SEVERITY_COLOR = {
  high: 'var(--accent-danger)',
  medium: 'var(--accent-amber)',
  low: 'var(--text-secondary)',
};

function fmtTick(value) {
  const d = new Date(value);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`;
}

function toMs(ts) {
  return new Date(ts).getTime();
}

export default function DeviceDetail() {
  const { deviceId } = useParams();
  const [history, setHistory] = useState([]);
  const [deviceName, setDeviceName] = useState('');
  const [forecast, setForecast] = useState(null);
  const [accuracyHistory, setAccuracyHistory] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [peaks, setPeaks] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [horizon, setHorizon] = useState('7d');
  const [modelType, setModelType] = useState('prophet');
  const [genLoading, setGenLoading] = useState(false);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [recLoading, setRecLoading] = useState(false);
  const [retrainLoading, setRetrainLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(null);

  const loadAll = useCallback(async () => {
    const [h, acc, an, pk, recs] = await Promise.all([
      api.get(`/api/analytics/device/${deviceId}/history?days=30`),
      api.get(`/api/analytics/device/${deviceId}/forecast-accuracy`),
      api.get(`/api/anomalies/device/${deviceId}`),
      api.get(`/api/anomalies/peaks/${deviceId}`),
      api.get(`/api/recommendations/device/${deviceId}`),
    ]);
    setHistory(h.data.readings);
    setDeviceName(h.data.device_name);
    setAccuracyHistory(acc.data);
    setAnomalies(an.data);
    setPeaks(pk.data);
    setRecommendations(recs.data);
    try {
      const latest = await api.get(`/api/forecasts/latest/${deviceId}`);
      setForecast(latest.data);
    } catch {
      setForecast(null);
    }
  }, [deviceId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleGenerateForecast = async () => {
    setGenLoading(true);
    try {
      await api.post('/api/forecasts/generate', { device_id: Number(deviceId), horizon, model_type: modelType });
      await new Promise((r) => setTimeout(r, 6000)); // background job needs a moment
      await loadAll();
    } finally {
      setGenLoading(false);
    }
  };

  const handleDetectAnomalies = async (method) => {
    setAnomalyLoading(true);
    try {
      await api.post(`/api/anomalies/detect/${deviceId}?method=${method}`);
      await loadAll();
    } finally {
      setAnomalyLoading(false);
    }
  };

  const handleGenerateRecommendations = async () => {
    setRecLoading(true);
    try {
      await api.post(`/api/recommendations/generate/${deviceId}`);
      await loadAll();
    } finally {
      setRecLoading(false);
    }
  };

  const handleRetrainNow = async () => {
    setRetrainLoading(true);
    try {
      await api.post('/api/forecasts/retrain-all');
      await new Promise((r) => setTimeout(r, 6000));
      await loadAll();
    } finally {
      setRetrainLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExportLoading(format);
    try {
      const res = await api.get(`/api/reports/device/${deviceId}/${format}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      const ext = format === 'csv' ? 'csv' : 'pdf';
      a.download = `${(deviceName || 'device').replace(/\s+/g, '_')}_report.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setExportLoading(null);
    }
  };

  // Numeric-time chart data so the anomaly scatter overlay lines up exactly with
  // the actual/predicted series regardless of minor timestamp-string formatting differences.
  const chartData = [
    ...history.map((h) => ({ x: toMs(h.timestamp), actual: h.energy_kwh })),
    ...(forecast?.predictions || []).map((p) => ({ x: toMs(p.timestamp), predicted: p.predicted, upper: p.upper, lower: p.lower })),
  ].sort((a, b) => a.x - b.x);

  const anomalyScatterData = anomalies.map((a) => ({ x: toMs(a.timestamp), y: a.energy_kwh, severity: a.severity }));

  const anomalyPoints = anomalies.slice(0, 200).map((a) => ({ timestamp: a.timestamp, value: a.energy_kwh, severity: a.severity }));

  // Model comparison: latest run per model type, for the accuracy bar chart
  const latestPerModel = {};
  for (const f of accuracyHistory) {
    if (!latestPerModel[f.model_type] || new Date(f.generated_at) > new Date(latestPerModel[f.model_type].generated_at)) {
      latestPerModel[f.model_type] = f;
    }
  }
  const comparisonData = Object.values(latestPerModel).map((f) => ({
    model: f.model_type,
    MAE: f.mae != null ? Number(f.mae.toFixed(2)) : 0,
    RMSE: f.rmse != null ? Number(f.rmse.toFixed(2)) : 0,
    MAPE: f.mape != null ? Number(f.mape.toFixed(1)) : 0,
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">{deviceName || `Device #${deviceId}`}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Consumption history, forecasts, and anomaly detection</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => handleExport('csv')} disabled={exportLoading === 'csv'}>
            <Download size={14} /> {exportLoading === 'csv' ? 'Exporting…' : 'CSV'}
          </Button>
          <Button variant="secondary" onClick={() => handleExport('pdf')} disabled={exportLoading === 'pdf'}>
            <FileText size={14} /> {exportLoading === 'pdf' ? 'Exporting…' : 'PDF report'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="Peak threshold" value={peaks?.threshold_kwh ?? '—'} unit="kWh" accent="amber" icon={TrendingUp} />
        <StatCard
          label="Peak hours"
          value={peaks?.peak_hours?.length ? `${peaks.peak_hours[0]}–${peaks.peak_hours[peaks.peak_hours.length - 1]}` : '—'}
          unit="h"
          accent="blue"
        />
        <StatCard label="Anomalies logged" value={anomalies.length} accent="danger" icon={AlertTriangle} />
        <StatCard
          label="Latest MAPE"
          value={forecast?.mape != null ? forecast.mape.toFixed(1) : '—'}
          unit="%"
          accent="teal"
        />
      </div>

      {peaks?.alerts?.length > 0 && (
        <div className="mb-6 flex items-start gap-2 px-4 py-3 rounded-[var(--radius-sm)] bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/30">
          <AlertTriangle size={15} className="text-[var(--accent-amber)] mt-0.5 shrink-0" />
          <div className="text-sm text-[var(--text-primary)]">{peaks.alerts.join(' · ')}</div>
        </div>
      )}

      <Panel
        title="Historical vs. predicted consumption"
        action={
          <div className="flex items-center gap-2">
            <select value={modelType} onChange={(e) => setModelType(e.target.value)} className="bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-2 py-1 text-xs">
              {MODELS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
            <select value={horizon} onChange={(e) => setHorizon(e.target.value)} className="bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-2 py-1 text-xs">
              {HORIZONS.map((h) => <option key={h.value} value={h.value}>{h.label}</option>)}
            </select>
            <Button onClick={handleGenerateForecast} disabled={genLoading} variant="secondary">
              <RefreshCw size={13} className={genLoading ? 'animate-spin' : ''} /> {genLoading ? 'Generating…' : 'Generate forecast'}
            </Button>
          </div>
        }
        className="mb-6"
      >
        {chartData.length === 0 ? (
          <EmptyState title="No data yet" description="Upload a dataset or wait for readings to populate history." />
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <ComposedChart data={chartData}>
              <defs>
                <linearGradient id="predictedFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-teal)" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="var(--accent-teal)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="x"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={fmtTick}
                stroke="var(--text-muted)"
                tick={{ fontSize: 10 }}
                minTickGap={40}
              />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} unit=" kWh" />
              <ZAxis range={[50, 50]} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--border-bright)', borderRadius: 6, fontSize: 12 }}
                labelFormatter={fmtTick}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {forecast?.predictions?.some((p) => p.upper != null) && (
                <Area type="monotone" dataKey="upper" stroke="none" fill="url(#predictedFill)" name="Confidence band" />
              )}
              <Line type="monotone" dataKey="actual" stroke="var(--accent-blue)" strokeWidth={1.5} dot={false} name="Actual" isAnimationActive={false} />
              <Line type="monotone" dataKey="predicted" stroke="var(--accent-teal)" strokeWidth={2} dot={false} strokeDasharray="4 2" name="Forecast" isAnimationActive={false} />
              <Scatter
                name="Anomaly"
                data={anomalyScatterData}
                dataKey="y"
                fill="var(--accent-danger)"
                shape={(props) => {
                  const { cx, cy, payload } = props;
                  return (
                    <circle
                      cx={cx}
                      cy={cy}
                      r={5}
                      fill={SEVERITY_COLOR[payload.severity] || 'var(--accent-danger)'}
                      stroke="var(--bg)"
                      strokeWidth={1.5}
                    />
                  );
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
        {forecast && (
          <div className="flex gap-6 mt-3 text-xs text-[var(--text-secondary)] font-mono-data">
            <span>MAE: {forecast.mae?.toFixed(2)}</span>
            <span>RMSE: {forecast.rmse?.toFixed(2)}</span>
            <span>MAPE: {forecast.mape?.toFixed(1)}%</span>
            <span className="text-[var(--text-muted)]">Model: {forecast.model_type}</span>
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-2 gap-6">
        <Panel
          title="Anomaly detection"
          action={
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => handleDetectAnomalies('z_score')} disabled={anomalyLoading}>Z-score</Button>
              <Button variant="secondary" onClick={() => handleDetectAnomalies('isolation_forest')} disabled={anomalyLoading}>Isolation Forest</Button>
            </div>
          }
        >
          {anomalyPoints.length === 0 ? (
            <EmptyState title="No anomalies detected" description="Run a detection method to scan readings — they'll also appear as markers on the chart above." />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {anomalyPoints.slice(0, 15).map((a, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)] text-sm">
                  <div>
                    <div className="font-mono-data text-xs text-[var(--text-muted)]">{fmtTick(a.timestamp)}</div>
                    <div className="font-mono-data">{a.value.toFixed(1)} kWh</div>
                  </div>
                  <SeverityBadge severity={a.severity} />
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title="Optimization recommendations"
          action={
            <Button variant="secondary" onClick={handleGenerateRecommendations} disabled={recLoading}>
              {recLoading ? 'Generating…' : 'Generate'}
            </Button>
          }
        >
          {recommendations.length === 0 ? (
            <EmptyState title="No recommendations yet" description="Generate recommendations based on current patterns." />
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {recommendations.map((r) => (
                <div key={r.id} className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)]">
                  <Lightbulb size={15} className="text-[var(--accent-teal)] mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm">{r.message}</p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <PriorityBadge priority={r.priority} />
                      {r.estimated_savings_kwh > 0 && (
                        <span className="text-xs text-[var(--accent-teal)] font-mono-data">~{r.estimated_savings_kwh} kWh saved</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Model comparison"
        action={
          <Button variant="secondary" onClick={handleRetrainNow} disabled={retrainLoading}>
            <Zap size={13} className={retrainLoading ? 'animate-pulse' : ''} /> {retrainLoading ? 'Retraining…' : 'Retrain all now'}
          </Button>
        }
        className="mt-6"
      >
        {comparisonData.length === 0 ? (
          <EmptyState title="No forecasts to compare yet" description="Generate a forecast with at least two different models to compare accuracy." />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={comparisonData}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="model" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--border-bright)', borderRadius: 6, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="MAE" fill="var(--accent-blue)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="RMSE" fill="var(--accent-amber)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="MAPE" fill="var(--accent-teal)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}

        {accuracyHistory.length > 0 && (
          <table className="w-full text-sm mt-6">
            <thead>
              <tr className="text-left text-xs text-[var(--text-muted)] uppercase border-b border-[var(--border)]">
                <th className="pb-2 font-medium">Generated</th>
                <th className="pb-2 font-medium">Model</th>
                <th className="pb-2 font-medium">Horizon</th>
                <th className="pb-2 font-medium">MAE</th>
                <th className="pb-2 font-medium">RMSE</th>
                <th className="pb-2 font-medium">MAPE</th>
              </tr>
            </thead>
            <tbody>
              {accuracyHistory.map((f) => (
                <tr key={f.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="py-2 font-mono-data text-xs text-[var(--text-secondary)]">{fmtTick(f.generated_at)}</td>
                  <td className="py-2 capitalize">{f.model_type}</td>
                  <td className="py-2 font-mono-data">{f.horizon}</td>
                  <td className="py-2 font-mono-data">{f.mae?.toFixed(2) ?? '—'}</td>
                  <td className="py-2 font-mono-data">{f.rmse?.toFixed(2) ?? '—'}</td>
                  <td className="py-2 font-mono-data">{f.mape != null ? `${f.mape.toFixed(1)}%` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
