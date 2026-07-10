import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import SectionPanel from '../components/ui/SectionPanel';
import { useExternalLeads, useChannelStatus } from '../api/hooks';
import KpiCard from '../components/ui/KpiCard';
import { UserCheck, Target, TrendingUp, Globe } from 'lucide-react';

export default function ExternalLeads() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useExternalLeads(1000);

  if (isLoading) return <PageSpinner />;
  if (isError) return <ErrorState message="Failed to load external leads" retry={refetch} />;

  const leads = data?.leads || [];
  const total = data?.total || leads.length;

  const qualified = leads.filter(l => l.lead_status === 'QUALIFIED' || l.lead_status === 'ENRICHED').length;
  const campaigns = [...new Set(leads.map(l => l.campaign).filter(Boolean))].length;
  const avgScore = leads.length > 0
    ? Math.round(leads.reduce((s, l) => s + (l.credit_score || 0), 0) / leads.length)
    : 0;

  const columns = [
    {
      header: 'Lead', accessor: 'full_name',
      cell: row => (
        <div>
          <div className="font-medium text-neutral-800">{row.full_name || '—'}</div>
          <div className="text-xs text-neutral-400">{row.external_reference}</div>
        </div>
      )
    },
    { header: 'Status', accessor: 'lead_status', cell: row => <Badge>{row.lead_status}</Badge> },
    { header: 'Campaign', accessor: 'campaign', cell: row => row.campaign || '—' },
    { header: 'Source', accessor: 'referral_source', cell: row => row.referral_source || '—' },
    {
      header: 'Credit Score', accessor: 'credit_score',
      cell: row => {
        const v = row.credit_score;
        const color = v >= 750 ? 'green' : v >= 650 ? 'amber' : 'red';
        return <Badge variant={color}>{v ?? '—'}</Badge>;
      }
    },
    {
      header: 'Income', accessor: 'estimated_income',
      cell: row => row.estimated_income ? `₹${Number(row.estimated_income).toLocaleString('en-IN')}` : '—'
    },
    { header: 'City', accessor: 'city', cell: row => row.city || '—' },
    { header: 'Consent', accessor: 'consent', cell: row => <Badge>{row.consent ? 'Yes' : 'No'}</Badge> },
    {
      header: 'Created', accessor: 'created_at',
      cell: row => row.lead_created_date ? new Date(row.lead_created_date).toLocaleDateString() : '—'
    },
  ];

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Leads" value={total.toLocaleString()} icon={UserCheck} color="blue" />
        <KpiCard label="Qualified / Enriched" value={qualified.toLocaleString()} icon={Target} color="green" />
        <KpiCard label="Campaigns" value={campaigns} icon={Globe} color="amber" />
        <KpiCard label="Avg Credit Score" value={avgScore} icon={TrendingUp} color="blue" />
      </div>

      <SectionPanel
        title={`External Leads (${total.toLocaleString()})`}
        subtitle="CRM leads from external sources — click to view enriched profile"
      >
        <DataTable
          columns={columns}
          data={leads}
          onRowClick={row => navigate(`/lead/${row.lead_id}`)}
          pageSize={25}
          emptyMessage="No external leads found"
        />
      </SectionPanel>
    </div>
  );
}
