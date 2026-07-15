import React, { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Activity, Mic, TrendingUp, Zap, Clock } from 'lucide-react';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';
import SectionPanel from '../components/ui/SectionPanel';
import { FieldRow } from '../components/ui/SectionPanel';
import { useCampaigns } from '../context/CampaignContext';

// ─── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Formats elapsed time from startedAt epoch ms into MM:SS string.
 * @param {number} startedAt
 */
function formatDuration(startedAt) {
  const secs = Math.floor((Date.now() - startedAt) / 1000);
  const m = Math.floor(secs / 60).toString().padStart(2, '0');
  const s = (secs % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

// ─── Live Pulse Indicator ──────────────────────────────────────────────────────

function LivePulse() {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success-500" />
    </span>
  );
}

// ─── Call Card ─────────────────────────────────────────────────────────────────

function CallRow({ call, isSelected, onClick }) {
  const sentimentColor = call.sentiment === 'Positive' ? 'green' : call.sentiment === 'Negative' ? 'red' : 'amber';

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border cursor-pointer transition-all duration-150 ${
        isSelected
          ? 'border-primary-400 bg-primary-50 shadow-sm'
          : 'border-neutral-200 bg-white hover:border-primary-200 hover:bg-neutral-50'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2.5 rounded-full bg-success-100 text-success-600 shrink-0">
            <Phone size={14} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-neutral-800 truncate">{call.customer_name}</div>
            <div className="text-xs text-neutral-400 font-mono mt-0.5">{call.phone}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <LivePulse />
          {/* Re-render duration via parent tick */}
          <span className="text-xs font-mono text-success-600 font-semibold">{formatDuration(call.startedAt)}</span>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <div className="col-span-2">
          <span className="text-neutral-400">Campaign: </span>
          <span className="text-neutral-700 font-medium">{call.campaign}</span>
        </div>
        <div>
          <span className="text-neutral-400">Stage: </span>
          <Badge variant="blue">{call.stage}</Badge>
        </div>
        <div>
          <span className="text-neutral-400">Sentiment: </span>
          <Badge variant={sentimentColor}>{call.sentiment}</Badge>
        </div>
      </div>
    </div>
  );
}

// ─── Detail Panel ──────────────────────────────────────────────────────────────

function DetailPanel({ call, onEndCall }) {
  const transcriptEndRef = useRef(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [call.transcript]);

  const sentimentColor = call.sentiment === 'Positive' ? 'green' : call.sentiment === 'Negative' ? 'red' : 'amber';

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header bar */}
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-full bg-success-100 text-success-600 animate-pulse">
            <Mic size={16} />
          </div>
          <div>
            <div className="text-sm font-bold text-neutral-800">{call.customer_name}</div>
            <div className="text-xs text-neutral-400 font-mono">{call.phone} · {call.campaign}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <LivePulse />
          <Badge variant="green">LIVE</Badge>
          <button
            onClick={() => onEndCall(call.call_id)}
            className="btn btn-danger btn-sm ml-1"
            title="End Call"
          >
            <PhoneOff size={12} /> End
          </button>
        </div>
      </div>

      {/* AI Insights */}
      <SectionPanel title="Real-time AI Insights" subtitle="Live intelligence from TARA Voice AI">
        <div className="space-y-0">
          <FieldRow label="Current Stage" value={<Badge variant="blue">{call.stage}</Badge>} />
          <FieldRow label="Sentiment" value={<Badge variant={sentimentColor}>{call.sentiment}</Badge>} />
          <FieldRow label="Detected Intent" value={call.intent} />
          <FieldRow label="Recommended Action" value={
            <span className="text-right text-xs font-medium text-primary-600">{call.next_action}</span>
          } />
          <FieldRow label="Agent" value={call.agent} />
          <FieldRow label="Status" value={<Badge variant="green">{call.status}</Badge>} />
        </div>
      </SectionPanel>

      {/* Live Transcript */}
      <div className="card flex flex-col flex-1 overflow-hidden">
        <div className="card-header">
          <div>
            <h3 className="text-sm font-semibold text-neutral-800">Live Transcript</h3>
            <p className="text-xs text-neutral-500 mt-0.5">Updating in real-time</p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-success-600 font-medium">
            <Activity size={12} className="animate-pulse" />
            LIVE
          </div>
        </div>
        <div className="card-body flex-1 overflow-y-auto space-y-3 max-h-72">
          {call.transcript.length === 0 ? (
            <p className="text-xs text-neutral-400 text-center py-8">Connecting...</p>
          ) : (
            call.transcript.map((line, idx) => (
              <div key={idx} className={`flex ${line.sender === 'agent' ? 'justify-end' : 'justify-start'}`}>
                <div className={`px-3 py-2 rounded-lg text-xs max-w-[85%] ${
                  line.sender === 'agent'
                    ? 'bg-primary-500 text-white rounded-br-none'
                    : 'bg-neutral-100 text-neutral-800 rounded-bl-none'
                }`}>
                  <div className="font-semibold mb-0.5 opacity-75 capitalize">
                    {line.sender === 'agent' ? 'TARA AI' : 'Customer'}
                  </div>
                  {line.text}
                </div>
              </div>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function LiveContactMonitor() {
  const { activeCalls, endCall, dripTranscriptLine } = useCampaigns();
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [, setTick] = useState(0);

  // Auto-select first call when calls arrive
  useEffect(() => {
    if (activeCalls.length > 0 && !activeCalls.find(c => c.call_id === selectedCallId)) {
      setSelectedCallId(activeCalls[0].call_id);
    }
    if (activeCalls.length === 0) setSelectedCallId(null);
  }, [activeCalls, selectedCallId]);

  // Tick every second to refresh durations
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  // Drip transcript lines for each call on different offsets
  useEffect(() => {
    if (activeCalls.length === 0) return;
    const timers = activeCalls.map((call, i) =>
      setInterval(() => dripTranscriptLine(call.call_id), 4000 + i * 1100)
    );
    return () => timers.forEach(clearInterval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCalls.length]);

  const selectedCall = activeCalls.find(c => c.call_id === selectedCallId);

  const avgDurationMs = activeCalls.length > 0
    ? activeCalls.reduce((s, c) => s + (Date.now() - c.startedAt), 0) / activeCalls.length
    : 0;
  const avgMinutes = Math.floor(avgDurationMs / 60000);

  return (
    <div className="space-y-4 flex flex-col">
      <PageHeader
        title="Live Contact Monitor"
        subtitle="Real-time view of all active TARA Voice AI sessions."
        actions={
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success-50 border border-success-200 text-success-700 text-xs font-semibold dark:bg-success-500/15 dark:border-success-500/30 dark:text-success-400">
            <LivePulse />
            {activeCalls.length} Active Call{activeCalls.length !== 1 ? 's' : ''}
          </div>
        }
      />

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-success-50 text-success-500"><Phone size={16} /></div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Active Calls</div>
            <div className="text-xl font-bold text-neutral-800">{activeCalls.length}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-50 text-primary-500"><TrendingUp size={16} /></div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Avg Duration</div>
            <div className="text-xl font-bold text-neutral-800">{avgMinutes}m</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-warning-50 text-warning-500"><Zap size={16} /></div>
          <div>
            <div className="text-xs text-neutral-400 uppercase tracking-wide font-medium">Positive</div>
            <div className="text-xl font-bold text-neutral-800">
              {activeCalls.filter(c => c.sentiment === 'Positive').length}/{activeCalls.length || '—'}
            </div>
          </div>
        </div>
      </div>

      {/* Main split: call list + detail panel */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: call list */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
            Active Sessions
          </div>
          {activeCalls.length === 0 ? (
            <div className="card p-10 text-center text-neutral-400">
              <PhoneOff size={24} className="mx-auto mb-3 opacity-40" />
              <p className="font-semibold text-neutral-600 text-sm">No active calls</p>
              <p className="text-xs mt-1">
                Go to <strong>Outreach Programs</strong>, open a campaign, upload contacts, and click <em>Launch Calls</em>.
              </p>
            </div>
          ) : (
            activeCalls.map(call => (
              <CallRow
                key={call.call_id}
                call={call}
                isSelected={selectedCallId === call.call_id}
                onClick={() => setSelectedCallId(call.call_id)}
              />
            ))
          )}
        </div>

        {/* Right: detail panel */}
        <div className="lg:col-span-3">
          {selectedCall ? (
            <DetailPanel call={selectedCall} onEndCall={endCall} />
          ) : (
            <div className="card h-full flex flex-col items-center justify-center text-center text-neutral-400 p-10">
              <Clock size={28} className="mb-3 opacity-40" />
              <p className="font-semibold text-neutral-600">No Call Selected</p>
              <p className="text-xs mt-1">Select an active session on the left to monitor the live transcript and AI insights.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
