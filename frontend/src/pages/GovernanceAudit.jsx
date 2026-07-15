import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Filter, X, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import SectionPanel from '../components/ui/SectionPanel';
import KpiCard from '../components/ui/KpiCard';
import PageHeader from '../components/ui/PageHeader';
import { DUMMY_AUDIT_LOGS } from '../api/auditData';

const STATUSES = ['All', 'Success', 'Failed', 'Pending'];

function statusVariant(s) {
  const map = { Success: 'green', Failed: 'red', Pending: 'amber' };
  return map[s] || 'neutral';
}

function formatTimestamp(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
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

export default function GovernanceAudit() {
  const navigate = useNavigate();

  const [userFilter, setUserFilter] = useState('All');
  const [moduleFilter, setModuleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(true);

  const userOptions = useMemo(
    () => ['All', ...new Set(DUMMY_AUDIT_LOGS.map(a => a.user).filter(Boolean))],
    [],
  );

  const moduleOptions = useMemo(
    () => ['All', ...new Set(DUMMY_AUDIT_LOGS.map(a => a.module).filter(Boolean))],
    [],
  );

  const filtered = useMemo(() => {
    return DUMMY_AUDIT_LOGS.filter(row => {
      if (userFilter !== 'All' && row.user !== userFilter) return false;
      if (moduleFilter !== 'All' && row.module !== moduleFilter) return false;
      if (statusFilter !== 'All' && row.status !== statusFilter) return false;
      if (dateFrom) {
        const d = new Date(row.timestamp);
        if (d < new Date(`${dateFrom}T00:00:00`)) return false;
      }
      if (dateTo) {
        const d = new Date(row.timestamp);
        if (d > new Date(`${dateTo}T23:59:59`)) return false;
      }
      return true;
    });
  }, [userFilter, moduleFilter, statusFilter, dateFrom, dateTo]);

  const hasActiveFilters = userFilter !== 'All' || moduleFilter !== 'All'
    || statusFilter !== 'All' || dateFrom || dateTo;

  function clearFilters() {
    setUserFilter('All');
    setModuleFilter('All');
    setStatusFilter('All');
    setDateFrom('');
    setDateTo('');
  }

  const successCount = filtered.filter(a => a.status === 'Success').length;
  const failedCount = filtered.filter(a => a.status === 'Failed').length;
  const pendingCount = filtered.filter(a => a.status === 'Pending').length;

  const columns = [
    {
      header: 'Timestamp',
      accessor: 'timestamp',
      cell: row => <span className="text-xs font-mono text-neutral-600 whitespace-nowrap">{formatTimestamp(row.timestamp)}</span>,
    },
    {
      header: 'User',
      accessor: 'user',
      cell: row => <span className="text-xs text-neutral-700">{row.user}</span>,
    },
    {
      header: 'Action',
      accessor: 'action',
      cell: row => <span className="text-sm font-medium text-neutral-800">{row.action}</span>,
    },
    {
      header: 'Module',
      accessor: 'module',
      cell: row => <Badge variant="blue">{row.module}</Badge>,
    },
    {
      header: 'Customer',
      accessor: 'customer',
      cell: row => (
        <span className={`text-sm ${row.customer === '—' ? 'text-neutral-400' : 'text-neutral-700'}`}>
          {row.customer}
        </span>
      ),
    },
    {
      header: 'IP Address',
      accessor: 'ip_address',
      cell: row => <span className="text-xs font-mono text-neutral-500">{row.ip_address}</span>,
    },
    {
      header: 'Status',
      accessor: 'status',
      cell: row => <Badge variant={statusVariant(row.status)}>{row.status}</Badge>,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Governance & Audit"
        subtitle="Enterprise audit trail for all TARA platform actions, ML inferences, and access events."
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
        <KpiCard label="Total Events" value={filtered.length} icon={Shield} color="blue" />
        <KpiCard label="Successful" value={successCount} icon={CheckCircle} color="green" />
        <KpiCard label="Failed" value={failedCount} icon={AlertTriangle} color="red" />
        <KpiCard label="Pending" value={pendingCount} icon={Clock} color="amber" />
      </div>

      {showFilters && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Filter Audit Logs</span>
            {hasActiveFilters && (
              <button type="button" onClick={clearFilters} className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1">
                <X size={12} /> Clear all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-4">
            <FilterSelect label="User" value={userFilter} options={userOptions} onChange={setUserFilter} />
            <FilterSelect label="Module" value={moduleFilter} options={moduleOptions} onChange={setModuleFilter} />
            <FilterSelect label="Status" value={statusFilter} options={STATUSES} onChange={setStatusFilter} />
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
        title="Audit Log"
        subtitle={`${filtered.length} event${filtered.length !== 1 ? 's' : ''} — click a row for full trace details`}
      >
        <DataTable
          columns={columns}
          data={filtered}
          onRowClick={row => navigate(`/governance/${row.audit_id}`)}
          pageSize={12}
          emptyMessage="No audit events match your filters"
        />
      </SectionPanel>
    </div>
  );
}
