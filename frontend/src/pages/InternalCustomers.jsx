import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import SectionPanel from '../components/ui/SectionPanel';
import { useCrmCustomers } from '../api/hooks';

function scoreColor(v) {
  if (v == null) return 'neutral';
  if (v >= 750) return 'green';
  if (v >= 650) return 'amber';
  return 'red';
}

function healthColor(v) {
  if (v == null) return 'neutral';
  if (v >= 70) return 'green';
  if (v >= 40) return 'amber';
  return 'red';
}

export default function InternalCustomers() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useCrmCustomers('internal', '', 1000);

  if (isLoading) return <PageSpinner />;
  if (isError) return <ErrorState message="Failed to load internal customers" retry={refetch} />;

  const customers = Array.isArray(data) ? data : [];

  const columns = [
    {
      header: 'Name', accessor: 'full_name',
      cell: row => (
        <div>
          <div className="font-medium text-neutral-800">{row.full_name || row.name || '—'}</div>
          <div className="text-xs text-neutral-400">{row.customer_id || row.id || ''}</div>
        </div>
      )
    },
    { header: 'Segment', accessor: 'segment', cell: row => <Badge>{row.segment || 'N/A'}</Badge> },
    {
      header: 'Credit Score', accessor: 'credit_score',
      cell: row => <Badge variant={scoreColor(row.credit_score)}>{row.credit_score ?? '—'}</Badge>
    },
    {
      header: 'Financial Health', accessor: 'financial_health_score',
      cell: row => {
        const v = row.financial_health_score;
        return v != null ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-neutral-100 rounded-full w-16">
              <div className={`h-full rounded-full ${healthColor(v) === 'green' ? 'bg-success-500' : healthColor(v) === 'amber' ? 'bg-warning-500' : 'bg-danger-500'}`} style={{ width: `${Math.min(100, v)}%` }} />
            </div>
            <span className="text-xs">{v}</span>
          </div>
        ) : '—';
      }
    },
    {
      header: 'Engagement Score', accessor: 'engagement_score',
      cell: row => row.engagement_score != null ? <span className="text-sm font-medium">{Number(row.engagement_score).toFixed(1)}</span> : '—'
    },
    { header: 'City', accessor: 'city', cell: row => row.city || '—' },
    {
      header: 'Repayment', accessor: 'repayment_label',
      cell: row => {
        const v = row.repayment_label || row.repayment_capacity;
        if (!v) return '—';
        const variant = v === 'High' ? 'green' : v === 'Medium' ? 'amber' : 'red';
        return <Badge variant={variant}>{v}</Badge>;
      }
    },
    {
      header: 'Recommended Product', accessor: 'recommended_product',
      cell: row => row.recommended_product
        ? <Badge variant="blue">{row.recommended_product}</Badge>
        : '—'
    },
  ];

  return (
    <div className="space-y-4">
      <SectionPanel
        title={`Internal Customers (${customers.length.toLocaleString()})`}
        subtitle="All core banking customers — click to view Customer 360 profile"
      >
        <DataTable
          columns={columns}
          data={customers}
          onRowClick={row => navigate(`/customer/${row.customer_id || row.entity_id || row.id}`)}
          pageSize={25}
          emptyMessage="No internal customers found"
        />
      </SectionPanel>
    </div>
  );
}
