import React from 'react';
const VARIANTS = {
  blue: 'badge-blue',
  green: 'badge-green',
  amber: 'badge-amber',
  red: 'badge-red',
  neutral: 'badge-neutral',
};

const STATUS_MAP = {
  NEW: 'blue', ACTIVE: 'green', ENRICHED: 'green', QUALIFIED: 'green',
  CONTACTED: 'amber', CONVERTED: 'green', DISQUALIFIED: 'red',
  HIGH: 'green', MEDIUM: 'amber', LOW: 'amber', VERY_HIGH: 'green',
  healthy: 'green', degraded: 'amber', unavailable: 'red', untrained: 'neutral',
  true: 'green', false: 'neutral',
};

export default function Badge({ children, variant }) {
  const v = variant || STATUS_MAP[String(children)] || 'neutral';
  return <span className={VARIANTS[v] || 'badge-neutral'}>{children}</span>;
}
