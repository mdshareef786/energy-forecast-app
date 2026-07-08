import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui';

export default function Register() {
  const { register, loading, error } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'analyst' });

  const handleChange = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await register(form);
    if (ok) navigate('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-9 h-9 rounded-[var(--radius-sm)] bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/40 flex items-center justify-center">
            <Zap size={18} className="text-[var(--accent-amber)]" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-display font-semibold">GridSense</div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono-data tracking-wide">ENERGY AI</div>
          </div>
        </div>

        <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-6">
          <h1 className="text-lg font-semibold mb-1">Create account</h1>
          <p className="text-sm text-[var(--text-secondary)] mb-5">Set up access to the console.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Full name</label>
              <input
                required
                value={form.full_name}
                onChange={handleChange('full_name')}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="Jane Doe"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Email</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={handleChange('email')}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={form.password}
                onChange={handleChange('password')}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-secondary)] mb-1.5">Role</label>
              <select
                value={form.role}
                onChange={handleChange('role')}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-bright)] rounded-[var(--radius-sm)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent-amber)]"
              >
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>

            {error && (
              <p className="text-xs text-[var(--accent-danger)] bg-[var(--accent-danger)]/10 border border-[var(--accent-danger)]/30 rounded-[var(--radius-sm)] px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" disabled={loading} className="w-full justify-center">
              {loading ? 'Creating account…' : 'Create account'}
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-[var(--text-secondary)] mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-[var(--accent-amber)] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
