import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

// ─── Platform Summary (Dashboard KPIs) ───────────────────────────────────────
export const usePlatformSummary = () =>
  useQuery({ queryKey: ['platform-summary'], queryFn: () => api.get('/api/ops/platform-summary').then(r => r.data), staleTime: 30000 });

export const useOpsDashboard = () =>
  useQuery({ queryKey: ['ops-dashboard'], queryFn: () => api.get('/api/ops/dashboard').then(r => r.data), staleTime: 30000 });

// ─── CRM Customers ───────────────────────────────────────────────────────────
export const useCrmCustomers = (type = 'all', q = '', limit = 500) =>
  useQuery({
    queryKey: ['crm-customers', type, q, limit],
    queryFn: () => api.get('/api/ops/crm/customers', { params: { customer_type: type, q, limit } }).then(r => r.data),
    staleTime: 60000,
  });

export const useCrmCustomer = (entityId) =>
  useQuery({
    queryKey: ['crm-customer', entityId],
    queryFn: () => api.get(`/api/ops/crm/customers/${entityId}`).then(r => r.data),
    enabled: !!entityId,
    staleTime: 60000,
  });

// ─── Customer 360 ────────────────────────────────────────────────────────────
export const useCustomer360 = (customerId) =>
  useQuery({
    queryKey: ['customer360', customerId],
    queryFn: () => api.get(`/api/customer360/${customerId}`).then(r => r.data),
    enabled: !!customerId,
    staleTime: 60000,
  });

// ─── Financial ───────────────────────────────────────────────────────────────
export const useFinancial = (customerId) =>
  useQuery({
    queryKey: ['financial', customerId],
    queryFn: () => api.get(`/api/financial/${customerId}`).then(r => r.data),
    enabled: !!customerId,
    staleTime: 60000,
    retry: false,
  });

// ─── Behaviour ───────────────────────────────────────────────────────────────
export const useBehaviour = (customerId) =>
  useQuery({
    queryKey: ['behaviour', customerId],
    queryFn: () =>
      api.get(`/api/behaviour/${customerId}`)
        .then(r => r.data)
        .catch(err => {
          if (err?.response?.status === 404) return null;
          throw err;
        }),
    enabled: !!customerId,
    staleTime: 60000,
    retry: false,
  });

// ─── Relationship ─────────────────────────────────────────────────────────────
export const useRelationship = (customerId) =>
  useQuery({
    queryKey: ['relationship', customerId],
    queryFn: () =>
      api.get(`/api/relationship/${customerId}`)
        .then(r => r.data)
        .catch(err => {
          if (err?.response?.status === 404) return null;
          throw err;
        }),
    enabled: !!customerId,
    staleTime: 60000,
    retry: false,
  });

// ─── Transactions ─────────────────────────────────────────────────────────────
export const useTransactions = (customerId, limit = 50) =>
  useQuery({
    queryKey: ['transactions', customerId, limit],
    queryFn: () => api.get(`/api/transactions/${customerId}`, { params: { limit } }).then(r => r.data),
    enabled: !!customerId,
    staleTime: 60000,
    retry: false,
  });

// ─── Behaviour Summary ────────────────────────────────────────────────────────
export const useBehaviourSummary = (customerId) =>
  useQuery({
    queryKey: ['behaviour-summary', customerId],
    queryFn: () => api.get(`/api/behaviour-summary/${customerId}`).then(r => r.data),
    enabled: !!customerId,
    staleTime: 60000,
    retry: false,
  });

// ─── External Leads ───────────────────────────────────────────────────────────
export const useExternalLeads = (limit = 200, offset = 0) =>
  useQuery({
    queryKey: ['external-leads', limit, offset],
    queryFn: () => api.get('/api/external/leads', { params: { limit, offset } }).then(r => r.data),
    staleTime: 60000,
  });

export const useExternalProfile = (leadId) =>
  useQuery({
    queryKey: ['external-profile', leadId],
    queryFn: () => api.get(`/api/external/profile/${leadId}`).then(r => r.data),
    enabled: !!leadId,
    staleTime: 60000,
    retry: false,
  });

export const useExternalAnalytics = (leadId) =>
  useQuery({
    queryKey: ['external-analytics', leadId],
    queryFn: () => api.get(`/api/external/analytics/${leadId}`).then(r => r.data),
    enabled: !!leadId,
    staleTime: 60000,
    retry: false,
  });

export const useExternalIntelligence = (leadId) =>
  useQuery({
    queryKey: ['external-intelligence', leadId],
    queryFn: () => api.get(`/api/external/intelligence/${leadId}`).then(r => r.data),
    enabled: !!leadId,
    staleTime: 60000,
    retry: false,
  });

// ─── ML Models ───────────────────────────────────────────────────────────────
export const useRepaymentModelInfo = () =>
  useQuery({ queryKey: ['ml-repayment-info'], queryFn: () => api.get('/api/ml/repayment/model-info').then(r => r.data), staleTime: 120000, retry: false });

export const useProductRecommendationInfo = () =>
  useQuery({ queryKey: ['ml-product-rec-info'], queryFn: () => api.get('/api/ml/product-recommendation/model-info').then(r => r.data), staleTime: 120000, retry: false });

export const useConversionModelInfo = () =>
  useQuery({ queryKey: ['ml-conversion-info'], queryFn: () => api.get('/api/ml/conversion/model-info').then(r => r.data), staleTime: 120000, retry: false });

// ─── Explainability ───────────────────────────────────────────────────────────
export const useExplainReport = (customerId) =>
  useQuery({
    queryKey: ['explain-report', customerId],
    queryFn: () =>
      api.get(`/api/explain/${customerId}`)
        .then(r => r.data)
        .catch(err => {
          // 404 = no report yet in DB — return null instead of throwing
          if (err?.response?.status === 404) return null;
          throw err;
        }),
    enabled: !!customerId,
    staleTime: 0,          // always re-fetch from DB on every selection
    cacheTime: 0,
    retry: false,
  });

// ─── Engagement ───────────────────────────────────────────────────────────────
export const useChannelStatus = () =>
  useQuery({ queryKey: ['channel-status'], queryFn: () => api.get('/api/engagement/channels/status').then(r => r.data), staleTime: 15000 });

export const useEngagementPreview = (limit = 20, profileTypes = 'External,Internal') =>
  useQuery({
    queryKey: ['engagement-preview', limit, profileTypes],
    queryFn: () =>
      api
        .get('/api/engagement/preview', {
          params: { limit, profile_types: profileTypes },
          timeout: 60000,
        })
        .then(r => r.data),
    staleTime: 30000,
    retry: false,
  });

export const useHandoffQueue = () =>
  useQuery({ queryKey: ['handoff-queue'], queryFn: () => api.get('/api/ops/handoffs').then(r => r.data), staleTime: 15000 });

// ─── Pipeline Runner ─────────────────────────────────────────────────────────
export const usePipelineLive = (enabled = false) =>
  useQuery({
    queryKey: ['pipeline-live'],
    queryFn: () => api.get('/api/pipeline/live').then(r => r.data),
    enabled,
    refetchInterval: enabled ? 1000 : false,
    staleTime: 0,
  });

export const usePipelineRuns = (limit = 5) =>
  useQuery({
    queryKey: ['pipeline-runs', limit],
    queryFn: () => api.get('/api/pipeline/runs', { params: { limit } }).then(r => r.data),
    staleTime: 30000,
  });

export const useRunSubsetPipeline = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params) =>
      api.post('/api/pipeline/run/subset', null, { params, timeout: 600000 }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform-summary'] });
      qc.invalidateQueries({ queryKey: ['ops-dashboard'] });
      qc.invalidateQueries({ queryKey: ['crm-customers'] });
      qc.invalidateQueries({ queryKey: ['external-leads'] });
      qc.invalidateQueries({ queryKey: ['pipeline-runs'] });
      qc.invalidateQueries({ queryKey: ['pipeline-live'] });
    },
  });
};

