import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Filter, X, CheckCircle, MessageSquare, TrendingUp } from 'lucide-react';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import SectionPanel from '../components/ui/SectionPanel';
import KpiCard from '../components/ui/KpiCard';
import PageHeader from '../components/ui/PageHeader';
import { useCampaigns } from '../context/CampaignContext';

const CHANNELS = ['All', 'Voice', 'Email', 'SMS', 'WhatsApp', 'Multi-Channel'];
const OUTCOMES = ['All', 'Converted', 'Interested', 'Follow-up Scheduled', 'Callback Scheduled', 'Opened', 'Link Clicked', 'Engaged', 'No Response', 'No Answer', 'Declined'];
const SENTIMENTS = ['All', 'Positive', 'Neutral-Positive', 'Neutral', 'Negative'];

function sentimentVariant(s) {
  if (!s) return 'neutral';
  const lower = s.toLowerCase();
  if (lower.includes('negative')) return 'red';
  if (lower === 'positive' || (lower.includes('positive') && !lower.includes('neutral'))) return 'green';
  if (lower.includes('positive')) return 'green';
  return 'amber';
}

function outcomeVariant(o) {
  const map = {
    Converted: 'green',
    Interested: 'blue',
    'Follow-up Scheduled': 'amber',
    'Callback Scheduled': 'amber',
    Opened: 'blue',
    'Link Clicked': 'blue',
    Engaged: 'blue',
    'No Response': 'neutral',
    'No Answer': 'neutral',
    Declined: 'red',
  };
  return map[o] || 'neutral';
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function FilterSelect({ label, value, options, onChange }) {
  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{label}</label>
      <select className="form-select py-1.5 text-sm" value={value} onChange={e => onChange(e.target.value)}>
        {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    </div>
  );
}

export default function InteractionHistory() {
  const navigate = useNavigate();
  const { completedInteractions } = useCampaigns();

  const [channelFilter, setChannelFilter] = useState('All');
  const [campaignFilter, setCampaignFilter] = useState('All');
  const [outcomeFilter, setOutcomeFilter] = useState('All');
  const [sentimentFilter, setSentimentFilter] = useState('All');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(true);

  const campaignOptions = useMemo(
    () => ['All', ...new Set(completedInteractions.map(i => i.campaign).filter(Boolean))],
    [completedInteractions],
  );

  const filtered = useMemo(() => {
    return completedInteractions.filter(row => {
      if (channelFilter !== 'All' && row.channel !== channelFilter) return false;
      if (campaignFilter !== 'All' && row.campaign !== campaignFilter) return false;
      if (outcomeFilter !== 'All' && row.outcome !== outcomeFilter) return false;
      if (sentimentFilter !== 'All' && row.sentiment !== sentimentFilter) return false;
      if (dateFrom) {
        const d = new Date(row.date);
        if (d < new Date(`${dateFrom}T00:00:00`)) return false;
      }
      if (dateTo) {
        const d = new Date(row.date);
        if (d > new Date(`${dateTo}T23:59:59`)) return false;
      }
      return true;
    });
  }, [completedInteractions, channelFilter, campaignFilter, outcomeFilter, sentimentFilter, dateFrom, dateTo]);

  const hasActiveFilters = channelFilter !== 'All' || campaignFilter !== 'All'
    || outcomeFilter !== 'All' || sentimentFilter !== 'All' || dateFrom || dateTo;

  function clearFilters() {
    setChannelFilter('All');
    setCampaignFilter('All');
    setOutcomeFilter('All');
    setSentimentFilter('All');
    setDateFrom('');
    setDateTo('');
  }

  const convertedCount = filtered.filter(i => i.outcome === 'Converted').length;
  const positiveCount = filtered.filter(i => i.sentiment?.toLowerCase().includes('positive')).length;
  const voiceCount = filtered.filter(i => i.channel === 'Voice').length;

  const columns = [
    {
      header: 'Customer',
      accessor: 'customer_name',
      cell: row => (
        <div>
          <div className="font-medium text-neutral-800">{row.customer_name}</div>
          {row.phone && row.phone !== '—' && (
            <div className="text-xs text-neutral-400 font-mono mt-0.5">{row.phone}</div>
          )}
        </div>
      ),
    },
    {
      header: 'Date',
      accessor: 'date',
      cell: row => <span className="text-xs text-neutral-600 whitespace-nowrap">{formatDate(row.date)}</span>,
    },
    {
      header: 'Channel',
      accessor: 'channel',
      cell: row => <Badge>{row.channel}</Badge>,
    },
    {
      header: 'Campaign',
      accessor: 'campaign',
      cell: row => <span className="text-xs text-neutral-700">{row.campaign}</span>,
    },
    {
      header: 'Duration',
      accessor: 'duration',
      cell: row => <span className="font-mono text-xs">{row.duration || '—'}</span>,
    },
    {
      header: 'Outcome',
      accessor: 'outcome',
      cell: row => <Badge variant={outcomeVariant(row.outcome)}>{row.outcome}</Badge>,
    },
    {
      header: 'Sentiment',
      accessor: 'sentiment',
      cell: row => <Badge variant={sentimentVariant(row.sentiment)}>{row.sentiment}</Badge>,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Interaction History"
        subtitle="Browse completed outreach sessions across all channels and campaigns."
        actions={
          <button
            type="button"
            onClick={() => setShowFilters(v => !v)}
            className={`btn btn-secondary btn-sm ${showFilters ? 'border-primary-300 text-primary-600' : ''}`}
          >
            <Filter size={14} />
            Filters
            {hasActiveFilters && (
              <span className="ml-1 w-2 h-2 rounded-full bg-primary-500 inline-block" />
            )}
          </button>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Interactions" value={filtered.length} icon={History} color="blue" />
        <KpiCard label="Conversions" value={convertedCount} icon={CheckCircle} color="green" />
        <KpiCard label="Positive Sentiment" value={positiveCount} icon={TrendingUp} color="amber" />
        <KpiCard label="Voice Sessions" value={voiceCount} icon={MessageSquare} color="blue" />
      </div>

      {showFilters && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Filter Interactions</span>
            {hasActiveFilters && (
              <button type="button" onClick={clearFilters} className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1">
                <X size={12} /> Clear all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-4">
            <FilterSelect label="Channel" value={channelFilter} options={CHANNELS} onChange={setChannelFilter} />
            <FilterSelect label="Campaign" value={campaignFilter} options={campaignOptions} onChange={setCampaignFilter} />
            <FilterSelect label="Outcome" value={outcomeFilter} options={OUTCOMES} onChange={setOutcomeFilter} />
            <FilterSelect label="Sentiment" value={sentimentFilter} options={SENTIMENTS} onChange={setSentimentFilter} />
            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">From</label>
              <input type="date" className="form-input py-1.5 text-sm" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">To</label>
              <input type="date" className="form-input py-1.5 text-sm" value={dateTo} onChange={e => setDateTo(e.target.value)} />
            </div>
          </div>
        </div>
      )}

      <SectionPanel
        title="Completed Interactions"
        subtitle={`${filtered.length} interaction${filtered.length !== 1 ? 's' : ''} — click a row for full details`}
      >
        <DataTable
          columns={columns}
          data={filtered}
          onRowClick={row => navigate(`/history/${row.interaction_id}`)}
          pageSize={12}
          emptyMessage="No completed interactions match your filters"
        />
      </SectionPanel>
    </div>
  );
}
