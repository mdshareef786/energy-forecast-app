export function Panel({ title, action, children, className = '' }) {
  return (
    <div className={`rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function SeverityBadge({ severity }) {
  const styles = {
    high: { bg: 'rgba(229,72,77,0.12)', color: 'var(--accent-danger)', border: 'rgba(229,72,77,0.3)' },
    medium: { bg: 'rgba(242,183,5,0.12)', color: 'var(--accent-amber)', border: 'rgba(242,183,5,0.3)' },
    low: { bg: 'rgba(147,163,168,0.12)', color: 'var(--text-secondary)', border: 'rgba(147,163,168,0.3)' },
  }[severity] || { bg: 'rgba(147,163,168,0.12)', color: 'var(--text-secondary)', border: 'rgba(147,163,168,0.3)' };

  return (
    <span
      className="px-2 py-0.5 rounded-full text-[11px] font-mono-data uppercase tracking-wide border"
      style={{ background: styles.bg, color: styles.color, borderColor: styles.border }}
    >
      {severity}
    </span>
  );
}

export function PriorityBadge({ priority }) {
  return <SeverityBadge severity={priority} />;
}

export function Button({ children, onClick, variant = 'primary', disabled, type = 'button', className = '' }) {
  const base = 'inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-sm)] text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-[var(--accent-amber)] text-[#1a1400] hover:brightness-110',
    secondary: 'bg-[var(--surface-raised)] text-[var(--text-primary)] border border-[var(--border-bright)] hover:border-[var(--accent-amber)]/50',
    ghost: 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="text-center py-12">
      <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
      {description && <p className="text-sm text-[var(--text-secondary)] mt-1">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
