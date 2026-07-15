import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Clock, Megaphone, User, Phone, Mail, MapPin,
  MessageSquare, Brain, Target, TrendingUp, Lightbulb,
  CheckCircle, AlertCircle, FileText, Calendar,
} from 'lucide-react';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';
import SectionPanel, { FieldRow, ScoreBar } from '../components/ui/SectionPanel';
import { ErrorState } from '../components/ui/States';
import { useCampaigns } from '../context/CampaignContext';
import { getDummyInteractionById, getInteractionDetail } from '../api/interactionData';

const EXPLAIN_COLORS = [
  'bg-violet-50 text-violet-700 border-violet-200',
  'bg-sky-50 text-sky-700 border-sky-200',
  'bg-emerald-50 text-emerald-700 border-emerald-200',
  'bg-amber-50 text-amber-700 border-amber-200',
  'bg-rose-50 text-rose-700 border-rose-200',
];

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

function priorityVariant(p) {
  const map = { High: 'red', Medium: 'amber', Low: 'green', None: 'neutral' };
  return map[p] || 'neutral';
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ExplainNote({ code, feature, explanation, impact }) {
  const colorClass = EXPLAIN_COLORS[(code - 1) % EXPLAIN_COLORS.length];
  return (
    <div className={`flex gap-3 items-start p-3 rounded-lg border ${colorClass}`}>
      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white/60 border border-current shrink-0">
        #{code}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold">{feature.replace(/_/g, ' ')}</span>
          {impact && (
            <Badge variant={impact === 'high' ? 'green' : impact === 'medium' ? 'amber' : 'neutral'}>
              {impact} impact
            </Badge>
          )}
        </div>
        {explanation && <p className="text-xs mt-1 opacity-80 leading-relaxed">{explanation}</p>}
      </div>
    </div>
  );
}

export default function InteractionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getInteractionById } = useCampaigns();

  const base = getInteractionById(id) || getDummyInteractionById(id);
  const detail = getInteractionDetail(base);

  if (!detail) {
    return (
      <ErrorState
        message="Interaction not found"
        retry={() => navigate('/history')}
      />
    );
  }

  const { customer, campaign_info, call_metadata, customer_intent, sentiment_analysis, outcome_detail, follow_up, explainability_notes } = detail;
  const hasTranscript = Array.isArray(detail.transcript) && detail.transcript.length > 0;
  const sentimentPct = Math.round((sentiment_analysis?.score ?? 0.5) * 100);

  return (
    <div className="space-y-6">
      <button type="button" onClick={() => navigate('/history')} className="btn btn-secondary btn-sm">
        <ArrowLeft size={14} /> Back
      </button>
      <PageHeader
        title={customer.name}
        subtitle={`${call_metadata.channel} · ${formatDate(call_metadata.started_at)} · ${call_metadata.duration}`}
        actions={<Badge variant={outcomeVariant(outcome_detail.label)}>{outcome_detail.label}</Badge>}
      />

      {/* Top summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-50 text-primary-500"><User size={16} /></div>
          <div className="min-w-0">
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Customer</div>
            <div className="text-sm font-bold text-neutral-800 truncate">{customer.name}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-500"><Megaphone size={16} /></div>
          <div className="min-w-0">
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Campaign</div>
            <div className="text-sm font-bold text-neutral-800 truncate">{campaign_info.name}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-50 text-amber-500"><Clock size={16} /></div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Duration</div>
            <div className="text-sm font-bold text-neutral-800 font-mono">{call_metadata.duration}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-success-50 text-success-500"><MessageSquare size={16} /></div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Channel</div>
            <div className="text-sm font-bold text-neutral-800">{call_metadata.channel}</div>
          </div>
        </div>
      </div>

      {/* Customer + Campaign + Call Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SectionPanel title="Customer Information" subtitle="Profile and contact details">
          <div className="space-y-0">
            <FieldRow label="Full Name" value={customer.name} />
            <FieldRow label="Customer ID" value={<span className="font-mono text-xs">{customer.customer_id}</span>} />
            <FieldRow label="Profile Type" value={<Badge>{customer.profile_type}</Badge>} />
            <FieldRow label="Segment" value={customer.segment} />
            <FieldRow label="City" value={
              <span className="flex items-center gap-1 justify-end"><MapPin size={12} className="text-neutral-400" />{customer.city}</span>
            } />
            {customer.credit_score && (
              <FieldRow label="Credit Score" value={<Badge variant={customer.credit_score >= 700 ? 'green' : 'amber'}>{customer.credit_score}</Badge>} />
            )}
            {customer.account_tenure_years != null && (
              <FieldRow label="Account Tenure" value={`${customer.account_tenure_years} years`} />
            )}
            <FieldRow label="Phone" value={
              <span className="flex items-center gap-1 justify-end font-mono text-xs"><Phone size={12} className="text-neutral-400" />{customer.phone}</span>
            } />
            <FieldRow label="Email" value={
              <span className="flex items-center gap-1 justify-end text-xs"><Mail size={12} className="text-neutral-400 shrink-0" />{customer.email}</span>
            } />
          </div>
        </SectionPanel>

        <SectionPanel title="Campaign" subtitle="Outreach program context">
          <div className="space-y-0">
            <FieldRow label="Campaign Name" value={campaign_info.name} />
            <FieldRow label="Product" value={<Badge variant="blue">{campaign_info.product}</Badge>} />
            <FieldRow label="Target Audience" value={campaign_info.target_audience} />
            <FieldRow label="Campaign Channel" value={<Badge>{campaign_info.channel}</Badge>} />
            <FieldRow label="Status" value={
              <Badge variant={campaign_info.status === 'Active' ? 'green' : campaign_info.status === 'Completed' ? 'blue' : 'neutral'}>
                {campaign_info.status}
              </Badge>
            } />
            {campaign_info.campaign_id && (
              <FieldRow
                label="View Program"
                value={
                  <Link to={`/outreach/${campaign_info.campaign_id}`} className="text-primary-600 hover:underline text-sm">
                    Open campaign →
                  </Link>
                }
              />
            )}
          </div>
        </SectionPanel>

        <SectionPanel title="Call Metadata" subtitle="Session technical details">
          <div className="space-y-0">
            <FieldRow label="Call / Session ID" value={<span className="font-mono text-xs">{call_metadata.call_id}</span>} />
            <FieldRow label="Session ID" value={<span className="font-mono text-xs">{call_metadata.session_id}</span>} />
            <FieldRow label="Direction" value={<Badge>{call_metadata.direction}</Badge>} />
            <FieldRow label="Started" value={formatDate(call_metadata.started_at)} />
            <FieldRow label="Ended" value={formatDate(call_metadata.ended_at)} />
            <FieldRow label="Duration" value={<span className="font-mono">{call_metadata.duration}</span>} />
            <FieldRow label="Agent" value={call_metadata.agent} />
            <FieldRow label="Language" value={call_metadata.language} />
            <FieldRow label="Recording" value={
              call_metadata.recording_available
                ? <Badge variant="green">Available</Badge>
                : <Badge variant="neutral">N/A</Badge>
            } />
            {call_metadata.twilio_sid && (
              <FieldRow label="Twilio SID" value={<span className="font-mono text-xs">{call_metadata.twilio_sid}</span>} />
            )}
          </div>
        </SectionPanel>
      </div>

      {/* AI Summary */}
      <SectionPanel title="AI Summary" subtitle="TARA-generated session overview">
        <div className="flex gap-3">
          <div className="p-2.5 rounded-lg bg-primary-50 text-primary-500 shrink-0 h-fit">
            <Brain size={18} />
          </div>
          <p className="text-sm text-neutral-700 leading-relaxed">{detail.ai_summary}</p>
        </div>
      </SectionPanel>

      {/* Intent, Sentiment, Outcome, Follow-up */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionPanel title="Customer Intent" subtitle="Detected intent classification">
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs text-neutral-400 uppercase tracking-wider font-medium mb-1">Primary Intent</div>
                <div className="text-base font-semibold text-neutral-800">{customer_intent.primary}</div>
                {customer_intent.secondary && (
                  <div className="text-xs text-neutral-500 mt-1">Secondary: {customer_intent.secondary}</div>
                )}
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs text-neutral-400 mb-1">Confidence</div>
                <div className="text-lg font-bold text-primary-600">
                  {Math.round((customer_intent.confidence ?? 0) * 100)}%
                </div>
              </div>
            </div>
            {customer_intent.keywords?.length > 0 && (
              <div>
                <div className="text-xs text-neutral-400 uppercase tracking-wider font-medium mb-2">Keywords</div>
                <div className="flex flex-wrap gap-1.5">
                  {customer_intent.keywords.map(kw => (
                    <span key={kw} className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 border border-neutral-200">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <FieldRow label="Intent Category" value={<Badge variant="blue">{customer_intent.intent_category?.replace(/_/g, ' ')}</Badge>} />
          </div>
        </SectionPanel>

        <SectionPanel title="Sentiment Analysis" subtitle="Emotional tone across the session">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-neutral-400 uppercase tracking-wider font-medium mb-1">Overall Sentiment</div>
                <Badge variant={sentimentVariant(sentiment_analysis.overall)}>{sentiment_analysis.overall}</Badge>
              </div>
              <div className="text-right">
                <div className="text-xs text-neutral-400 mb-1">Score</div>
                <div className="text-lg font-bold text-neutral-800">{sentimentPct}%</div>
              </div>
            </div>
            <ScoreBar
              label="Sentiment Score"
              value={sentimentPct}
              color={sentimentPct >= 70 ? 'green' : sentimentPct >= 45 ? 'amber' : 'red'}
            />
            <FieldRow label="Trend" value={
              <span className="flex items-center gap-1 justify-end capitalize">
                <TrendingUp size={12} className="text-neutral-400" />
                {sentiment_analysis.trend}
              </span>
            } />
            {sentiment_analysis.breakdown?.length > 0 && (
              <div className="space-y-2 pt-1">
                <div className="text-xs text-neutral-400 uppercase tracking-wider font-medium">Phase Breakdown</div>
                {sentiment_analysis.breakdown.map((phase, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="text-neutral-600">{phase.phase}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={sentimentVariant(phase.sentiment)}>{phase.sentiment}</Badge>
                      <span className="font-mono text-neutral-500 w-8 text-right">{Math.round(phase.score * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </SectionPanel>

        <SectionPanel title="Outcome" subtitle="Final disposition and conversion signals">
          <div className="space-y-0">
            <FieldRow label="Disposition" value={<Badge variant={outcomeVariant(outcome_detail.label)}>{outcome_detail.label}</Badge>} />
            <FieldRow label="Confidence" value={`${Math.round((outcome_detail.confidence ?? 0) * 100)}%`} />
            <FieldRow label="Conversion Probability" value={
              <Badge variant={outcome_detail.conversion_probability >= 0.7 ? 'green' : outcome_detail.conversion_probability >= 0.4 ? 'amber' : 'red'}>
                {Math.round((outcome_detail.conversion_probability ?? 0) * 100)}%
              </Badge>
            } />
            <FieldRow label="Next Stage" value={outcome_detail.next_stage} />
            <FieldRow label="Disposition Code" value={<span className="font-mono text-xs">{outcome_detail.disposition_code}</span>} />
          </div>
        </SectionPanel>

        <SectionPanel title="Follow-up Recommendation" subtitle="Suggested next actions">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Target size={14} className="text-primary-500 shrink-0" />
              <p className="text-sm text-neutral-700 leading-relaxed">{follow_up.recommendation}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-neutral-50 border border-neutral-100">
                <div className="text-xs text-neutral-400 mb-1">Priority</div>
                <Badge variant={priorityVariant(follow_up.priority)}>{follow_up.priority}</Badge>
              </div>
              <div className="p-3 rounded-lg bg-neutral-50 border border-neutral-100">
                <div className="text-xs text-neutral-400 mb-1">Channel</div>
                <Badge>{follow_up.channel}</Badge>
              </div>
            </div>
            {follow_up.scheduled_at && (
              <div className="flex items-center gap-2 text-xs text-neutral-600">
                <Calendar size={12} className="text-neutral-400" />
                Scheduled: {formatDate(follow_up.scheduled_at)}
              </div>
            )}
            {follow_up.action_items?.length > 0 && (
              <div>
                <div className="text-xs text-neutral-400 uppercase tracking-wider font-medium mb-2">Action Items</div>
                <ul className="space-y-1.5">
                  {follow_up.action_items.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-xs text-neutral-700">
                      <CheckCircle size={12} className="text-success-500 shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </SectionPanel>
      </div>

      {/* Full Transcript */}
      <SectionPanel
        title="Full Transcript"
        subtitle={hasTranscript ? `${detail.transcript.length} messages · ${call_metadata.channel} session log` : 'No conversational transcript recorded'}
      >
        {hasTranscript ? (
          <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
            {detail.transcript.map((line, idx) => (
              <div key={idx} className={`flex ${line.sender === 'agent' ? 'justify-end' : 'justify-start'}`}>
                <div className={`px-3 py-2 rounded-lg text-xs max-w-[85%] ${
                  line.sender === 'agent'
                    ? 'bg-primary-500 text-white rounded-br-none'
                    : 'bg-neutral-100 text-neutral-800 rounded-bl-none'
                }`}>
                  <div className="font-semibold mb-0.5 opacity-75 capitalize">
                    {line.sender === 'agent' ? (call_metadata.agent || 'TARA AI') : customer.name}
                  </div>
                  {line.text}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-neutral-400">
            <FileText size={28} className="mb-3 opacity-40" />
            <p className="text-sm font-medium text-neutral-600">No transcript available</p>
            <p className="text-xs mt-1 text-center max-w-sm">
              {call_metadata.channel === 'Email'
                ? 'Email interactions capture delivery metrics but not a conversational transcript.'
                : call_metadata.channel === 'SMS'
                  ? 'SMS interactions show message content in the session log when available.'
                  : 'No transcript was recorded for this session.'}
            </p>
          </div>
        )}
      </SectionPanel>

      {/* Explainability Notes */}
      <SectionPanel
        title="Generated Explainability Notes"
        subtitle="ML feature attributions driving TARA's decisions for this interaction"
        actions={
          <span className="text-xs text-neutral-400 flex items-center gap-1">
            <Lightbulb size={12} /> Layer 4 XAI
          </span>
        }
      >
        {explainability_notes?.length > 0 ? (
          <div className="space-y-3">
            {explainability_notes.map(note => (
              <ExplainNote key={note.code} {...note} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-neutral-400">
            <AlertCircle size={24} className="mb-2 opacity-40" />
            <p className="text-sm">No explainability notes generated for this interaction.</p>
          </div>
        )}
      </SectionPanel>
    </div>
  );
}
