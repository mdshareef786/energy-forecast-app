import { useEffect, useRef, useState, useCallback } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Activity, Radio } from 'lucide-react';
import api from '../api/client';
import { Panel, EmptyState } from '../components/ui';
import StatCard from '../components/StatCard';

const POLL_INTERVAL_MS = 10000;

function fmtTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function LiveMonitor() {
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [liveSeries, setLiveSeries] = useState([]);
  const [lastReading, setLastReading] = useState(null);
  const [connected, setConnected] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    (async () => {
      const buildings = await api.get('/api/buildings');
      const allDevices = [];
      for (const b of buildings.data) {
        const devs = await api.get(`/api/devices?building_id=${b.id}`);
        allDevices.push(...devs.data.map((d) => ({ ...d, buildingName: b.name })));
      }
      setDevices(allDevices);
      if (allDevices.length > 0) setSelectedDeviceId(allDevices[0].id);
    })();
  }, []);

  const poll = useCallback(async () => {
    if (!selectedDeviceId) return;
    try {
      const res = await api.get(`/api/analytics/device/${selectedDeviceId}/history?days=1`);
      setConnected(true);
      const readings = res.data.readings;
      if (readings.length > 0) {
        const latest = readings[readings.length - 1];
        setLastReading(latest);
        setLiveSeries((prev) => {
          const next = [...prev, { time: latest.timestamp, value: latest.energy_kwh }];
          // keep a rolling window so the chart doesn't grow unbounded
          return next.slice(-60);
        });
      }
    } catch {
      setConnected(false);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    setLiveSeries([]);
    setLastReading(null);
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(pollRef.current);
  }, [poll]);

  const selectedDevice = devices.find((d) => d.id === selectedDeviceId);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            Live Monitor
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${connected ? 'bg-[var(--accent-teal)]' : 'bg-[var(--accent-danger)]'} opacity-75`} />
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${connected ? 'bg-[var(--accent-teal)]' : 'bg-[var(--accent-danger)]'}`} />
            </span>
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Polling the latest reading every {POLL_INTERVAL_MS / 1000}s — a lightweight real-time view without needing hardware push access.
          </p>
        </div>
        <select
          value={selectedDeviceId || ''}
          onChange={(e) => setSelectedDeviceId(Number(e.target.value))}
          className="bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm"
        >
          {devices.map((d) => (
            <option key={d.id} value={d.id}>{d.buildingName} — {d.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard
          label="Current reading"
          value={lastReading ? lastReading.energy_kwh.toFixed(1) : '—'}
          unit="kWh"
          accent="amber"
          icon={Activity}
        />
        <StatCard
          label="Temperature"
          value={lastReading?.temperature_c != null ? lastReading.temperature_c.toFixed(1) : '—'}
          unit="°C"
          accent="blue"
        />
        <StatCard
          label="Connection"
          value={connected ? 'Live' : 'Idle'}
          accent={connected ? 'teal' : 'danger'}
          icon={Radio}
          sub={lastReading ? `Last update ${fmtTime(lastReading.timestamp)}` : undefined}
        />
      </div>

      <Panel title={selectedDevice ? `${selectedDevice.name} — rolling window` : 'Live consumption'}>
        {liveSeries.length === 0 ? (
          <EmptyState title="Waiting for data…" description="This device may not have recent readings yet." />
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={liveSeries}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="time" tickFormatter={fmtTime} stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} unit=" kWh" />
              <Tooltip
                contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--border-bright)', borderRadius: 6, fontSize: 12 }}
                labelFormatter={fmtTime}
              />
              <Line type="monotone" dataKey="value" stroke="var(--accent-amber)" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Panel>
    </div>
  );
}
