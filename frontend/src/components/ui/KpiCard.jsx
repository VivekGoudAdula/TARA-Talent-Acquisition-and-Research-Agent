import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const ACCENT_BORDER = {
  blue: 'border-l-primary-500',
  green: 'border-l-success-500',
  amber: 'border-l-warning-500',
  red: 'border-l-danger-500',
  neutral: 'border-l-neutral-400 dark:border-l-slate-500',
};

export default function KpiCard({ label, value, sub, trend, trendDir, icon: Icon, color = 'blue', onClick }) {
  const colorMap = {
    blue: 'bg-primary-50 text-primary-500 dark:bg-primary-500/15 dark:text-primary-400',
    green: 'bg-success-50 text-success-500 dark:bg-success-500/15 dark:text-success-400',
    amber: 'bg-warning-50 text-warning-500 dark:bg-warning-500/15 dark:text-warning-500',
    red: 'bg-danger-50 text-danger-500 dark:bg-danger-500/15 dark:text-danger-400',
    neutral: 'bg-neutral-100 text-neutral-500 dark:bg-slate-700/50 dark:text-slate-400',
  };

  return (
    <div
      className={`card p-5 flex flex-col gap-3 border-l-4 ${ACCENT_BORDER[color] || ACCENT_BORDER.blue} ${
        onClick ? 'cursor-pointer hover:shadow-panel transition-shadow' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <span className="metric-label">{label}</span>
        {Icon && (
          <div className={`p-2 rounded-lg ${colorMap[color]}`}>
            <Icon size={16} />
          </div>
        )}
      </div>
      <div>
        <div className="metric-value">{value ?? '—'}</div>
        {sub && <div className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{sub}</div>}
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs font-medium ${trendDir === 'up' ? 'text-success-500' : 'text-danger-500'}`}>
          {trendDir === 'up' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {trend}
        </div>
      )}
    </div>
  );
}
