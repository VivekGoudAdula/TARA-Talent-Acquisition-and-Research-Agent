import React from 'react';
export default function SectionPanel({ title, subtitle, actions, children, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>{title}</h3>}
            {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>{subtitle}</p>}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
}

export function FieldRow({ label, value, mono = false }) {
  return (
    <div
      className="flex items-start justify-between py-2 last:border-0"
      style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
    >
      <span className="text-xs font-medium w-40 shrink-0" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
      <span
        className={`text-sm text-right ${mono ? 'font-mono' : ''}`}
        style={{ color: 'var(--color-text-primary)' }}
      >
        {value ?? '—'}
      </span>
    </div>
  );
}

export function ScoreBar({ label, value, max = 100, color = 'primary' }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const colorClass = {
    primary: 'bg-primary-500',
    green: 'bg-success-500',
    amber: 'bg-warning-500',
    red: 'bg-danger-500',
  }[color] || 'bg-primary-500';

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs w-36 shrink-0" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-surface-elevated)' }}>
        <div className={`h-full rounded-full transition-all duration-500 ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium w-10 text-right" style={{ color: 'var(--color-text-secondary)' }}>{value}</span>
    </div>
  );
}
