/** Enterprise audit log dummy data for Governance & Audit pages. */

export const DUMMY_AUDIT_LOGS = [
  {
    audit_id: 'aud-001',
    timestamp: '2026-07-15T09:12:34.000Z',
    user: 'priya.sharma@sbi.co.in',
    action: 'ML Model Inference',
    module: 'Conversion ML',
    customer: 'Priya Nair',
    customer_id: 'demo-lead-001',
    ip_address: '10.24.18.45',
    status: 'Success',
  },
  {
    audit_id: 'aud-002',
    timestamp: '2026-07-15T08:55:10.000Z',
    user: 'system@tara.sbi',
    action: 'Voice Call Initiated',
    module: 'Engagement',
    customer: 'Rahul Sharma',
    customer_id: 'demo-lead-002',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
  {
    audit_id: 'aud-003',
    timestamp: '2026-07-15T08:30:00.000Z',
    user: 'admin@tara.sbi',
    action: 'Pipeline Run Triggered',
    module: 'Pipeline',
    customer: '—',
    customer_id: null,
    ip_address: '192.168.1.102',
    status: 'Success',
  },
  {
    audit_id: 'aud-004',
    timestamp: '2026-07-14T17:45:22.000Z',
    user: 'raj.kumar@sbi.co.in',
    action: 'Explainability Report Generated',
    module: 'Explainable AI',
    customer: 'Ananya Iyer',
    customer_id: 'demo-lead-003',
    ip_address: '10.24.19.88',
    status: 'Success',
  },
  {
    audit_id: 'aud-005',
    timestamp: '2026-07-14T16:20:05.000Z',
    user: 'system@tara.sbi',
    action: 'WhatsApp Message Sent',
    module: 'Engagement',
    customer: 'Arjun Das',
    customer_id: 'lead-6',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
  {
    audit_id: 'aud-006',
    timestamp: '2026-07-14T14:10:33.000Z',
    user: 'meera.iyer@sbi.co.in',
    action: 'Customer 360 View Accessed',
    module: 'CRM',
    customer: 'Vikram Patel',
    customer_id: 'lead-2',
    ip_address: '10.24.20.15',
    status: 'Success',
  },
  {
    audit_id: 'aud-007',
    timestamp: '2026-07-14T11:05:18.000Z',
    user: 'system@tara.sbi',
    action: 'Repayment Model Inference',
    module: 'Repayment ML',
    customer: 'Meera Krishnan',
    customer_id: 'demo-lead-005',
    ip_address: '10.24.18.12',
    status: 'Failed',
  },
  {
    audit_id: 'aud-008',
    timestamp: '2026-07-14T10:22:00.000Z',
    user: 'priya.sharma@sbi.co.in',
    action: 'Campaign Launched',
    module: 'Outreach',
    customer: '—',
    customer_id: null,
    ip_address: '10.24.18.45',
    status: 'Success',
  },
  {
    audit_id: 'aud-009',
    timestamp: '2026-07-13T15:40:00.000Z',
    user: 'system@tara.sbi',
    action: 'Voice Session Completed',
    module: 'Voice AI',
    customer: 'Rahul Sharma',
    customer_id: 'demo-lead-002',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
  {
    audit_id: 'aud-010',
    timestamp: '2026-07-13T12:18:44.000Z',
    user: 'admin@tara.sbi',
    action: 'Model Retrain Requested',
    module: 'ML Ops',
    customer: '—',
    customer_id: null,
    ip_address: '192.168.1.102',
    status: 'Pending',
  },
  {
    audit_id: 'aud-011',
    timestamp: '2026-07-13T09:30:12.000Z',
    user: 'raj.kumar@sbi.co.in',
    action: 'Product Recommendation',
    module: 'Product ML',
    customer: 'Sana Khan',
    customer_id: 'lead-7',
    ip_address: '10.24.19.88',
    status: 'Success',
  },
  {
    audit_id: 'aud-012',
    timestamp: '2026-07-12T16:55:00.000Z',
    user: 'meera.iyer@sbi.co.in',
    action: 'Handoff Queue Review',
    module: 'Engagement',
    customer: 'Deepak Menon',
    customer_id: 'ext-4412',
    ip_address: '10.24.20.15',
    status: 'Success',
  },
  {
    audit_id: 'aud-013',
    timestamp: '2026-07-12T11:00:00.000Z',
    user: 'system@tara.sbi',
    action: 'SMS Opt-out Processed',
    module: 'Engagement',
    customer: 'Rohan Gupta',
    customer_id: 'lead-8',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
  {
    audit_id: 'aud-014',
    timestamp: '2026-07-11T08:15:30.000Z',
    user: 'admin@tara.sbi',
    action: 'Access Denied — Unauthorized Export',
    module: 'CRM',
    customer: '—',
    customer_id: null,
    ip_address: '203.45.67.89',
    status: 'Failed',
  },
  {
    audit_id: 'aud-015',
    timestamp: '2026-07-10T14:05:55.000Z',
    user: 'system@tara.sbi',
    action: 'Conversion Score Updated',
    module: 'Conversion ML',
    customer: 'Meera Krishnan',
    customer_id: 'demo-lead-005',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
  {
    audit_id: 'aud-016',
    timestamp: '2026-07-09T10:30:00.000Z',
    user: 'priya.sharma@sbi.co.in',
    action: 'Lead Enrichment Batch',
    module: 'Pipeline',
    customer: '—',
    customer_id: null,
    ip_address: '10.24.18.45',
    status: 'Success',
  },
  {
    audit_id: 'aud-017',
    timestamp: '2026-07-08T17:22:11.000Z',
    user: 'raj.kumar@sbi.co.in',
    action: 'XAI Feature Attribution',
    module: 'Explainable AI',
    customer: 'Kavitha Reddy',
    customer_id: 'ext-2298',
    ip_address: '10.24.19.88',
    status: 'Success',
  },
  {
    audit_id: 'aud-018',
    timestamp: '2026-07-07T13:30:45.000Z',
    user: 'system@tara.sbi',
    action: 'Multi-Channel Orchestration',
    module: 'Engagement',
    customer: 'Deepak Menon',
    customer_id: 'ext-4412',
    ip_address: '10.24.18.12',
    status: 'Success',
  },
];

/** Rich detail payloads for Audit Detail page. */
export const DUMMY_AUDIT_DETAILS = {
  'aud-001': {
    request: {
      endpoint: 'POST /api/ml/conversion/predict',
      entity_id: 'demo-lead-001',
      entity_type: 'External',
      features: {
        consent: 1,
        lead_quality_score: 82,
        credit_score: 742,
        digital_engagement_score: 78,
        previous_campaign_response: 1,
        communication_readiness: 0.91,
      },
    },
    response: {
      conversion_probability: 0.78,
      predicted_label: 'High Intent',
      model_version: '1.0.0',
      inference_ms: 42,
    },
    model_used: 'xgboost-conversion-v1.0.0',
    prompt_version: null,
    decision: 'Approve outreach — customer qualifies for Personal Loan campaign',
    explainability_reference: 'XAI-RPT-demo-lead-001-20260715',
    trace_id: 'trc-7f3a9b2e1c4d5e6f7890abcd',
  },
  'aud-002': {
    request: {
      endpoint: 'POST /api/engagement/callback/start',
      phone: '9123456780',
      entity_id: 'demo-lead-002',
      entity_type: 'External',
      source_channel: 'Outreach',
      campaign_id: 'cmp-002',
    },
    response: {
      triggered: true,
      session_id: 'sess-voice-002',
      call_sid: 'CA8e4f1a2b3c4d5e6',
      timing_ms: { total: 1240 },
    },
    model_used: 'tara-voice-agent-v2.1',
    prompt_version: 'voice-lending-offer-v2.1.3',
    decision: 'Initiate outbound voice call for Gold Credit Card upgrade',
    explainability_reference: 'XAI-RPT-demo-lead-002-20260715',
    trace_id: 'trc-8e4f1a2b3c4d5e6f7890abce',
  },
  'aud-004': {
    request: {
      endpoint: 'POST /api/explain/generate',
      customer_id: 'demo-lead-003',
      include_repayment: true,
      include_conversion: true,
      include_product_rec: true,
    },
    response: {
      report_id: 'XAI-RPT-demo-lead-003-20260714',
      sections_generated: ['repayment', 'conversion', 'product_recommendation'],
      generation_ms: 890,
    },
    model_used: 'shap-explainer-v1.2 + xgboost-conversion-v1.0.0',
    prompt_version: 'xai-narrative-v1.0.2',
    decision: 'Generate full explainability report for customer review',
    explainability_reference: 'XAI-RPT-demo-lead-003-20260714',
    trace_id: 'trc-9f5a2b3c4d5e6f7890abcdf',
  },
  'aud-007': {
    request: {
      endpoint: 'POST /api/ml/repayment/predict',
      customer_id: 'demo-lead-005',
      features: { income: null, credit_score: 698, emi_burden: 0.42 },
    },
    response: {
      error: 'Missing required feature: monthly_income',
      error_code: 'FEATURE_VALIDATION_FAILED',
    },
    model_used: 'random-forest-repayment-v1.0.0',
    prompt_version: null,
    decision: 'Inference rejected — incomplete feature vector',
    explainability_reference: null,
    trace_id: 'trc-a1b2c3d4e5f6789012345678',
  },
  'aud-014': {
    request: {
      endpoint: 'GET /api/ops/crm/customers/export',
      requested_by: 'unknown@external.com',
      format: 'csv',
      limit: 10000,
    },
    response: {
      error: '403 Forbidden',
      error_code: 'RBAC_DENIED',
      required_role: 'crm_admin',
      actual_role: 'none',
    },
    model_used: null,
    prompt_version: null,
    decision: 'Block unauthorized bulk export attempt',
    explainability_reference: null,
    trace_id: 'trc-blocked-export-20260711',
  },
};

function buildDefaultAuditDetail(log) {
  const isFailed = log.status === 'Failed';
  const isPending = log.status === 'Pending';

  return {
    request: {
      endpoint: `POST /api/${log.module.toLowerCase().replace(/\s+/g, '-')}/action`,
      user: log.user,
      action: log.action,
      customer_id: log.customer_id,
      timestamp: log.timestamp,
    },
    response: isFailed
      ? { error: 'Operation failed', status: log.status }
      : isPending
        ? { status: 'pending', message: 'Operation queued for processing' }
        : { status: 'success', message: `${log.action} completed successfully` },
    model_used: log.module.includes('ML') || log.module === 'Voice AI'
      ? 'tara-ml-default-v1.0.0'
      : log.module === 'Explainable AI'
        ? 'shap-explainer-v1.2'
        : null,
    prompt_version: log.module === 'Voice AI' ? 'voice-agent-v2.0.0' : log.module === 'Explainable AI' ? 'xai-narrative-v1.0.0' : null,
    decision: isFailed
      ? `Deny — ${log.action} failed validation or authorization`
      : `${log.action} approved and executed for ${log.customer !== '—' ? log.customer : 'system operation'}`,
    explainability_reference: log.customer_id ? `XAI-RPT-${log.customer_id}` : null,
    trace_id: `trc-${log.audit_id.replace('aud-', '')}-${Date.now().toString(36)}`,
  };
}

export function getAuditLogById(id) {
  return DUMMY_AUDIT_LOGS.find(a => a.audit_id === id);
}

export function getAuditDetail(log) {
  if (!log) return null;
  const overlay = DUMMY_AUDIT_DETAILS[log.audit_id];
  const defaults = buildDefaultAuditDetail(log);
  if (!overlay) return { ...log, ...defaults };
  return { ...log, ...defaults, ...overlay };
}
