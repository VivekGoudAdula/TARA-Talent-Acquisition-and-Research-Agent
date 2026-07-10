import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export default function KpiCard({ label, value, sub, trend, trendDir, icon: Icon, color = 'blue', onClick }) {
  const colorMap = {
    blue: 'bg-primary-50 text-primary-500',
    green: 'bg-success-50 text-success-500',
    amber: 'bg-warning-50 text-warning-500',
    red: 'bg-danger-50 text-danger-500',
    neutral: 'bg-neutral-100 text-neutral-500',
  };

  return (
    <div
      className={`card p-5 flex flex-col gap-3 ${onClick ? 'cursor-pointer hover:shadow-panel transition-shadow' : ''}`}
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
        {sub && <div className="text-xs text-neutral-400 mt-0.5">{sub}</div>}
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
