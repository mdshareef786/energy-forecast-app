import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, Plus, ArrowRight, Zap, AlertTriangle, Lightbulb } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import StatCard from '../components/StatCard';
import { Panel, Button, EmptyState } from '../components/ui';

export default function Dashboard() {
  const { user } = useAuth();
  const [buildings, setBuildings] = useState([]);
  const [summaries, setSummaries] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', location: '' });

  const loadData = async () => {
    setLoading(true);
    const res = await api.get('/api/buildings');
    setBuildings(res.data);
    const summaryEntries = await Promise.all(
      res.data.map(async (b) => {
        try {
          const s = await api.get(`/api/analytics/building/${b.id}/summary`);
          return [b.id, s.data];
        } catch {
          return [b.id, null];
        }
      })
    );
    setSummaries(Object.fromEntries(summaryEntries));
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.post('/api/buildings', form);
    setForm({ name: '', location: '' });
    setShowCreate(false);
    loadData();
  };

  const totals = Object.values(summaries).reduce(
    (acc, s) => {
      if (!s) return acc;
      acc.energy += s.total_energy_kwh || 0;
      acc.anomalies += s.anomaly_count || 0;
      acc.recommendations += s.recommendation_count || 0;
      acc.devices += s.device_count || 0;
      return acc;
    },
    { energy: 0, anomalies: 0, recommendations: 0, devices: 0 }
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Overview</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Fleet-wide energy consumption at a glance.</p>
        </div>
        {user?.role === 'admin' && (
          <Button onClick={() => setShowCreate((s) => !s)}>
            <Plus size={15} /> New building
          </Button>
        )}
      </div>

      {showCreate && (
        <Panel className="mb-6">
          <form onSubmit={handleCreate} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Building name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="e.g. HQ Tower"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Location</label>
              <input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="e.g. Hyderabad"
              />
            </div>
            <Button type="submit">Create</Button>
          </form>
        </Panel>
      )}

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total consumption" value={totals.energy.toFixed(0)} unit="kWh" accent="amber" icon={Zap} />
        <StatCard label="Buildings" value={buildings.length} accent="blue" icon={Building2} />
        <StatCard label="Devices tracked" value={totals.devices} accent="teal" icon={Lightbulb} />
        <StatCard label="Open anomalies" value={totals.anomalies} accent="danger" icon={AlertTriangle} />
      </div>

      <Panel title="Buildings">
        {loading ? (
          <p className="text-sm text-[var(--text-secondary)]">Loading…</p>
        ) : buildings.length === 0 ? (
          <EmptyState
            title="No buildings yet"
            description="Add your first building to start tracking devices and energy consumption."
          />
        ) : (
          <div className="divide-y divide-[var(--border)] -m-5">
            {buildings.map((b) => {
              const s = summaries[b.id];
              return (
                <Link
                  key={b.id}
                  to={`/buildings/${b.id}`}
                  className="flex items-center justify-between px-5 py-4 hover:bg-[var(--surface-raised)] transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)] flex items-center justify-center">
                      <Building2 size={16} className="text-[var(--text-secondary)]" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{b.name}</div>
                      <div className="text-xs text-[var(--text-muted)]">{b.location || 'No location set'}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-right">
                    <div>
                      <div className="font-mono-data text-sm text-[var(--accent-amber)]">
                        {s ? s.total_energy_kwh.toFixed(0) : '—'}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] uppercase">kWh</div>
                    </div>
                    <div>
                      <div className="font-mono-data text-sm">{s ? s.device_count : '—'}</div>
                      <div className="text-[10px] text-[var(--text-muted)] uppercase">devices</div>
                    </div>
                    <div>
                      <div className={`font-mono-data text-sm ${s?.anomaly_count ? 'text-[var(--accent-danger)]' : ''}`}>
                        {s ? s.anomaly_count : '—'}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] uppercase">anomalies</div>
                    </div>
                    <ArrowRight size={16} className="text-[var(--text-muted)] group-hover:text-[var(--accent-amber)] transition-colors" />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
