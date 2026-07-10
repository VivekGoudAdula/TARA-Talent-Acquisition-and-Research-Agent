import React from 'react';
export default function SectionPanel({ title, subtitle, actions, children, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h3 className="text-sm font-semibold text-neutral-800">{title}</h3>}
            {subtitle && <p className="text-xs text-neutral-500 mt-0.5">{subtitle}</p>}
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
    <div className="flex items-start justify-between py-2 border-b border-neutral-50 last:border-0">
      <span className="text-xs font-medium text-neutral-500 w-40 shrink-0">{label}</span>
      <span className={`text-sm text-neutral-800 text-right ${mono ? 'font-mono' : ''}`}>{value ?? '—'}</span>
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
      <span className="text-xs text-neutral-500 w-36 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-neutral-700 w-10 text-right">{value}</span>
    </div>
  );
}
