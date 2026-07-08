import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, ArrowRight, Plus } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Panel, Button, EmptyState } from '../components/ui';

export default function Buildings() {
  const { user } = useAuth();
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', location: '' });

  const load = async () => {
    setLoading(true);
    const res = await api.get('/api/buildings');
    setBuildings(res.data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.post('/api/buildings', form);
    setForm({ name: '', location: '' });
    setShowCreate(false);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Buildings</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Manage properties and their tracked devices.</p>
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
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Location</label>
              <input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
              />
            </div>
            <Button type="submit">Create</Button>
          </form>
        </Panel>
      )}

      <Panel>
        {loading ? (
          <p className="text-sm text-[var(--text-secondary)]">Loading…</p>
        ) : buildings.length === 0 ? (
          <EmptyState title="No buildings yet" description="Create one to start tracking energy consumption." />
        ) : (
          <div className="divide-y divide-[var(--border)] -m-5">
            {buildings.map((b) => (
              <Link key={b.id} to={`/buildings/${b.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-[var(--surface-raised)] transition-colors group">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-[var(--radius-sm)] bg-[var(--surface-raised)] border border-[var(--border)] flex items-center justify-center">
                    <Building2 size={16} className="text-[var(--text-secondary)]" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">{b.name}</div>
                    <div className="text-xs text-[var(--text-muted)]">{b.location || 'No location set'}</div>
                  </div>
                </div>
                <ArrowRight size={16} className="text-[var(--text-muted)] group-hover:text-[var(--accent-amber)] transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
