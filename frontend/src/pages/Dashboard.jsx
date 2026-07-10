import React from 'react';
import { Users, UserCheck, Target, Megaphone, Brain, TrendingUp, Phone, Activity, AlertCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts';
import KpiCard from '../components/ui/KpiCard';
import SectionPanel from '../components/ui/SectionPanel';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import { usePlatformSummary, useOpsDashboard, useChannelStatus } from '../api/hooks';
import { simulateDemoPipeline, buildDemoPipelineStepNames, mergePlatformCounts, buildPipelineOverviewChartData } from '../api/dummyData';
import PipelineFlowLine from '../components/ui/PipelineFlowLine';

function fmt(n) { return n != null ? Number(n).toLocaleString() : '—'; }

export default function Dashboard() {
  const summary = usePlatformSummary();
  const dashboard = useOpsDashboard();
  const channels = useChannelStatus();

  const [pipelineTarget, setPipelineTarget] = React.useState('both');
  const [limitInternal, setLimitInternal] = React.useState(5);
  const [limitExternal, setLimitExternal] = React.useState(5);
  const [demoRunning, setDemoRunning] = React.useState(false);
  const [demoLive, setDemoLive] = React.useState(null);
  const [demoResult, setDemoResult] = React.useState(null);

  const handleRunPipeline = async () => {
    setDemoResult(null);
    setDemoRunning(true);
    setDemoLive({
      steps: buildDemoPipelineStepNames(pipelineTarget, true).map(step => ({
        step,
        status: 'pending',
        detail: null,
        duration_ms: 0,
      })),
      current_step: null,
      is_running: true,
    });
    try {
      const result = await simulateDemoPipeline({
        target: pipelineTarget,
        limitInternal,
        limitExternal,
        trainModels: true,
        onProgress: setDemoLive,
      });
      setDemoResult(result);
    } finally {
      setDemoRunning(false);
      setDemoLive(prev => (prev ? { ...prev, is_running: false, current_step: null } : null));
    }
  };

  if (summary.isLoading) return <PageSpinner />;
  if (summary.isError) return <ErrorState message="Could not load platform summary. Is the backend running?" retry={summary.refetch} />;

  const s = summary.data || {};
  const d = dashboard.data || {};
  const ch = channels.data || {};

  // Build KPI values from platform summary (merged with demo fallbacks)
  const counts = mergePlatformCounts(s.counts);
  const pipeline = s.pipeline_status || {};

  const kpis = [
    { label: 'Internal Customers', value: fmt(counts.customers), icon: Users, color: 'blue' },
    { label: 'External Leads', value: fmt(counts.external_leads), icon: UserCheck, color: 'blue' },
    { label: '360 Profiles Built', value: fmt(counts.customer_360_profile), icon: Target, color: 'green' },
    { label: 'Feature Store', value: fmt(counts.feature_store), icon: Brain, color: 'green' },
    { label: 'Lead Features', value: fmt(counts.lead_feature_store), icon: Activity, color: 'amber' },
    { label: 'Training Dataset', value: fmt(counts.training_dataset), icon: TrendingUp, color: 'amber' },
    { label: 'Explainability Reports', value: fmt(counts.explainability_reports), icon: AlertCircle, color: 'neutral' },
    { label: 'Pipeline Status', value: pipeline.status || 'Unknown', icon: Megaphone, color: pipeline.status === 'completed' ? 'green' : 'amber' },
  ];

  // Channel status for grid
  const channelList = ch.channels || [];

  // Recent leads from summary
  const recentLeads = s.recent_leads || [];

  // Chart data from collection counts (demo-filled when API returns zeros)
  const collectionData = buildPipelineOverviewChartData(s.counts);

  const idleSteps = buildDemoPipelineStepNames(pipelineTarget, true).map(step => ({
    step,
    status: 'pending',
    detail: null,
    duration_ms: 0,
  }));
  const flowSteps = demoRunning && demoLive?.steps?.length
    ? demoLive.steps
    : (demoResult?.steps?.length ? demoResult.steps : idleSteps);

  return (
    <div className="space-y-6">
      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map(k => <KpiCard key={k.label} {...k} />)}
      </div>

      {/* Demo Pipeline Control Panel */}
      <SectionPanel
        title="Demo Pipeline Control Panel"
        subtitle="Simulated scoring & analytics flow — demo mode for presentations"
      >
        <div className="flex flex-col md:flex-row md:items-end gap-6 pb-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-600 uppercase tracking-wider block">Pipeline Target</label>
            <div className="flex rounded-md shadow-sm">
              {['both', 'internal', 'external'].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setPipelineTarget(t)}
                  className={`px-4 py-2 text-sm font-medium border first:rounded-l-md last:rounded-r-md -ml-px ${
                    pipelineTarget === t
                      ? 'bg-blue-600 border-blue-600 text-white z-10'
                      : 'bg-white border-neutral-300 text-neutral-700 hover:bg-neutral-50'
                  }`}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {(pipelineTarget === 'internal' || pipelineTarget === 'both') && (
            <div className="space-y-2 w-full md:w-36">
              <label className="text-xs font-semibold text-neutral-600 uppercase tracking-wider block">Internal Limit</label>
              <input
                type="number"
                min="1"
                max="1000"
                value={limitInternal}
                onChange={(e) => setLimitInternal(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-1.5 border border-neutral-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white text-neutral-800"
              />
            </div>
          )}

          {(pipelineTarget === 'external' || pipelineTarget === 'both') && (
            <div className="space-y-2 w-full md:w-36">
              <label className="text-xs font-semibold text-neutral-600 uppercase tracking-wider block">External Limit</label>
              <input
                type="number"
                min="1"
                max="1000"
                value={limitExternal}
                onChange={(e) => setLimitExternal(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-1.5 border border-neutral-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white text-neutral-800"
              />
            </div>
          )}

          <button
            type="button"
            disabled={demoRunning}
            onClick={handleRunPipeline}
            className={`w-full md:w-auto px-6 py-2 rounded-md font-semibold text-sm shadow-sm flex items-center justify-center gap-2 ${
              demoRunning
                ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed border border-neutral-200'
                : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
            }`}
          >
            {demoRunning ? (
              <>
                <svg className="animate-spin h-4 w-4 text-neutral-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Activity className="h-4 w-4" />
                <span>Run Pipeline</span>
              </>
            )}
          </button>
        </div>

        {/* Live pipeline flow line */}
        <div className="mt-2 border-t border-neutral-100 pt-4">
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">
            Pipeline Flow {demoRunning ? '(Live Demo)' : ''}
          </div>
          <PipelineFlowLine
            steps={flowSteps}
            currentStep={demoLive?.current_step}
            isRunning={demoRunning || demoLive?.is_running}
          />
        </div>

        {/* Pipeline Execution Details */}
        {demoResult && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-md space-y-2">
            <div className="flex items-center gap-2 text-emerald-800 font-semibold text-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              <span>Demo pipeline complete (Success: {demoResult.success ? 'Yes' : 'No'})</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 pt-2">
              {demoResult.steps?.map((step) => (
                <div key={step.step} className="bg-white border border-emerald-100 rounded px-2.5 py-1.5 text-xs shadow-sm">
                  <div className="font-semibold text-neutral-700 capitalize">{step.step.replace(/_/g, ' ')}</div>
                  <div className="flex justify-between items-center mt-1">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      step.status === 'ok' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {step.status.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-neutral-400">{step.duration_ms}ms</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </SectionPanel>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Overview Chart */}
        <SectionPanel title="Data Pipeline Overview" subtitle="Collection document counts" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={collectionData} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E1DFDD" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: '#605E5C' }}
                interval={0}
                angle={-35}
                textAnchor="end"
                height={56}
              />
              <YAxis tick={{ fontSize: 11, fill: '#605E5C' }} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E1DFDD' }}
                formatter={(value) => [Number(value).toLocaleString(), 'Documents']}
              />
              <Bar dataKey="value" fill="#0078D4" radius={[4, 4, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </SectionPanel>

        {/* Channel Status */}
        <SectionPanel title="Engagement Channels" subtitle="Real-time channel health">
          {channelList.length === 0 ? (
            <div className="text-sm text-neutral-400 text-center py-8">No channel data</div>
          ) : (
            <div className="space-y-2">
              {channelList.map(ch => (
                <div key={ch.channel} className="flex items-center justify-between py-1.5 border-b border-neutral-50 last:border-0">
                  <span className="text-sm font-medium text-neutral-700 capitalize">{ch.channel}</span>
                  <Badge>{ch.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </SectionPanel>
      </div>

      {/* Recent Leads */}
      {recentLeads.length > 0 && (
        <SectionPanel title="Recent External Leads" subtitle="Latest leads from CRM">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  {['Name', 'Status', 'Campaign', 'Source', 'Created'].map(h => (
                    <th key={h} className="table-header">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentLeads.slice(0, 8).map((lead, i) => (
                  <tr key={i} className="table-row">
                    <td className="table-cell font-medium">{lead.full_name || lead.name || '—'}</td>
                    <td className="table-cell"><Badge>{lead.lead_status || lead.status}</Badge></td>
                    <td className="table-cell">{lead.campaign || '—'}</td>
                    <td className="table-cell">{lead.referral_source || '—'}</td>
                    <td className="table-cell text-neutral-400">{lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionPanel>
      )}

      {/* Pipeline Metadata */}
      {pipeline && Object.keys(pipeline).length > 0 && (
        <SectionPanel title="Pipeline Status">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(pipeline).map(([k, v]) => (
              <div key={k} className="bg-neutral-50 rounded p-3">
                <div className="text-xs text-neutral-500 capitalize mb-1">{k.replace(/_/g, ' ')}</div>
                <div className="text-sm font-semibold text-neutral-800 truncate">{String(v)}</div>
              </div>
            ))}
          </div>
        </SectionPanel>
      )}
    </div>
  );
}
