import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Plus, ArrowRight, Lightbulb, PlayCircle } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import StatCard from '../components/StatCard';
import { Panel, Button, EmptyState, PriorityBadge } from '../components/ui';

const SCENARIOS = [
  { value: 'peak_reduction', label: 'Peak-hour reduction', param: 'peak_reduction_percent', paramLabel: 'Reduction %', defaultVal: 20 },
  { value: 'occupancy', label: 'Occupancy change', param: 'occupancy_change_percent', paramLabel: 'Occupancy change %', defaultVal: -20 },
  { value: 'temperature', label: 'Temperature change', param: 'temperature_change_c', paramLabel: 'Δ Temperature (°C)', defaultVal: 2 },
  { value: 'shutdown', label: 'Scheduled shutdown', param: 'hours_shutdown_per_day', paramLabel: 'Hours/day shut down', defaultVal: 4 },
];

export default function BuildingDetail() {
  const { buildingId } = useParams();
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [simulations, setSimulations] = useState([]);
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [deviceForm, setDeviceForm] = useState({ name: '', device_type: '', rated_capacity_kw: '' });
  const [scenarioType, setScenarioType] = useState('peak_reduction');
  const [scenarioValue, setScenarioValue] = useState(20);
  const [simLoading, setSimLoading] = useState(false);

  const load = async () => {
    const [s, r, sims] = await Promise.all([
      api.get(`/api/analytics/building/${buildingId}/summary`),
      api.get(`/api/recommendations/building/${buildingId}`),
      api.get(`/api/simulations/building/${buildingId}`),
    ]);
    setSummary(s.data);
    setRecommendations(r.data);
    setSimulations(sims.data);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildingId]);

  const handleAddDevice = async (e) => {
    e.preventDefault();
    await api.post('/api/devices', {
      ...deviceForm,
      building_id: Number(buildingId),
      rated_capacity_kw: deviceForm.rated_capacity_kw ? Number(deviceForm.rated_capacity_kw) : null,
    });
    setDeviceForm({ name: '', device_type: '', rated_capacity_kw: '' });
    setShowAddDevice(false);
    load();
  };

  const handleSimulate = async (e) => {
    e.preventDefault();
    setSimLoading(true);
    const scenario = SCENARIOS.find((s) => s.value === scenarioType);
    try {
      await api.post('/api/simulations/run', {
        building_id: Number(buildingId),
        name: `${scenario.label} (${scenarioValue})`,
        scenario_type: scenarioType,
        parameters: { [scenario.param]: Number(scenarioValue) },
      });
      load();
    } finally {
      setSimLoading(false);
    }
  };

  if (!summary) return <p className="text-sm text-[var(--text-secondary)]">Loading…</p>;

  const currentScenario = SCENARIOS.find((s) => s.value === scenarioType);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">{summary.building_name}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">{summary.device_count} devices tracked</p>
        </div>
        {user?.role === 'admin' && (
          <Button onClick={() => setShowAddDevice((s) => !s)}>
            <Plus size={15} /> Add device
          </Button>
        )}
      </div>

      {showAddDevice && (
        <Panel className="mb-6">
          <form onSubmit={handleAddDevice} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Device name</label>
              <input
                required
                value={deviceForm.name}
                onChange={(e) => setDeviceForm({ ...deviceForm, name: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="e.g. HVAC-2"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Type</label>
              <input
                value={deviceForm.device_type}
                onChange={(e) => setDeviceForm({ ...deviceForm, device_type: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="e.g. HVAC, lighting"
              />
            </div>
            <div className="w-40">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Capacity (kW)</label>
              <input
                type="number"
                value={deviceForm.rated_capacity_kw}
                onChange={(e) => setDeviceForm({ ...deviceForm, rated_capacity_kw: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="50"
              />
            </div>
            <Button type="submit">Add</Button>
          </form>
        </Panel>
      )}

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Total consumption" value={summary.total_energy_kwh.toFixed(0)} unit="kWh" accent="amber" />
        <StatCard label="Anomalies detected" value={summary.anomaly_count} accent="danger" />
        <StatCard label="Recommendations" value={summary.recommendation_count} accent="teal" />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <Panel title="Devices">
            {summary.devices.length === 0 ? (
              <EmptyState title="No devices yet" description="Add a device to start collecting energy readings." />
            ) : (
              <div className="divide-y divide-[var(--border)] -m-5">
                {summary.devices.map((d) => (
                  <Link
                    key={d.id}
                    to={`/devices/${d.id}`}
                    className="flex items-center justify-between px-5 py-3.5 hover:bg-[var(--surface-raised)] transition-colors group"
                  >
                    <div>
                      <div className="text-sm font-medium">{d.name}</div>
                      <div className="text-xs text-[var(--text-muted)]">{d.device_type || 'Unclassified'}</div>
                    </div>
                    <ArrowRight size={16} className="text-[var(--text-muted)] group-hover:text-[var(--accent-amber)] transition-colors" />
                  </Link>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Optimization recommendations">
            {recommendations.length === 0 ? (
              <EmptyState
                title="No recommendations yet"
                description="Generate recommendations from a device's detail page once it has readings."
              />
            ) : (
              <div className="space-y-3">
                {recommendations.map((r) => (
                  <div key={r.id} className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)]">
                    <Lightbulb size={16} className="text-[var(--accent-teal)] mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm">{r.message}</p>
                      <div className="flex items-center gap-3 mt-1.5">
                        <PriorityBadge priority={r.priority} />
                        {r.estimated_savings_kwh > 0 && (
                          <span className="text-xs text-[var(--accent-teal)] font-mono-data">
                            ~{r.estimated_savings_kwh} kWh saved
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Scenario simulation">
            <form onSubmit={handleSimulate} className="space-y-3">
              <div>
                <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Scenario</label>
                <select
                  value={scenarioType}
                  onChange={(e) => {
                    setScenarioType(e.target.value);
                    setScenarioValue(SCENARIOS.find((s) => s.value === e.target.value).defaultVal);
                  }}
                  className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                >
                  {SCENARIOS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-[var(--text-secondary)] mb-1.5">{currentScenario.paramLabel}</label>
                <input
                  type="number"
                  value={scenarioValue}
                  onChange={(e) => setScenarioValue(e.target.value)}
                  className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                />
              </div>
              <Button type="submit" disabled={simLoading} className="w-full justify-center">
                <PlayCircle size={15} /> {simLoading ? 'Running…' : 'Run simulation'}
              </Button>
            </form>
          </Panel>

          <Panel title="Recent simulations">
            {simulations.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">No simulations run yet.</p>
            ) : (
              <div className="space-y-3">
                {simulations.slice(0, 6).map((s) => (
                  <div key={s.id} className="p-3 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)]">
                    <div className="text-sm font-medium mb-1">{s.name}</div>
                    <div className="flex justify-between text-xs">
                      <span className="text-[var(--text-secondary)]">Baseline: <span className="font-mono-data">{s.baseline_kwh}</span> kWh</span>
                      <span className="text-[var(--accent-teal)]">
                        −{s.savings_percent}% ({s.savings_kwh} kWh)
                      </span>
                    </div>
                    {s.estimated_cost_impact != null && (
                      <div className="text-xs text-[var(--text-muted)] mt-1">Est. cost impact: ${s.estimated_cost_impact}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
