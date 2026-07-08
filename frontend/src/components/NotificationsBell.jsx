import { useEffect, useRef, useState } from 'react';
import { Bell, AlertTriangle, TrendingUp, RefreshCw, Info } from 'lucide-react';
import api from '../api/client';

const SOURCE_ICON = {
  anomaly: AlertTriangle,
  forecast_threshold: TrendingUp,
  retraining: RefreshCw,
  peak_prediction: TrendingUp,
};

const SEVERITY_COLOR = {
  critical: 'var(--accent-danger)',
  warning: 'var(--accent-amber)',
  info: 'var(--accent-blue)',
};

function timeAgo(ts) {
  const diffMs = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const ref = useRef(null);

  const load = async () => {
    try {
      const [alertsRes, countRes] = await Promise.all([
        api.get('/api/alerts?limit=20'),
        api.get('/api/alerts/unread-count'),
      ]);
      setAlerts(alertsRes.data);
      setUnreadCount(countRes.data.count);
    } catch {
      // silently ignore — notification bell shouldn't break the rest of the UI
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAllRead = async () => {
    await api.post('/api/alerts/read-all');
    load();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative w-9 h-9 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-raised)] flex items-center justify-center hover:border-[var(--accent-amber)]/50 transition-colors"
      >
        <Bell size={15} className="text-[var(--text-secondary)]" />
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-[var(--accent-danger)] text-white text-[10px] font-mono-data flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] shadow-xl z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
            <span className="text-sm font-semibold">Alerts</span>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-[var(--accent-amber)] hover:underline">
                Mark all read
              </button>
            )}
          </div>
          {alerts.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-[var(--text-secondary)]">No alerts yet</div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {alerts.map((a) => {
                const Icon = SOURCE_ICON[a.source] || Info;
                return (
                  <div key={a.id} className={`flex items-start gap-2.5 px-4 py-3 ${a.is_read ? 'opacity-60' : ''}`}>
                    <Icon size={14} style={{ color: SEVERITY_COLOR[a.severity] }} className="mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[var(--text-primary)] leading-snug">{a.message}</p>
                      <p className="text-[10px] text-[var(--text-muted)] mt-1 font-mono-data">{timeAgo(a.created_at)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
