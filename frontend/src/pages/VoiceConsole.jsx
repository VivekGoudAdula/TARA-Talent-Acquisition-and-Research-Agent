import React, { useState, useEffect, useRef } from 'react';
import SectionPanel, { FieldRow } from '../components/ui/SectionPanel';
import Badge from '../components/ui/Badge';
import { PageSpinner } from '../components/ui/States';
import { useEngagementPreview } from '../api/hooks';
import {
  mergeVoiceDialerLeads,
  simulateVoiceCall,
  getVoiceDemoOutcome,
} from '../api/dummyData';
import api from '../api/client';
import { Phone, PhoneOff, Mic } from 'lucide-react';

/** Set to false only when Twilio voice bridge is verified working. */
const VOICE_DEMO_MODE = import.meta.env.VITE_VOICE_DEMO !== 'false';

export default function VoiceConsole() {
  const preview = useEngagementPreview(20, 'External,Internal');
  const [activeCall, setActiveCall] = useState(null);
  const [callStatus, setCallStatus] = useState('idle'); // idle, dialing, connected, ended
  const [transcript, setTranscript] = useState([]);
  const [outcome, setOutcome] = useState(null);
  const simCleanupRef = useRef(null);

  useEffect(() => {
    return () => {
      simCleanupRef.current?.();
    };
  }, []);

  useEffect(() => {
    if (VOICE_DEMO_MODE || !activeCall || callStatus !== 'connected') return;

    const eventSource = new EventSource('/api/engagement/conversations/stream');

    eventSource.addEventListener('conversation_message', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.entity_id === activeCall.lead_id && data.channel === 'Voice') {
          setTranscript(prev => {
            const exists = prev.some(m => m.text === data.body && m.sender === (data.role === 'agent' ? 'agent' : 'user'));
            if (exists) return prev;
            return [...prev, { sender: data.role === 'agent' ? 'agent' : 'user', text: data.body }];
          });
        }
      } catch (err) {
        console.error('SSE parse error', err);
      }
    });

    eventSource.onerror = (err) => {
      console.error('SSE EventSource error', err);
    };

    return () => {
      eventSource.close();
    };
  }, [activeCall, callStatus]);

  if (preview.isLoading) return <PageSpinner />;
  const leads = mergeVoiceDialerLeads(preview.isError ? [] : preview.data);

  const startDemoCall = (lead) => {
    simCleanupRef.current?.();
    setActiveCall(lead);
    setCallStatus('dialing');
    setTranscript([]);
    setOutcome(null);

    simCleanupRef.current = simulateVoiceCall(lead, {
      onConnected: () => setCallStatus('connected'),
      onLine: (line) => setTranscript(prev => [...prev, line]),
      onComplete: (demoOutcome) => {
        setCallStatus('ended');
        setOutcome(demoOutcome);
        simCleanupRef.current = null;
      },
    });
  };

  const handleDial = async (lead) => {
    if (VOICE_DEMO_MODE) {
      startDemoCall(lead);
      return;
    }

    simCleanupRef.current?.();
    setActiveCall(lead);
    setCallStatus('dialing');
    setTranscript([]);
    setOutcome(null);

    try {
      const historyRes = await api.get(`/api/engagement/conversations/${lead.lead_id}`);
      if (historyRes.data?.messages) {
        const msgs = historyRes.data.messages.map(m => ({
          sender: m.role === 'agent' ? 'agent' : 'user',
          text: m.body,
        }));
        setTranscript(msgs);
      }
    } catch {
      console.debug('No previous conversation thread found.');
    }

    try {
      await api.get('/api/engagement/callback/trigger', {
        params: {
          phone: lead.phone_number,
          entity_id: lead.lead_id,
          entity_type: lead.profile_type || 'Internal',
        },
      });
      setCallStatus('connected');
    } catch (err) {
      console.warn('Live voice call failed — falling back to demo simulation:', err);
      startDemoCall(lead);
    }
  };

  const handleHangup = async () => {
    simCleanupRef.current?.();
    simCleanupRef.current = null;
    setCallStatus('ended');

    if (VOICE_DEMO_MODE && activeCall) {
      if (!outcome) {
        setOutcome(getVoiceDemoOutcome(activeCall));
      }
      return;
    }

    try {
      const outcomeRes = await api.get(`/api/engagement/events/${activeCall.lead_id}`);
      const voiceEvents = (outcomeRes.data || []).filter(e => e.channel === 'Voice');
      if (voiceEvents.length > 0) {
        voiceEvents.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        const latest = voiceEvents[0];
        const meta = latest.metadata || {};
        setOutcome({
          summary: latest.message_preview || 'Call completed successfully.',
          sentiment: meta.sentiment || 'Neutral-Positive',
          duration: `${meta.duration_seconds || 30}s`,
          reasoning: meta.intent ? `Customer intent classified: ${meta.intent}` : 'Normal execution',
          tool_calls: meta.agent_id || 'lending_offer_agent',
        });
      } else if (activeCall) {
        setOutcome(getVoiceDemoOutcome(activeCall));
      }
    } catch {
      if (activeCall) {
        setOutcome(getVoiceDemoOutcome(activeCall));
      }
    }
  };

  const resetWorkspace = () => {
    simCleanupRef.current?.();
    simCleanupRef.current = null;
    setCallStatus('idle');
    setActiveCall(null);
    setTranscript([]);
    setOutcome(null);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <SectionPanel
        title="Active Dialer Queue"
        subtitle={VOICE_DEMO_MODE ? 'Demo mode — scripted voice conversations' : 'Trigger live voice outreach call'}
      >
        {VOICE_DEMO_MODE && (
          <div className="mb-3 px-2.5 py-2 rounded bg-amber-50 border border-amber-100 text-xs text-amber-800">
            Voice bridge offline — using static demo transcripts and AI summaries.
          </div>
        )}
        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {leads.map((l) => (
            <div key={l.lead_id} className="p-3 border border-neutral-100 bg-white rounded flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-neutral-800">{l.full_name}</div>
                <div className="text-xs text-neutral-400 mt-0.5">{l.phone_number}</div>
                {l.recommended_product && (
                  <div className="text-[10px] text-primary-600 mt-0.5">{l.recommended_product}</div>
                )}
              </div>
              <button
                className="btn btn-primary btn-sm p-2 rounded-full"
                onClick={() => handleDial(l)}
                disabled={callStatus === 'dialing' || callStatus === 'connected'}
              >
                <Phone size={14} />
              </button>
            </div>
          ))}
        </div>
      </SectionPanel>

      <div className="md:col-span-2 space-y-6">
        {callStatus === 'idle' ? (
          <div className="card p-10 flex flex-col items-center justify-center text-center h-full text-neutral-400">
            <div className="w-12 h-12 bg-neutral-100 rounded-full flex items-center justify-center mb-4"><Mic size={20} /></div>
            <p className="font-semibold text-neutral-700">Voice Workspace Idle</p>
            <p className="text-xs mt-1">
              {VOICE_DEMO_MODE
                ? 'Select a customer to play a scripted AI voice conversation demo'
                : 'Select a customer from the queue to start dialing via the Twilio voice bridge'}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="card p-4 flex items-center justify-between bg-white border border-neutral-200">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-full ${callStatus === 'connected' ? 'bg-success-100 text-success-600 animate-pulse' : 'bg-primary-100 text-primary-600'}`}>
                  <Phone size={16} />
                </div>
                <div>
                  <div className="text-sm font-bold text-neutral-800">{activeCall?.full_name}</div>
                  <div className="text-xs text-neutral-400">
                    {VOICE_DEMO_MODE ? 'SBI Voice Agent — Demo Simulation' : 'Dialing via SBI Voice System'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {VOICE_DEMO_MODE && <Badge variant="amber">DEMO</Badge>}
                <Badge>{callStatus.toUpperCase()}</Badge>
                {callStatus !== 'ended' ? (
                  <button className="btn btn-danger btn-sm" onClick={handleHangup}>
                    <PhoneOff size={12} /> Hang Up
                  </button>
                ) : (
                  <button className="btn btn-secondary btn-sm" onClick={resetWorkspace}>
                    Close Workspace
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SectionPanel title="Live Transcript" className="h-[350px] flex flex-col">
                <div className="flex-1 overflow-y-auto space-y-3 p-1">
                  {transcript.length === 0 ? (
                    <p className="text-xs text-neutral-400 text-center py-10">
                      {callStatus === 'dialing' ? 'Ringing customer...' : 'Connecting to channel streams...'}
                    </p>
                  ) : (
                    transcript.map((t, idx) => (
                      <div key={idx} className={`p-2.5 rounded text-xs max-w-[85%] ${t.sender === 'agent' ? 'bg-primary-50 text-primary-800 ml-auto' : 'bg-neutral-100 text-neutral-800'}`}>
                        <div className="font-semibold capitalize mb-0.5">{t.sender}</div>
                        <div>{t.text}</div>
                      </div>
                    ))
                  )}
                </div>
              </SectionPanel>

              <SectionPanel title="Post-Call AI Summary">
                {!outcome ? (
                  <p className="text-xs text-neutral-400 text-center py-10">Outcome analysis will appear here after call hangs up</p>
                ) : (
                  <div className="space-y-4">
                    <FieldRow label="Sentiment" value={<Badge variant="green">{outcome.sentiment}</Badge>} />
                    <FieldRow label="Duration" value={outcome.duration} />
                    <FieldRow label="AI Action Triggered" value={<Badge variant="blue">{outcome.tool_calls}</Badge>} />
                    <div>
                      <h4 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Reasoning Analysis</h4>
                      <p className="text-xs text-neutral-700 leading-relaxed bg-neutral-50 p-2.5 rounded border border-neutral-100">{outcome.reasoning}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Call Summary</h4>
                      <p className="text-xs text-neutral-700 leading-relaxed bg-neutral-50 p-2.5 rounded border border-neutral-100">{outcome.summary}</p>
                    </div>
                  </div>
                )}
              </SectionPanel>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
