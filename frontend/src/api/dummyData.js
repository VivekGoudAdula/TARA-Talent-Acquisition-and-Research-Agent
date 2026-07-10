/** Demo / fallback data when API responses are empty or incomplete. */

const now = () => new Date().toISOString();

/** Fallback MongoDB collection counts for Dashboard KPIs & pipeline overview chart. */
export const DUMMY_PLATFORM_COUNTS = {
  customers: 1000,
  external_leads: 1000,
  customer_360_profile: 950,
  feature_store: 6243,
  lead_feature_store: 1180,
  training_dataset: 760,
  explainability_reports: 540,
  ml_model_runs: 8,
  conversion_scores: 420,
  product_recommendations: 180,
  repayment_predictions: 95,
};

export function mergePlatformCounts(apiCounts = {}) {
  const merged = { ...DUMMY_PLATFORM_COUNTS };
  Object.entries(apiCounts || {}).forEach(([key, value]) => {
    const n = Number(value);
    if (!Number.isNaN(n) && n > 0) merged[key] = n;
  });
  return merged;
}

export function buildPipelineOverviewChartData(apiCounts = {}) {
  const c = mergePlatformCounts(apiCounts);
  return [
    { name: 'Customers', value: c.customers },
    { name: 'Ext. Leads', value: c.external_leads },
    { name: '360 Profiles', value: c.customer_360_profile },
    { name: 'Feature Store', value: c.feature_store },
    { name: 'Lead FS', value: c.lead_feature_store },
    { name: 'Training', value: c.training_dataset },
    { name: 'XAI Reports', value: c.explainability_reports },
    { name: 'ML Runs', value: c.ml_model_runs },
    { name: 'Conv. Scores', value: c.conversion_scores },
    { name: 'Products', value: c.product_recommendations },
    { name: 'Repayment', value: c.repayment_predictions },
  ];
}

export const DUMMY_ML_MODELS = {
  repayment: {
    trained: true,
    algorithm: 'random_forest',
    version: '1.0.0',
    last_trained: now(),
    train_samples: 850,
    test_samples: 150,
    metrics: { accuracy: 0.91, f1: 0.87, roc_auc: 0.89 },
    feature_importance: {
      income: 0.28,
      financial_health_score: 0.22,
      digital_engagement_score: 0.18,
      credit_score: 0.16,
      savings_ratio: 0.10,
      emi_burden: 0.06,
    },
  },
  product: {
    trained: true,
    algorithm: 'Hybrid Rules + Repayment ML Ranker',
    version: '1.0.0',
    last_trained: now(),
    train_samples: 1000,
    test_samples: 200,
    metrics: { accuracy: 0.94, f1: 0.92, roc_auc: 0.96 },
    feature_importance: {
      credit_score: 0.40,
      monthly_income: 0.30,
      repayment_capacity: 0.20,
      emi_ratio: 0.10,
    },
  },
  conversion: {
    trained: true,
    algorithm: 'xgboost',
    version: '1.0.0',
    last_trained: now(),
    train_samples: 500,
    test_samples: 100,
    metrics: { accuracy: 0.82, f1: 0.78, roc_auc: 0.85 },
    feature_importance: {
      consent: 0.24,
      lead_quality_score: 0.20,
      credit_score: 0.18,
      digital_engagement_score: 0.15,
      previous_campaign_response: 0.12,
      communication_readiness: 0.11,
    },
  },
};

export function mergeMlModelInfo(apiData, dummyKey) {
  if (!apiData) {
    return {
      trained: false,
      algorithm: 'None',
      version: '1.0.0',
      last_trained: null,
      train_samples: 0,
      test_samples: 0,
      metrics: { accuracy: 0, f1: 0, roc_auc: 0 },
      feature_importance: {},
    };
  }

  const importance = {};
  Object.entries(apiData.feature_importance || {}).forEach(([k, v]) => {
    if (v == null || v === 0) return;
    const normalized = String(k)
      .replace(/^(num|cat)_/i, '')
      .replace(/^(num|cat)\s+/i, '')
      .replace(/_/g, ' ')
      .trim();
    importance[normalized] = v;
  });

  return {
    trained: apiData.trained ?? false,
    algorithm: apiData.algorithm || 'Unknown',
    version: apiData.version || '1.0.0',
    last_trained: apiData.last_trained || null,
    train_samples: apiData.train_samples || 0,
    test_samples: apiData.test_samples || 0,
    metrics: {
      accuracy: apiData.metrics?.accuracy || 0,
      f1: apiData.metrics?.f1 || 0,
      roc_auc: apiData.metrics?.roc_auc || 0,
    },
    feature_importance: importance,
  };
}

export function buildDummyExplainReport(customer) {
  const name = customer?.full_name || customer?.name || 'Customer';
  const isExternal = customer?.profile_type === 'External' || customer?.isExternal === true;
  const product = customer?.recommended_product || customer?.recommended_campaign || (isExternal ? 'Gold Credit Card' : 'Personal Loan');
  const repayment = customer?.repayment_label || customer?.repayment_capacity || (isExternal ? 'Medium' : 'High');
  const convRaw = customer?.conversion_probability;
  const convProb = convRaw != null
    ? (convRaw <= 1 ? convRaw : convRaw / 100)
    : (isExternal ? 0.68 : 0.72);

  const summary = isExternal
    ? `${name} is an enriched external lead with ${repayment.toLowerCase()} repayment indicators and a `
      + `${Math.round(convProb * 100)}% estimated conversion probability for ${product}. `
      + 'The explainability layer combined lead enrichment, credit band signals, channel responsiveness, '
      + 'and fraud-screening outcomes before ranking this product for the next outreach cycle.'
    : `${name} demonstrates a ${repayment} repayment profile with strong eligibility for ${product}. `
      + 'The ML stack evaluated income stability, digital engagement, and historical repayment behaviour '
      + 'before ranking this product as the top cross-sell opportunity.';

  return {
    report_id: 'demo-report',
    customer_id: customer?.customer_id || customer?.entity_id || customer?.id,
    profile_type: isExternal ? 'External' : 'Internal',
    repayment_prediction: repayment,
    recommended_product: product,
    conversion_probability: convProb,
    created_at: now(),
    is_demo: true,
    narrative: summary,
    explanation: {
      summary,
      repayment_explanation: isExternal
        ? `Repayment capacity is assessed as ${repayment} based on credit score band, estimated debt capacity, `
          + 'and income confidence from the external enrichment pipeline.'
        : `Repayment capacity is assessed as ${repayment} based on cash-flow indicators, `
          + 'EMI burden relative to income, and observed savings behaviour in the Customer 360 profile.',
      product_explanation: `${product} is recommended because the ${isExternal ? 'lead' : 'customer'} meets eligibility thresholds `
        + 'for income, credit quality, and relationship depth while maintaining acceptable debt-service ratios.',
      conversion_explanation: `Estimated conversion probability is ${Math.round(convProb * 100)}% for the next personalised outreach cycle, driven by engagement score and prior channel responsiveness.`,
      confidence_summary: isExternal
        ? 'Overall model confidence is Medium-High for conversion; Medium for repayment on external leads.'
        : 'Overall model confidence is High for repayment and product fit; Medium-High for conversion.',
    },
    reason_codes: isExternal
      ? [
          { code: 1, feature: 'Lead Enrichment', explanation: 'Profile completed with KYC and income verification signals.' },
          { code: 2, feature: 'Credit Band', explanation: 'Credit score band supports preferred product tier eligibility.' },
          { code: 3, feature: 'Channel Fit', explanation: 'Best contact channel aligns with historical lead response patterns.' },
          { code: 4, feature: 'Product Fit', explanation: `${product} matches segment rules and lead quality score.` },
        ]
      : [
          { code: 1, feature: 'Income Stability', explanation: 'Monthly income supports current EMI obligations with buffer.' },
          { code: 2, feature: 'Digital Engagement', explanation: 'Active mobile banking usage indicates strong adoption.' },
          { code: 3, feature: 'Credit Quality', explanation: 'Credit score band aligns with preferred product tier.' },
          { code: 4, feature: 'Product Fit', explanation: `${product} matches segment rules and repayment tier.` },
        ],
  };
}

export const DUMMY_ENGAGEMENT_CHANNELS = {
  channels: [
    { channel: 'voice', status: 'Active' },
    { channel: 'whatsapp', status: 'Active' },
    { channel: 'sms', status: 'Active' },
    { channel: 'email', status: 'Active' },
  ],
};

export const DUMMY_ENGAGEMENT_LEADS = [
  {
    lead_id: 'demo-lead-001',
    full_name: 'Priya Nair',
    phone_number: '9876543210',
    email: 'priya.nair@example.com',
    profile_type: 'Internal',
    conversion_probability: 0.78,
    recommended_product: 'Personal Loan',
    repayment_capacity: 'High',
  },
  {
    lead_id: 'demo-lead-002',
    full_name: 'Rahul Sharma',
    phone_number: '9123456780',
    email: 'rahul.sharma@example.com',
    profile_type: 'External',
    conversion_probability: 0.65,
    recommended_product: 'Gold Credit Card',
    repayment_capacity: 'Medium',
  },
  {
    lead_id: 'demo-lead-003',
    full_name: 'Ananya Iyer',
    phone_number: '9988776655',
    email: 'ananya.iyer@example.com',
    profile_type: 'Internal',
    conversion_probability: 0.82,
    recommended_product: 'Premium Savings Plus',
    repayment_capacity: 'Very High',
  },
  {
    lead_id: 'demo-lead-004',
    full_name: 'Vikram Patel',
    phone_number: '9012345678',
    email: 'vikram.patel@example.com',
    profile_type: 'External',
    conversion_probability: 0.54,
    recommended_product: 'Digital Savings Account',
    repayment_capacity: 'Medium',
  },
  {
    lead_id: 'demo-lead-005',
    full_name: 'Meera Krishnan',
    phone_number: '9765432109',
    email: 'meera.k@example.com',
    profile_type: 'Internal',
    conversion_probability: 0.71,
    recommended_product: 'Recurring Deposit',
    repayment_capacity: 'High',
  },
];

export const DUMMY_HANDOFFS = [
  {
    customer_name: 'Priya Nair',
    status: 'pending',
    assigned_rm_name: 'Rajesh Menon',
    status_notes: 'High-value internal customer — product discussion scheduled',
  },
  {
    customer_name: 'Ananya Iyer',
    status: 'in_progress',
    assigned_rm_name: 'Sneha Kapoor',
    status_notes: 'Premium savings cross-sell in progress',
  },
  {
    customer_name: 'Rahul Sharma',
    status: 'pending',
    assigned_rm_name: null,
    status_notes: 'External lead qualified — awaiting RM assignment',
  },
];

export function mergeEngagementChannels(apiData) {
  const channels = apiData?.channels?.length ? apiData.channels : DUMMY_ENGAGEMENT_CHANNELS.channels;
  return { ...(apiData || {}), channels };
}

export function mergeEngagementLeads(apiLeads) {
  return Array.isArray(apiLeads) ? apiLeads : [];
}

export function mergeHandoffQueue(apiHandoffs) {
  return Array.isArray(apiHandoffs) ? apiHandoffs : [];
}

/** Scripted voice-agent demo for Voice Console when Twilio bridge is unavailable. */
export const DUMMY_VOICE_TRANSCRIPTS = {
  'demo-lead-001': [
    { sender: 'agent', text: 'Namaste Priya ji, this is Raj from SBI. I am calling regarding a pre-approved Personal Loan offer tailored for you.', delayMs: 1200 },
    { sender: 'user', text: 'Yes, I was looking at loan options recently.', delayMs: 2800 },
    { sender: 'agent', text: 'Great. Based on your profile, you are eligible for up to ₹8.5 lakhs at 10.9% interest with flexible EMI options.', delayMs: 3200 },
    { sender: 'user', text: 'What documents would I need?', delayMs: 2400 },
    { sender: 'agent', text: 'Just your Aadhaar, PAN, and last three months salary slips. I can send a WhatsApp link to complete the application in five minutes.', delayMs: 3600 },
    { sender: 'user', text: 'Please send the link. I will review tonight.', delayMs: 2200 },
    { sender: 'agent', text: 'Done. I have triggered the application link on WhatsApp. Thank you Priya ji, have a good day.', delayMs: 2800 },
  ],
  'demo-lead-002': [
    { sender: 'agent', text: 'Hello Rahul, Raj here from SBI. We have a Gold Credit Card offer with zero annual fee for the first year.', delayMs: 1200 },
    { sender: 'user', text: 'I already have two credit cards.', delayMs: 2000 },
    { sender: 'agent', text: 'Understood. This card offers 5X reward points on dining and fuel, plus lounge access — it complements existing cards well.', delayMs: 3400 },
    { sender: 'user', text: 'What is the credit limit?', delayMs: 1800 },
    { sender: 'agent', text: 'Your indicative limit is ₹2.5 lakhs based on your credit profile. Shall I email the detailed benefits?', delayMs: 3000 },
    { sender: 'user', text: 'Yes, email me. I will decide this weekend.', delayMs: 2400 },
    { sender: 'agent', text: 'Email sent. I have noted your interest for follow-up on Monday.', delayMs: 2200 },
  ],
  'demo-lead-003': [
    { sender: 'agent', text: 'Good afternoon Ananya ji, calling from SBI about your Premium Savings Plus upgrade eligibility.', delayMs: 1200 },
    { sender: 'user', text: 'I have been a customer for ten years.', delayMs: 2000 },
    { sender: 'agent', text: 'Exactly — loyal customers like you qualify for 7.1% interest on balances above ₹1 lakh, with free locker for one year.', delayMs: 3400 },
    { sender: 'user', text: 'That sounds good. Can I upgrade online?', delayMs: 2200 },
    { sender: 'agent', text: 'Yes, via YONO app under Products → Savings Upgrade. I can also schedule a branch visit if you prefer.', delayMs: 3200 },
    { sender: 'user', text: 'I will try the app first. Thank you.', delayMs: 2000 },
    { sender: 'agent', text: 'Wonderful. Upgrade link is on its way via SMS. Thank you for banking with SBI.', delayMs: 2400 },
  ],
  'demo-lead-004': [
    { sender: 'agent', text: 'Hello Vikram, this is SBI calling about opening a Digital Savings Account with instant video KYC.', delayMs: 1200 },
    { sender: 'user', text: 'How long does KYC take?', delayMs: 1800 },
    { sender: 'agent', text: 'Video KYC takes about eight minutes. Account is active same day with virtual debit card.', delayMs: 3000 },
    { sender: 'user', text: 'I am busy right now.', delayMs: 1600 },
    { sender: 'agent', text: 'No problem. I will send a callback link on WhatsApp — you can pick a convenient slot.', delayMs: 2800 },
    { sender: 'user', text: 'Okay, send it.', delayMs: 1400 },
    { sender: 'agent', text: 'Link sent. We will follow up tomorrow morning. Have a good day Vikram.', delayMs: 2200 },
  ],
  'demo-lead-005': [
    { sender: 'agent', text: 'Namaste Meera ji, Raj from SBI. You have a pre-qualified Recurring Deposit offer at 7.4% for 24 months.', delayMs: 1200 },
    { sender: 'user', text: 'What is the minimum amount?', delayMs: 1800 },
    { sender: 'agent', text: 'Minimum ₹1,000 per month. Based on your savings pattern, ₹5,000 monthly would build ₹1.3 lakhs with interest.', delayMs: 3400 },
    { sender: 'user', text: 'Can I start with ₹2,000?', delayMs: 1800 },
    { sender: 'agent', text: 'Absolutely. I will set up the RD application with ₹2,000 monthly debit from your savings account.', delayMs: 3000 },
    { sender: 'user', text: 'Go ahead please.', delayMs: 1600 },
    { sender: 'agent', text: 'RD mandate initiated. Confirmation SMS will arrive shortly. Thank you Meera ji.', delayMs: 2400 },
  ],
};

export const DUMMY_VOICE_OUTCOMES = {
  'demo-lead-001': {
    summary: 'Customer interested in Personal Loan. WhatsApp application link sent. Follow-up scheduled.',
    sentiment: 'Positive',
    duration: '2m 14s',
    reasoning: 'High conversion intent detected. Customer asked about documentation — strong buying signal. ML score 78% confirmed.',
    tool_calls: 'send_whatsapp_link, log_lead_intent',
  },
  'demo-lead-002': {
    summary: 'Gold Credit Card benefits emailed. Customer will decide over the weekend.',
    sentiment: 'Neutral-Positive',
    duration: '1m 52s',
    reasoning: 'Initial objection (existing cards) handled. Customer requested email — nurture track activated.',
    tool_calls: 'send_email, schedule_followup',
  },
  'demo-lead-003': {
    summary: 'Premium Savings Plus upgrade discussed. Customer will self-serve via YONO app.',
    sentiment: 'Positive',
    duration: '1m 48s',
    reasoning: 'Long-tenure customer with high loyalty score. Self-service path preferred — SMS upgrade link sent.',
    tool_calls: 'send_sms, update_crm',
  },
  'demo-lead-004': {
    summary: 'Digital account opening deferred. WhatsApp callback link sent for video KYC scheduling.',
    sentiment: 'Neutral',
    duration: '1m 22s',
    reasoning: 'Timing objection — callback scheduled. Lead remains warm with 54% conversion probability.',
    tool_calls: 'send_whatsapp_link, schedule_callback',
  },
  'demo-lead-005': {
    summary: 'Recurring Deposit mandate initiated at ₹2,000/month for 24 months.',
    sentiment: 'Positive',
    duration: '1m 56s',
    reasoning: 'Customer accepted RD offer with modified amount. Auto-debit mandate created successfully.',
    tool_calls: 'create_rd_mandate, send_sms_confirmation',
  },
};

const DEFAULT_VOICE_TRANSCRIPT = [
  { sender: 'agent', text: 'Hello, this is Raj from SBI. I am calling with a personalised banking offer for you.', delayMs: 1200 },
  { sender: 'user', text: 'Yes, please go ahead.', delayMs: 2000 },
  { sender: 'agent', text: 'Based on your profile, we have a tailored product recommendation. Would you like me to share the details?', delayMs: 3000 },
  { sender: 'user', text: 'Sure, tell me more.', delayMs: 1800 },
  { sender: 'agent', text: 'I have sent the details to your registered mobile number. Thank you for your time.', delayMs: 2800 },
];

const DEFAULT_VOICE_OUTCOME = {
  summary: 'Demo call completed. Customer engaged with the offer.',
  sentiment: 'Neutral-Positive',
  duration: '1m 30s',
  reasoning: 'Simulated voice session — live Twilio bridge unavailable.',
  tool_calls: 'lending_offer_agent',
};

export function getVoiceDemoTranscript(lead) {
  const id = lead?.lead_id || '';
  const scripted = DUMMY_VOICE_TRANSCRIPTS[id];
  if (scripted) return scripted;
  const name = (lead?.full_name || 'Customer').split(' ')[0];
  const product = lead?.recommended_product || 'Personal Loan';
  return DEFAULT_VOICE_TRANSCRIPT.map((line, idx) => {
    if (idx === 0 && line.sender === 'agent') {
      return { ...line, text: `Hello ${name}, this is Raj from SBI. I am calling about your ${product} eligibility.` };
    }
    return { ...line };
  });
}

export function getVoiceDemoOutcome(lead) {
  const id = lead?.lead_id || '';
  return DUMMY_VOICE_OUTCOMES[id] || {
    ...DEFAULT_VOICE_OUTCOME,
    summary: `${lead?.full_name || 'Customer'} — ${lead?.recommended_product || 'product'} outreach completed (demo).`,
    reasoning: `Demo simulation for ${lead?.profile_type || 'lead'} profile. Conversion probability ${Math.round((lead?.conversion_probability || 0.6) * 100)}%.`,
  };
}

/**
 * Play a scripted voice call in the UI. Returns a cleanup function to cancel timers.
 */
export function simulateVoiceCall(lead, { onLine, onConnected, onComplete }) {
  const script = getVoiceDemoTranscript(lead);
  const timers = [];
  let cancelled = false;

  const connectTimer = setTimeout(() => {
    if (cancelled) return;
    onConnected?.();
  }, 1800);
  timers.push(connectTimer);

  let offset = 2200;
  script.forEach((line) => {
    const t = setTimeout(() => {
      if (cancelled) return;
      onLine?.({ sender: line.sender, text: line.text });
    }, offset);
    timers.push(t);
    offset += line.delayMs || 2500;
  });

  const doneTimer = setTimeout(() => {
    if (cancelled) return;
    onComplete?.(getVoiceDemoOutcome(lead));
  }, offset + 400);
  timers.push(doneTimer);

  return () => {
    cancelled = true;
    timers.forEach(clearTimeout);
  };
}

export function mergeVoiceDialerLeads(apiLeads) {
  return mergeEngagementLeads(apiLeads);
}

const DEMO_STEP_MS = {
  external_enrich: 2800,
  external_analytics: 2400,
  external_intelligence: 3100,
  internal_build_all: 4200,
  behaviour_summary: 1800,
  ml_dataset: 1600,
  repayment_train: 3200,
  conversion_train: 3800,
  scoring_persist: 2200,
  explainability: 2800,
};

const DEMO_ANIM_MS = {
  external_enrich: 900,
  external_analytics: 800,
  external_intelligence: 900,
  internal_build_all: 1400,
  behaviour_summary: 700,
  ml_dataset: 600,
  repayment_train: 1000,
  conversion_train: 1100,
  scoring_persist: 800,
  explainability: 900,
};

function demoStepDetail(step, limitInternal, limitExternal) {
  const details = {
    external_enrich: `enriched=${limitExternal}`,
    external_analytics: `analytics=${limitExternal}`,
    external_intelligence: `intelligence=${limitExternal}`,
    internal_build_all: `completed=${limitInternal} failed=0`,
    behaviour_summary: `profiles_processed=${limitInternal + limitExternal}`,
    ml_dataset: `records=${limitInternal + limitExternal}`,
    repayment_train: 'best=random_forest',
    conversion_train: 'best=xgboost',
    scoring_persist: `scored=${limitInternal + limitExternal}`,
    explainability: `reports=${limitInternal}`,
  };
  return details[step] || 'ok';
}

export function buildDemoPipelineStepNames(target, trainModels = true) {
  const steps = [];
  if (target === 'external' || target === 'both') {
    steps.push('external_enrich', 'external_analytics', 'external_intelligence');
  }
  if (target === 'internal' || target === 'both') {
    steps.push('internal_build_all');
  }
  steps.push('behaviour_summary');
  if (trainModels) {
    steps.push('ml_dataset', 'repayment_train');
    if (target === 'external' || target === 'both') {
      steps.push('conversion_train');
    }
    steps.push('scoring_persist');
  }
  steps.push('explainability');
  return steps;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Animate a demo pipeline run for the Dashboard control panel.
 * Calls onProgress({ steps, current_step, is_running }) after each transition.
 */
export async function simulateDemoPipeline({
  target = 'both',
  limitInternal = 5,
  limitExternal = 5,
  trainModels = true,
  onProgress,
}) {
  const names = buildDemoPipelineStepNames(target, trainModels);
  let steps = names.map(step => ({
    step,
    status: 'pending',
    detail: null,
    duration_ms: 0,
  }));

  onProgress?.({ steps: [...steps], current_step: names[0], is_running: true });

  for (let i = 0; i < names.length; i += 1) {
    const name = names[i];
    steps = steps.map((s, idx) => (
      idx === i ? { ...s, status: 'running' } : s
    ));
    onProgress?.({ steps: [...steps], current_step: name, is_running: true });

    await sleep(DEMO_ANIM_MS[name] || 800);

    const duration = DEMO_STEP_MS[name] || 1500;
    steps = steps.map((s, idx) => {
      if (idx < i) return s;
      if (idx === i) {
        return {
          ...s,
          status: 'ok',
          duration_ms: duration,
          detail: demoStepDetail(name, limitInternal, limitExternal),
        };
      }
      return s;
    });
    const next = i + 1 < names.length ? names[i + 1] : null;
    onProgress?.({
      steps: [...steps],
      current_step: next,
      is_running: next != null,
    });
  }

  return {
    success: true,
    is_demo: true,
    pipeline_type: `demo_subset_${target}`,
    steps: steps.map(s => ({ step: s.step, status: 'ok', detail: s.detail, duration_ms: s.duration_ms })),
  };
}

function _seedFromId(id) {
  const s = String(id || 'default');
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) % 997;
  return h;
}

function _pick(seed, options) {
  return options[seed % options.length];
}

export function buildDummyBehaviourProfile(ctx = {}) {
  const { id, name, isExternal = false } = ctx;
  const seed = _seedFromId(id || name);
  const channels = ['Mobile App', 'UPI', 'Net Banking', 'Branch', 'WhatsApp'];
  const outcomes = ['Answered', 'Interested', 'Callback Requested', 'No Response'];
  const tiers = ['High', 'Medium', 'Low'];

  if (isExternal) {
    return {
      is_demo: true,
      digital_adoption_tier: _pick(seed, tiers),
      monthly_login_frequency: 4 + (seed % 12),
      preferred_transaction_channel: _pick(seed + 1, ['WhatsApp', 'Email', 'SMS', 'Voice Call']),
      last_transaction_date: new Date(Date.now() - (seed % 30) * 86400000).toISOString(),
      email_open_rate: 0.35 + (seed % 40) / 100,
      sms_click_rate: 0.12 + (seed % 25) / 100,
      social_media_click_count: 2 + (seed % 18),
      last_call_outcome: _pick(seed + 2, outcomes),
      shopping_score: 45 + (seed % 40),
      travel_score: 30 + (seed % 50),
      food_score: 40 + (seed % 35),
      investment_score: 25 + (seed % 55),
      entertainment_score: 50 + (seed % 30),
      top_interest: _pick(seed, ['Personal Loan', 'Credit Card', 'Savings Account', 'Insurance']),
      lifestyle_tags: ['Digital First', 'Campaign Responsive', 'Metro Urban'],
    };
  }

  return {
    is_demo: true,
    digital_adoption_tier: _pick(seed, tiers),
    monthly_login_frequency: 8 + (seed % 20),
    preferred_transaction_channel: _pick(seed, channels),
    last_transaction_date: new Date(Date.now() - (seed % 14) * 86400000).toISOString(),
    email_open_rate: 0.42 + (seed % 35) / 100,
    sms_click_rate: 0.18 + (seed % 30) / 100,
    social_media_click_count: 5 + (seed % 25),
    last_call_outcome: _pick(seed + 3, ['Answered', 'Completed', 'Follow-up Scheduled']),
    shopping_score: 55 + (seed % 35),
    travel_score: 48 + (seed % 42),
    food_score: 52 + (seed % 38),
    healthcare_score: 38 + (seed % 40),
    investment_score: 60 + (seed % 35),
    fuel_score: 44 + (seed % 30),
    education_score: 35 + (seed % 45),
    entertainment_score: 58 + (seed % 32),
    top_interest: _pick(seed, ['Shopping', 'Travel', 'Investments', 'Dining', 'Healthcare']),
    secondary_interest: _pick(seed + 1, ['OTT', 'Fuel', 'Education', 'Insurance']),
    lifestyle_tags: ['Salary Account', 'UPI Heavy', 'Digital Banking'],
  };
}

export function buildDummyRelationshipProfile(ctx = {}) {
  const { id, name, isExternal = false } = ctx;
  const seed = _seedFromId(id || name);
  const tiers = ['Platinum', 'Gold', 'Silver', 'Standard'];
  const risks = ['Low', 'Medium', 'Low-Medium'];

  if (isExternal) {
    return {
      is_demo: true,
      tenure_months: 0,
      active_products_count: 0,
      clv_score: 150000 + (seed % 8) * 25000,
      relationship_strength_level: _pick(seed, ['High Potential', 'Medium Potential', 'Nurture']),
      risk_rating: _pick(seed, risks),
      churn_probability: null,
      nps_score: null,
      relationship_tier: 'Prospect',
      product_penetration_score: seed % 15,
      engagement_score: 40 + (seed % 45),
      relationship_potential: 55 + (seed % 40),
      cross_sell_potential: _pick(seed, ['Personal Loan', 'Credit Card', 'Savings Plus']),
    };
  }

  return {
    is_demo: true,
    tenure_months: 24 + (seed % 96),
    active_products_count: 2 + (seed % 5),
    clv_score: 280000 + (seed % 12) * 35000,
    relationship_strength_level: _pick(seed, tiers),
    risk_rating: _pick(seed, risks),
    churn_probability: 0.05 + (seed % 20) / 100,
    nps_score: 6 + (seed % 4),
    relationship_tier: _pick(seed, tiers),
    number_of_products: 2 + (seed % 5),
    loyalty_score: 62 + (seed % 30),
    product_penetration_score: 45 + (seed % 40),
    engagement_score: 58 + (seed % 35),
    relationship_stability: 70 + (seed % 25),
  };
}

function _mergeProfile(apiData, dummy) {
  if (!apiData) return { ...dummy, is_demo: true };
  const merged = { ...dummy, ...apiData, is_demo: false };
  Object.keys(dummy).forEach((key) => {
    if (key === 'is_demo') return;
    const v = apiData[key];
    if (v == null || v === '' || v === '—') merged[key] = dummy[key];
  });
  return merged;
}

export function mergeBehaviourProfile(apiData, ctx = {}) {
  return _mergeProfile(apiData, buildDummyBehaviourProfile(ctx));
}

export function mergeRelationshipProfile(apiData, ctx = {}) {
  return _mergeProfile(apiData, buildDummyRelationshipProfile(ctx));
}
