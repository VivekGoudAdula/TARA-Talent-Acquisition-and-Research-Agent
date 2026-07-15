import React, { useState } from 'react';
import SectionPanel from '../components/ui/SectionPanel';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import PageHeader from '../components/ui/PageHeader';
import { useCrmCustomers, useExplainReport } from '../api/hooks';
import { buildDummyExplainReport } from '../api/dummyData';
import { RefreshCw, Activity, TrendingUp, ShieldCheck, AlertCircle } from 'lucide-react';

// ── Helpers ──────────────────────────────────────────────────────────────────

function ScoreRing({ value, label, color = '#4f46e5' }) {
  const pct = Math.min(100, Math.max(0, Math.round((value ?? 0) * 100)));
  const r = 26;
  const circ = 2 * Math.PI * r;
  const dash = circ - (circ * pct) / 100;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={68} height={68} className="-rotate-90">
        <circle cx={34} cy={34} r={r} strokeWidth={5} stroke="#e5e7eb" fill="none" />
        <circle
          cx={34} cy={34} r={r} strokeWidth={5} stroke={color} fill="none"
          strokeDasharray={circ} strokeDashoffset={dash}
          strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <span className="text-lg font-bold text-neutral-800 -mt-11 rotate-90 relative z-10"
        style={{ color }}>{pct}%</span>
      <span className="text-xs text-neutral-500 mt-5 text-center leading-tight">{label}</span>
    </div>
  );
}

function ReasonBadge({ code, feature, explanation }) {
  const colors = ['bg-violet-50 text-violet-700 border-violet-200',
    'bg-sky-50 text-sky-700 border-sky-200',
    'bg-emerald-50 text-emerald-700 border-emerald-200',
    'bg-amber-50 text-amber-700 border-amber-200',
    'bg-rose-50 text-rose-700 border-rose-200'];
  const c = colors[code % colors.length] || colors[0];
  return (
    <div className={`flex gap-3 items-start p-3 rounded-lg border ${c}`}>
      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white/60 border border-current">
        #{code}
      </span>
      <div>
        <div className="text-sm font-semibold">{feature}</div>
        {explanation && <div className="text-xs mt-0.5 opacity-75">{explanation}</div>}
      </div>
    </div>
  );
}

// ── Empty / Pipeline-not-run state ───────────────────────────────────────────
function NoReportState({ customerName }) {
  return (
    <div className="card p-10 flex flex-col items-center justify-center text-center h-full gap-4">
      <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center">
        <Activity size={28} className="text-amber-500" />
      </div>
      <div>
        <p className="font-semibold text-neutral-800 text-base">No Explanation Report Found</p>
        <p className="text-sm text-neutral-500 mt-1 max-w-xs mx-auto leading-relaxed">
          No ML explanation data exists for <strong>{customerName || 'this customer'}</strong> in the database yet.
          Run the Explainability Pipeline to generate and persist reports.
        </p>
      </div>
      <div className="mt-2 px-4 py-2 rounded-md bg-amber-50 border border-amber-200 text-xs text-amber-700 flex items-center gap-2">
        <AlertCircle size={13} />
        <span>Trigger pipeline → data will appear here automatically on next refresh</span>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ExplainableAI() {
  const [selectedId, setSelectedId] = useState(null);
  const [selectedName, setSelectedName] = useState('');

  const customersQuery = useCrmCustomers('internal', '', 200);
  const explainQuery = useExplainReport(selectedId);

  if (customersQuery.isLoading) return <PageSpinner />;
  if (customersQuery.isError) return <ErrorState message="Could not load customer profiles" />;

  const customers = customersQuery.data || [];
  const selectedCustomer = customers.find(
    c => (c.customer_id || c.entity_id || c.id) === selectedId
  );
  const apiReport = explainQuery.data;
  const exp = apiReport || null;
  const isDemoReport = false;

  const handleSelect = (c) => {
    const cid = c.customer_id || c.entity_id || c.id;
    setSelectedId(cid);
    setSelectedName(c.full_name || c.name || '');
  };

  const repayment = exp?.repayment_prediction;
  const convProb  = exp?.conversion_probability;
  const product   = exp?.recommended_product;
  const reasons   = exp?.reason_codes ?? [];
  const narrative = exp?.explanation?.summary || exp?.narrative || '';
  const repayExp  = exp?.explanation?.repayment_explanation || '';
  const prodExp   = exp?.explanation?.product_explanation || '';
  const convExp   = exp?.explanation?.conversion_explanation || '';
  const updatedAt = exp?.created_at ? new Date(exp.created_at).toLocaleString('en-IN', {
    dateStyle: 'medium', timeStyle: 'short'
  }) : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Explainable AI"
        subtitle="AI-driven explanations for repayment, conversion, and product recommendations."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* ── Left: Customer List ─────────────────────────────────────────── */}
      <SectionPanel title="Customer Profiles" subtitle="Click to load AI explanation from database">
        <div className="space-y-1 max-h-[620px] overflow-y-auto pr-1">
          {customers.map((c) => {
            const cid = c.customer_id || c.entity_id || c.id;
            const active = selectedId === cid;
            return (
              <button
                key={cid}
                onClick={() => handleSelect(c)}
                className={`w-full text-left p-3 rounded-lg text-sm transition-all border flex items-center justify-between gap-2
                  ${active
                    ? 'bg-primary-50 border-primary-300 font-medium shadow-sm'
                    : 'hover:bg-neutral-50 bg-white border-neutral-100'}`}
              >
                <div className="min-w-0">
                  <div className="text-neutral-800 font-medium truncate">
                    {c.full_name || c.name || '—'}
                  </div>
                  <div className="text-[10px] text-neutral-400 font-mono mt-0.5 truncate">{cid}</div>
                </div>
                <Badge>{c.segment || c.account_type || 'Standard'}</Badge>
              </button>
            );
          })}
        </div>
      </SectionPanel>

      {/* ── Right: Explanation Panel ────────────────────────────────────── */}
      <div className="md:col-span-2 space-y-5">
        {!selectedId ? (
          <div className="card p-10 flex flex-col items-center justify-center text-center h-full text-neutral-400">
            <span className="text-4xl mb-4">🔍</span>
            <p className="font-semibold text-neutral-700">Select a Customer Profile</p>
            <p className="text-xs mt-1">Click any profile on the left — explanation data loads directly from the database</p>
          </div>
        ) : explainQuery.isLoading ? (
          <div className="card p-10 flex items-center justify-center">
            <RefreshCw size={22} className="animate-spin text-primary-500 mr-3" />
            <span className="text-sm text-neutral-500">Fetching explanation from database...</span>
          </div>
        ) : explainQuery.isError ? (
          <ErrorState message="Failed to reach the backend. Please check the server." />
        ) : !exp ? (
          <NoReportState customerName={selectedName} />
        ) : (
          <>
            {isDemoReport && (
              <div className="card p-3 text-xs text-amber-800 bg-amber-50 border border-amber-200 flex items-center gap-2">
                <AlertCircle size={14} />
                Demo explanation — run Explainability Pipeline to persist live reports for {selectedName}.
              </div>
            )}
            {/* Header */}
            <div className="card p-4 flex items-center justify-between">
              <div>
                <div className="text-base font-semibold text-neutral-800">{selectedName}</div>
                {updatedAt && (
                  <div className="text-xs text-neutral-400 mt-0.5 flex items-center gap-1">
                    <RefreshCw size={10} /> Last pipeline run: {updatedAt}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {exp.profile_type && <Badge>{exp.profile_type}</Badge>}
                {product && <Badge variant="blue">{product}</Badge>}
              </div>
            </div>

            {/* Score rings */}
            <SectionPanel title="ML Predictions" subtitle="Direct from latest pipeline output in database">
              <div className="flex flex-wrap gap-8 justify-around py-4">
                {convProb != null && (
                  <ScoreRing value={convProb} label="Conversion Probability" color="#4f46e5" />
                )}
                {repayment != null && typeof repayment === 'number' && (
                  <ScoreRing value={repayment} label="Repayment Capacity" color="#10b981" />
                )}
                {repayment != null && typeof repayment === 'string' && (
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center justify-center w-16 h-16 rounded-full bg-emerald-50 border-2 border-emerald-300">
                      <ShieldCheck size={24} className="text-emerald-600" />
                    </div>
                    <span className="text-xs text-neutral-500 mt-1 text-center">Repayment</span>
                    <Badge variant="green">{repayment}</Badge>
                  </div>
                )}
              </div>
            </SectionPanel>

            {/* AI Narrative */}
            {narrative && (
              <SectionPanel
                title="AI Narrative Explanation"
                subtitle="Generated by the Explainability Pipeline"
              >
                <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 text-sm leading-relaxed text-neutral-700 whitespace-pre-line">
                  {narrative}
                </div>
              </SectionPanel>
            )}

            {/* Dimension-level explanations */}
            {(repayExp || prodExp || convExp) && (
              <SectionPanel title="Dimension Analysis">
                <div className="space-y-3">
                  {repayExp && (
                    <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                      <div className="text-xs font-bold text-emerald-700 uppercase mb-1 flex items-center gap-1">
                        <ShieldCheck size={12} /> Repayment Capacity
                      </div>
                      <p className="text-sm text-emerald-900">{repayExp}</p>
                    </div>
                  )}
                  {prodExp && (
                    <div className="p-3 rounded-lg bg-sky-50 border border-sky-200">
                      <div className="text-xs font-bold text-sky-700 uppercase mb-1 flex items-center gap-1">
                        <TrendingUp size={12} /> Product Recommendation
                      </div>
                      <p className="text-sm text-sky-900">{prodExp}</p>
                    </div>
                  )}
                  {convExp && (
                    <div className="p-3 rounded-lg bg-violet-50 border border-violet-200">
                      <div className="text-xs font-bold text-violet-700 uppercase mb-1 flex items-center gap-1">
                        <Activity size={12} /> Conversion Likelihood
                      </div>
                      <p className="text-sm text-violet-900">{convExp}</p>
                    </div>
                  )}
                </div>
              </SectionPanel>
            )}

            {/* Reason codes */}
            {reasons.length > 0 && (
              <SectionPanel title="Reason Codes & Feature Drivers">
                <div className="space-y-2">
                  {reasons.map((rc, i) => (
                    <ReasonBadge
                      key={i}
                      code={rc.code ?? i + 1}
                      feature={rc.feature || rc.label || String(rc)}
                      explanation={rc.explanation || rc.description || ''}
                    />
                  ))}
                </div>
              </SectionPanel>
            )}
          </>
        )}
      </div>
    </div>
  );
}
