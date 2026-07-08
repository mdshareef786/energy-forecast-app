import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutGrid, Building2, UploadCloud, LogOut, Zap, Radio } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import NotificationsBell from './NotificationsBell';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/buildings', label: 'Buildings', icon: Building2 },
  { to: '/live', label: 'Live Monitor', icon: Radio },
  { to: '/datasets', label: 'Datasets', icon: UploadCloud },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] flex flex-col">
        <div className="h-16 flex items-center justify-between gap-2 px-5 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-[var(--radius-sm)] bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/40 flex items-center justify-center">
              <Zap size={16} className="text-[var(--accent-amber)]" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-display font-semibold text-sm leading-tight">GridSense</div>
              <div className="text-[10px] text-[var(--text-muted)] font-mono-data tracking-wide">ENERGY AI</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)] text-sm transition-colors ${
                  isActive
                    ? 'bg-[var(--surface-raised)] text-[var(--text-primary)] border-l-2 border-[var(--accent-amber)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--surface-raised)] hover:text-[var(--text-primary)] border-l-2 border-transparent'
                }`
              }
            >
              <Icon size={16} strokeWidth={2} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-[var(--border)]">
          <div className="px-3 py-2 mb-1">
            <div className="text-sm font-medium truncate">{user?.full_name}</div>
            <div className="text-[11px] text-[var(--text-muted)] font-mono-data uppercase tracking-wide">{user?.role}</div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)] text-sm text-[var(--text-secondary)] hover:bg-[var(--accent-danger)]/10 hover:text-[var(--accent-danger)] transition-colors"
          >
            <LogOut size={16} strokeWidth={2} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 shrink-0 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-end px-6">
          <NotificationsBell />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
