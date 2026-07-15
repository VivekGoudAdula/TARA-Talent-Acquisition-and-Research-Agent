import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Shield, User, Clock, Server, Brain,
  FileJson, Lightbulb, GitBranch, CheckCircle, XCircle,
} from 'lucide-react';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';
import SectionPanel, { FieldRow } from '../components/ui/SectionPanel';
import { ErrorState } from '../components/ui/States';
import { getAuditLogById, getAuditDetail } from '../api/auditData';

function statusVariant(s) {
  const map = { Success: 'green', Failed: 'red', Pending: 'amber' };
  return map[s] || 'neutral';
}

function formatTimestamp(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function JsonBlock({ data, label }) {
  if (!data) return null;
  return (
    <div>
      <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">{label}</div>
      <pre className="text-xs font-mono bg-neutral-900 text-neutral-100 rounded-lg p-4 overflow-x-auto leading-relaxed max-h-72 overflow-y-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default function AuditDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const log = getAuditLogById(id);
  const detail = getAuditDetail(log);

  if (!detail) {
    return (
      <ErrorState
        message="Audit event not found"
        retry={() => navigate('/governance')}
      />
    );
  }

  return (
    <div className="space-y-6">
      <button type="button" onClick={() => navigate('/governance')} className="btn btn-secondary btn-sm">
        <ArrowLeft size={14} /> Back
      </button>
      <PageHeader
        title={detail.action}
        subtitle={`${detail.module} · ${formatTimestamp(detail.timestamp)}`}
        actions={<Badge variant={statusVariant(detail.status)}>{detail.status}</Badge>}
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-50 text-primary-500"><User size={16} /></div>
          <div className="min-w-0">
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">User</div>
            <div className="text-sm font-bold text-neutral-800 truncate">{detail.user}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-500"><Server size={16} /></div>
          <div className="min-w-0">
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Module</div>
            <div className="text-sm font-bold text-neutral-800">{detail.module}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-50 text-amber-500"><Clock size={16} /></div>
          <div className="min-w-0">
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Customer</div>
            <div className="text-sm font-bold text-neutral-800 truncate">{detail.customer}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className={`p-2 rounded-lg ${detail.status === 'Success' ? 'bg-success-50 text-success-500' : detail.status === 'Failed' ? 'bg-danger-50 text-danger-500' : 'bg-warning-50 text-warning-500'}`}>
            {detail.status === 'Success' ? <CheckCircle size={16} /> : detail.status === 'Failed' ? <XCircle size={16} /> : <Clock size={16} />}
          </div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Status</div>
            <Badge variant={statusVariant(detail.status)}>{detail.status}</Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionPanel title="Event Summary" subtitle="Audit record metadata">
          <div className="space-y-0">
            <FieldRow label="Audit ID" value={<span className="font-mono text-xs">{detail.audit_id}</span>} />
            <FieldRow label="Timestamp" value={formatTimestamp(detail.timestamp)} />
            <FieldRow label="User" value={detail.user} />
            <FieldRow label="Action" value={detail.action} />
            <FieldRow label="Module" value={<Badge variant="blue">{detail.module}</Badge>} />
            <FieldRow label="Customer" value={detail.customer} />
            <FieldRow label="IP Address" value={<span className="font-mono text-xs">{detail.ip_address}</span>} />
            <FieldRow label="Status" value={<Badge variant={statusVariant(detail.status)}>{detail.status}</Badge>} />
          </div>
        </SectionPanel>

        <SectionPanel title="Decision & Traceability" subtitle="AI decision and observability references">
          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                <Shield size={12} /> Decision
              </div>
              <p className="text-sm text-neutral-700 leading-relaxed bg-neutral-50 border border-neutral-100 rounded-lg p-3">
                {detail.decision}
              </p>
            </div>
            <div className="space-y-0">
              <FieldRow label="Trace ID" value={
                <span className="font-mono text-xs flex items-center gap-1 justify-end">
                  <GitBranch size={11} className="text-neutral-400" />
                  {detail.trace_id}
                </span>
              } />
              <FieldRow label="Model Used" value={
                detail.model_used
                  ? <span className="flex items-center gap-1 justify-end text-xs"><Brain size={11} className="text-primary-500" />{detail.model_used}</span>
                  : <span className="text-neutral-400">—</span>
              } />
              <FieldRow label="Prompt Version" value={
                detail.prompt_version
                  ? <span className="font-mono text-xs">{detail.prompt_version}</span>
                  : <span className="text-neutral-400">N/A</span>
              } />
              <FieldRow label="Explainability Ref" value={
                detail.explainability_reference
                  ? (
                    <Link to="/explainability" className="text-primary-600 hover:underline text-xs flex items-center gap-1 justify-end">
                      <Lightbulb size={11} />
                      {detail.explainability_reference}
                    </Link>
                  )
                  : <span className="text-neutral-400">—</span>
              } />
            </div>
          </div>
        </SectionPanel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionPanel
          title="Request"
          subtitle="Inbound API payload"
          actions={<FileJson size={14} className="text-neutral-400" />}
        >
          <JsonBlock data={detail.request} label="Request Body" />
        </SectionPanel>

        <SectionPanel
          title="Response"
          subtitle="Outbound API response"
          actions={<FileJson size={14} className="text-neutral-400" />}
        >
          <JsonBlock data={detail.response} label="Response Body" />
        </SectionPanel>
      </div>
    </div>
  );
}
