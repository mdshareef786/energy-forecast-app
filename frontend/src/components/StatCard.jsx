export default function StatCard({ label, value, unit, accent = 'amber', icon: Icon, sub }) {
  const accentColor = {
    amber: 'var(--accent-amber)',
    teal: 'var(--accent-teal)',
    danger: 'var(--accent-danger)',
    blue: 'var(--accent-blue)',
  }[accent];

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-5 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 w-full h-[2px]"
        style={{ background: accentColor, opacity: 0.6 }}
      />
      <div className="flex items-start justify-between">
        <div className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-medium">{label}</div>
        {Icon && <Icon size={14} style={{ color: accentColor }} />}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="font-mono-data text-2xl font-semibold" style={{ color: accentColor }}>
          {value}
        </span>
        {unit && <span className="text-xs text-[var(--text-secondary)] font-mono-data">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-[var(--text-secondary)]">{sub}</div>}
    </div>
  );
}
