import React, { useState } from 'react';
import SectionPanel from '../components/ui/SectionPanel';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import PageHeader from '../components/ui/PageHeader';
import DataTable from '../components/ui/DataTable';
import { useChannelStatus, useEngagementPreview, useHandoffQueue } from '../api/hooks';
import {
  mergeEngagementChannels,
  mergeEngagementLeads,
  mergeHandoffQueue,
} from '../api/dummyData';
import api from '../api/client';
import { MessageSquare, Phone, Mail, MessageCircle, AlertTriangle, CheckCircle } from 'lucide-react';

export default function EngagementCenter() {
  const channels = useChannelStatus();
  const preview = useEngagementPreview(20, 'External');
  const handoffs = useHandoffQueue();
  const [sending, setSending] = useState({});
  const [outcomeMsg, setOutcomeMsg] = useState(null);

  if (channels.isLoading) return <PageSpinner />;
  if (channels.isError) return <ErrorState message="Could not load engagement systems data" />;

  const ch = mergeEngagementChannels(channels.data);
  const leads = preview.isError || !preview.data
    ? mergeEngagementLeads([])
    : mergeEngagementLeads(preview.data);
  const usingDemoLeads = preview.isError || !preview.data;
  const handoffQueue = mergeHandoffQueue(handoffs.data);
  const usingDemoHandoffs = false;

  const handleSend = async (lead, channel) => {
    const key = `${lead.lead_id}-${channel}`;
    setSending(prev => ({ ...prev, [key]: true }));
    try {
      await api.post('/api/engagement/send-custom', {
        phone: lead.phone_number || lead.phone,
        name: lead.full_name || lead.name || 'Customer',
        email: lead.email || null,
        channel: channel,
        use_tara_intelligence: true
      });
      setOutcomeMsg({ type: 'success', text: `Outreach sent successfully via ${channel}!` });
    } catch (err) {
      setOutcomeMsg({ type: 'danger', text: `Failed to send outreach via ${channel}.` });
    } finally {
      setSending(prev => ({ ...prev, [key]: false }));
      setTimeout(() => setOutcomeMsg(null), 5000);
    }
  };

  const columns = [
    { header: 'Lead Name', accessor: 'full_name' },
    { header: 'Contact', accessor: 'phone_number' },
    { header: 'Category', accessor: 'profile_type', cell: row => <Badge>{row.profile_type}</Badge> },
    {
      header: 'Eligibility Score', accessor: 'conversion_probability',
      cell: row => {
        const raw = row.conversion_probability;
        const v = raw != null && raw <= 1 ? Math.round(raw * 100) : Math.round(raw || 0);
        return <Badge variant={v >= 70 ? 'green' : 'amber'}>{v}%</Badge>;
      }
    },
    {
      header: 'Actions', key: 'actions',
      cell: row => (
        <div className="flex gap-2">
          {['whatsapp', 'sms', 'email'].map(channel => {
            const key = `${row.lead_id}-${channel}`;
            return (
              <button
                key={channel}
                className="btn btn-secondary btn-sm"
                onClick={() => handleSend(row, channel)}
                disabled={sending[key]}
              >
                {sending[key] ? 'Sending...' : `Send ${channel.toUpperCase()}`}
              </button>
            );
          })}
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Engagement Center"
        subtitle="Multi-channel outreach, lead preview, and officer handoff queue."
      />

      {/* Toast outcomes */}
      {outcomeMsg && (
        <div className={`p-4 rounded-md flex items-center gap-2 ${outcomeMsg.type === 'success' ? 'bg-success-50 text-success-600' : 'bg-danger-50 text-danger-600'}`}>
          {outcomeMsg.type === 'success' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          <span className="text-sm font-medium">{outcomeMsg.text}</span>
        </div>
      )}

      {/* Demo notice */}
      {(usingDemoLeads || usingDemoHandoffs) && (
        <div className="p-3 rounded-md text-xs text-amber-800 bg-amber-50 border border-amber-200 flex items-center gap-2">
          <AlertTriangle size={14} />
          <span>
            Showing demo engagement data{usingDemoLeads ? ' for outreach queue' : ''}
            {usingDemoLeads && usingDemoHandoffs ? ' and' : ''}
            {usingDemoHandoffs ? ' RM handoffs' : ''} — live data appears after pipeline scoring.
          </span>
        </div>
      )}

      {/* Grid of channels */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {(ch.channels || []).map(c => {
          const Icon = {
            voice: Phone,
            whatsapp: MessageCircle,
            sms: MessageSquare,
            email: Mail
          }[c.channel] || MessageSquare;

          return (
            <div key={c.channel} className="card p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-primary-50 text-primary-500"><Icon size={16} /></div>
                <div>
                  <div className="text-sm font-semibold text-neutral-800 capitalize">{c.channel}</div>
                  <div className="text-xs text-neutral-400">Outreach Channel</div>
                </div>
              </div>
              <Badge>{c.status}</Badge>
            </div>
          );
        })}
      </div>

      {/* Outreach Leads List */}
      <SectionPanel
        title="Active Outreach Pre-Approved Queue"
        subtitle={
          preview.isLoading
            ? 'Loading live leads from TARA…'
            : usingDemoLeads
              ? 'Showing demo leads — live preview unavailable or still loading'
              : 'Leads qualified for direct automated campaigns'
        }
      >
        {preview.isLoading ? (
          <div className="py-10 text-center text-neutral-400 text-sm">Fetching engagement preview…</div>
        ) : (
          <DataTable columns={columns} data={leads} pageSize={10} />
        )}
      </SectionPanel>

      {/* Handoff queue */}
      {handoffQueue.length > 0 && (
        <SectionPanel
          title="RM Direct Handoff Queue"
          subtitle={usingDemoHandoffs ? 'Demo candidates waiting for agent assignment' : 'Qualified candidates waiting for agent assignment'}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="table-header">Name</th>
                  <th className="table-header">RM Status</th>
                  <th className="table-header">Assigned RM</th>
                  <th className="table-header">Notes</th>
                </tr>
              </thead>
              <tbody>
                {handoffQueue.map((h, i) => (
                  <tr key={i} className="table-row">
                    <td className="table-cell font-medium">{h.customer_name}</td>
                    <td className="table-cell"><Badge>{h.status}</Badge></td>
                    <td className="table-cell">{h.assigned_rm_name || 'Unassigned'}</td>
                    <td className="table-cell">{h.status_notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionPanel>
      )}
    </div>
  );
}
