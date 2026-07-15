import React, { createContext, useContext, useState, useCallback } from 'react';
import { DUMMY_CAMPAIGNS } from '../api/dummyData';
import { DUMMY_INTERACTION_HISTORY } from '../api/interactionData';

/**
 * CampaignContext
 * ─────────────────
 * Single source of truth for campaigns and active monitor calls.
 * No backend required — all state is in-memory, shared via React Context.
 *
 * Provides:
 *  - campaigns          list of all campaign objects
 *  - addCampaign        create a new campaign
 *  - addContactsToCampaign  upload parsed CSV contacts to a campaign
 *  - activeCalls        list of currently "ringing" call objects for the monitor
 *  - launchCalls        turn a campaign's contacts into active monitor calls
 *  - endCall            remove a call from the active list (archives to interaction history)
 *  - completedInteractions  all finished outreach sessions
 *  - getInteractionById lookup a completed interaction by id
 */

const CampaignContext = createContext(null);

function formatDurationMs(ms) {
  const secs = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/** Turn a live monitor call into a completed interaction record. */
function buildCompletedInteraction(call, durationMs) {
  const stage = call.stage || 'Closing';
  let outcome = 'Engaged';
  if (stage === 'Closing' && call.sentiment === 'Positive') outcome = 'Interested';
  else if (call.sentiment === 'Negative') outcome = 'Declined';
  else if (stage === 'Introduction') outcome = 'Callback Scheduled';

  return {
    interaction_id: call.call_id.replace(/^live-/, 'int-'),
    customer_name: call.customer_name,
    customer_id: null,
    phone: call.phone,
    email: call.email,
    date: new Date().toISOString(),
    channel: 'Voice',
    campaign: call.campaign,
    campaign_id: call.campaign_id,
    duration: formatDurationMs(durationMs),
    duration_seconds: Math.floor(durationMs / 1000),
    outcome,
    sentiment: call.sentiment || 'Neutral',
    status: 'completed',
    agent: call.agent || 'TARA Voice AI',
    intent: call.intent || '—',
    summary: `Voice session for ${call.campaign} ended — ${outcome.toLowerCase()}.`,
    reasoning: 'Archived from Live Contact Monitor session.',
    transcript: call.transcript || [],
  };
}

/** Internal: generate sequential transcript lines for a simulated call. */
const AGENT_OPENERS = [
  (name, product) => `Namaste ${name} ji, this is TARA from SBI. I'm calling about a personalised ${product} offer tailored for you.`,
  (name, product) => `Hello ${name}, TARA here from SBI. We have an exclusive ${product} offer available for you today.`,
  (name, product) => `Good day ${name}! This is TARA, your SBI AI assistant. I'm reaching out about our ${product} programme.`,
];
const USER_RESPONSES = [
  'Yes, tell me more about this.',
  'Okay, go ahead.',
  'I am listening.',
  'Sure, what is the offer?',
];
const STAGES = ['Introduction', 'Needs Discovery', 'Product Pitch', 'Objection Handling', 'Closing'];
const SENTIMENTS = ['Neutral', 'Positive', 'Positive', 'Positive', 'Neutral'];

/**
 * Build an initial call object from a contact row and campaign metadata.
 * @param {object} contact - { name, phone, email, ... }
 * @param {object} campaign - campaign object
 * @param {number} index - position in the contact list (affects opener variation)
 */
function buildActiveCall(contact, campaign, index) {
  const opener = AGENT_OPENERS[index % AGENT_OPENERS.length](contact.name, campaign.product);
  const userReply = USER_RESPONSES[index % USER_RESPONSES.length];
  return {
    call_id: `live-${campaign.campaign_id}-${Date.now()}-${index}`,
    customer_name: contact.name,
    phone: contact.phone || contact.mobile || '—',
    email: contact.email || '—',
    campaign: campaign.name,
    campaign_id: campaign.campaign_id,
    stage: STAGES[0],
    agent: 'TARA Voice AI',
    status: 'Connected',
    startedAt: Date.now() - Math.floor(Math.random() * 30000), // stagger start times
    sentiment: SENTIMENTS[0],
    intent: 'Listening to offer',
    next_action: 'Introduce product benefits',
    transcript: [
      { sender: 'agent', text: opener },
      { sender: 'user', text: userReply },
    ],
    // Follow-up lines dripped by the monitor
    pendingLines: [
      { sender: 'agent', text: `Based on your profile, you qualify for our ${campaign.product} with excellent benefits.` },
      { sender: 'user', text: 'What are the key benefits?' },
      { sender: 'agent', text: 'You get competitive rates, flexible terms, and instant approval. Would you like me to send the details to your WhatsApp?' },
      { sender: 'user', text: 'Yes, please send it over.' },
      { sender: 'agent', text: 'Done! I have triggered the application link on WhatsApp. Thank you for your time.' },
    ],
  };
}

export function CampaignProvider({ children }) {
  const [campaigns, setCampaigns] = useState(DUMMY_CAMPAIGNS);
  const [activeCalls, setActiveCalls] = useState([]);
  const [completedInteractions, setCompletedInteractions] = useState(DUMMY_INTERACTION_HISTORY);

  /** Add a brand-new campaign created via the modal form. */
  const addCampaign = useCallback((formData) => {
    const newCampaign = {
      campaign_id: `cmp-${Date.now()}`,
      name: formData.name,
      product: formData.product,
      target_audience: formData.target_audience,
      channel: formData.channel,
      status: 'Draft',
      start_date: formData.start_date,
      end_date: formData.end_date,
      qualified_leads: 0,
      conversion_rate: 0.0,
      assigned_leads: [],
    };
    setCampaigns(prev => [...prev, newCampaign]);
    return newCampaign;
  }, []);

  /**
   * Attach parsed CSV contacts to a campaign.
   * @param {string} campaignId
   * @param {Array<{name, phone, email}>} contacts
   */
  const addContactsToCampaign = useCallback((campaignId, contacts) => {
    setCampaigns(prev =>
      prev.map(c => {
        if (c.campaign_id !== campaignId) return c;
        const newLeads = contacts.map((ct, i) => ({
          id: `csv-${campaignId}-${i}`,
          name: ct.name || ct.Name || ct.full_name || `Contact ${i + 1}`,
          status: 'Pending',
          contact: ct.phone || ct.mobile || ct.Phone || ct.email || ct.Email || '—',
          score: Math.floor(Math.random() * 30) + 60,
          phone: ct.phone || ct.mobile || ct.Phone || '—',
          email: ct.email || ct.Email || '—',
        }));
        return {
          ...c,
          status: 'Active',
          qualified_leads: c.qualified_leads + contacts.length,
          assigned_leads: [...(c.assigned_leads || []), ...newLeads],
        };
      })
    );
  }, []);

  /**
   * Turn a campaign's assigned_leads into active live calls visible on the monitor.
   * @param {string} campaignId
   */
  const launchCalls = useCallback((campaignId) => {
    const campaign = campaigns.find(c => c.campaign_id === campaignId);
    if (!campaign) return;

    const leads = campaign.assigned_leads || [];
    const newCalls = leads
      .filter(lead => lead.status !== 'Converted') // don't re-call converted leads
      .map((lead, i) => buildActiveCall(lead, campaign, i));

    setActiveCalls(prev => {
      // Remove any existing calls for this campaign before re-launching
      const filtered = prev.filter(ac => ac.campaign_id !== campaignId);
      return [...filtered, ...newCalls];
    });

    // Mark the campaign as Active
    setCampaigns(prev =>
      prev.map(c => c.campaign_id === campaignId ? { ...c, status: 'Active' } : c)
    );
  }, [campaigns]);

  /** Remove a call from the active monitor list and archive it to interaction history. */
  const endCall = useCallback((callId) => {
    setActiveCalls(prev => {
      const call = prev.find(c => c.call_id === callId);
      if (call) {
        const durationMs = Date.now() - call.startedAt;
        const record = buildCompletedInteraction(call, durationMs);
        setCompletedInteractions(h => [record, ...h]);
      }
      return prev.filter(c => c.call_id !== callId);
    });
  }, []);

  const getInteractionById = useCallback(
    (id) => completedInteractions.find(i => i.interaction_id === id),
    [completedInteractions],
  );

  /** Drip a new transcript line into a specific active call (used by the monitor). */
  const dripTranscriptLine = useCallback((callId) => {
    setActiveCalls(prev =>
      prev.map(call => {
        if (call.call_id !== callId) return call;
        const [next, ...rest] = call.pendingLines || [];
        if (!next) return call;
        const stageIdx = Math.min(
          STAGES.length - 1,
          Math.floor((call.transcript.length - 2) / 2)
        );
        return {
          ...call,
          transcript: [...call.transcript, next],
          pendingLines: rest,
          stage: STAGES[stageIdx],
          sentiment: SENTIMENTS[stageIdx],
        };
      })
    );
  }, []);

  const value = {
    campaigns,
    addCampaign,
    addContactsToCampaign,
    activeCalls,
    launchCalls,
    endCall,
    dripTranscriptLine,
    completedInteractions,
    getInteractionById,
  };

  return (
    <CampaignContext.Provider value={value}>
      {children}
    </CampaignContext.Provider>
  );
}

/** Hook to access campaign context from any page. */
export function useCampaigns() {
  const ctx = useContext(CampaignContext);
  if (!ctx) throw new Error('useCampaigns must be used within CampaignProvider');
  return ctx;
}
