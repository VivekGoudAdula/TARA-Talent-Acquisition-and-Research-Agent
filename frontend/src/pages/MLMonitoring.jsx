import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import SectionPanel from '../components/ui/SectionPanel';
import Badge from '../components/ui/Badge';
import { PageSpinner, ErrorState } from '../components/ui/States';
import PageHeader from '../components/ui/PageHeader';
import { useRepaymentModelInfo, useProductRecommendationInfo, useConversionModelInfo } from '../api/hooks';
import api from '../api/client';
import { mergeMlModelInfo } from '../api/dummyData';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { RefreshCw } from 'lucide-react';

function normalizeFeatureLabel(raw) {
  return String(raw || '')
    .replace(/^(num|cat)\s+/i, '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function buildFeatureImportanceChartData(importance) {
  const byLabel = {};
  Object.entries(importance || {}).forEach(([key, weight]) => {
    const name = normalizeFeatureLabel(key);
    const w = Number(weight) || 0;
    if (!name || w <= 0) return;
    byLabel[name] = Math.max(byLabel[name] || 0, w);
  });
  return Object.entries(byLabel)
    .map(([name, weight]) => ({ name, weight }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 5);
}

function ModelPerformanceMetrics({ metrics }) {
  const isRegression = metrics?.model_type === 'regression';

  if (isRegression) {
    return (
      <div>
        <h4 className="text-xs font-semibold text-neutral-500 uppercase mb-3">Model Performance (Regression)</h4>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="border border-neutral-100 rounded p-2">
            <div className="text-xs text-neutral-500">MAE</div>
            <div className="text-sm font-bold text-neutral-800">
              {metrics.mae != null ? `${Number(metrics.mae).toFixed(2)} pts` : '—'}
            </div>
          </div>
          <div className="border border-neutral-100 rounded p-2">
            <div className="text-xs text-neutral-500">RMSE</div>
            <div className="text-sm font-bold text-neutral-800">
              {metrics.rmse != null ? `${Number(metrics.rmse).toFixed(2)} pts` : '—'}
            </div>
          </div>
          <div className="border border-neutral-100 rounded p-2">
            <div className="text-xs text-neutral-500">R²</div>
            <div className="text-sm font-bold text-neutral-800">
              {metrics.r2 != null ? Number(metrics.r2).toFixed(3) : '—'}
            </div>
          </div>
        </div>
        <p className="text-[10px] text-neutral-400 mt-2">
          Predicts conversion probability (0–100%). Lower MAE/RMSE is better; R² closer to 1 is better.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-xs font-semibold text-neutral-500 uppercase mb-3">Model Accuracy & Performance</h4>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="border border-neutral-100 rounded p-2">
          <div className="text-xs text-neutral-500">Accuracy</div>
          <div className="text-sm font-bold text-neutral-800">
            {metrics.accuracy != null ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div className="border border-neutral-100 rounded p-2">
          <div className="text-xs text-neutral-500">F1 Score</div>
          <div className="text-sm font-bold text-neutral-800">
            {metrics.f1 != null ? `${(metrics.f1 * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div className="border border-neutral-100 rounded p-2">
          <div className="text-xs text-neutral-500">ROC-AUC</div>
          <div className="text-sm font-bold text-neutral-800">
            {metrics.roc_auc != null ? `${(metrics.roc_auc * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureImportanceChart({ importance }) {
  const chartData = buildFeatureImportanceChartData(importance);
  if (!chartData.length) return null;

  const longest = Math.max(...chartData.map(d => d.name.length), 8);
  const yAxisWidth = Math.min(130, Math.max(72, longest * 5.2));
  const chartHeight = chartData.length * 34 + 16;

  return (
    <div>
      <h4 className="text-xs font-semibold text-neutral-500 uppercase mb-2">Top Features Importance</h4>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
          barCategoryGap="28%"
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E1DFDD" />
          <XAxis type="number" fontSize={10} tickLine={false} />
          <YAxis
            dataKey="name"
            type="category"
            width={yAxisWidth}
            fontSize={10}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <Tooltip />
          <Bar dataKey="weight" fill="#107C10" radius={[0, 4, 4, 0]} barSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function MLMonitoring() {
  const queryClient = useQueryClient();
  const [training, setTraining] = useState(null);
  const [trainError, setTrainError] = useState(null);
  const [trainMessage, setTrainMessage] = useState(null);

  const repayment = useRepaymentModelInfo();
  const productRec = useProductRecommendationInfo();
  const conversion = useConversionModelInfo();

  const trainModel = async (key, endpoint) => {
    setTraining(key);
    setTrainError(null);
    setTrainMessage(null);
    try {
      const { data } = await api.post(endpoint);
      setTrainMessage(`${key} trained — ${data.best_model || 'ok'} (${data.records_used ?? '—'} records)`);
      const queryKeys = { repayment: 'ml-repayment-info', conversion: 'ml-conversion-info' };
      if (queryKeys[key]) {
        await queryClient.invalidateQueries({ queryKey: [queryKeys[key]] });
      }
    } catch (err) {
      setTrainError(err?.response?.data?.detail || err?.message || 'Training failed');
    } finally {
      setTraining(null);
    }
  };

  const isLoading = repayment.isLoading || productRec.isLoading || conversion.isLoading;
  if (isLoading) return <PageSpinner />;

  const models = [
    {
      name: 'Repayment Capacity Predictor',
      query: repayment,
      label: 'Repayment',
      trainKey: 'repayment',
      trainEndpoint: '/api/ml/repayment/train',
      canTrain: true,
      dummyKey: 'repayment',
    },
    {
      name: 'Product Recommendation Engine',
      query: productRec,
      label: 'Product Recommendation',
      canTrain: false,
      dummyKey: 'product',
    },
    {
      name: 'Lead Conversion Scorer',
      query: conversion,
      label: 'Conversion',
      trainKey: 'conversion',
      trainEndpoint: '/api/ml/conversion/train',
      canTrain: true,
      dummyKey: 'conversion',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="ML Monitoring"
        subtitle="Model health, training controls, and performance metrics."
      />

      {(trainMessage || trainError) && (
        <div className={`card p-3 text-sm ${trainError ? 'text-red-700 bg-red-50 border-red-200' : 'text-emerald-700 bg-emerald-50 border-emerald-200'}`}>
          {trainError || trainMessage}
        </div>
      )}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {models.map(({ name, query, label, trainKey, trainEndpoint, canTrain, dummyKey }) => {
          if (query.isError) {
            const m = mergeMlModelInfo(null, dummyKey);
            const metrics = m.metrics || {};
            return (
              <SectionPanel key={name} title={name} subtitle={`Algorithm: ${m.algorithm} (demo)`}>
                <div className="space-y-6">
                  <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Showing demo metrics — train model or check API connection for live data.
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-neutral-500 uppercase">Status</span>
                    <Badge variant="green">Demo</Badge>
                  </div>
                  <div className="bg-neutral-50 rounded p-4 space-y-2 text-xs">
                    <div className="flex justify-between"><span className="text-neutral-500">Train Samples:</span><span className="font-medium">{m.train_samples}</span></div>
                    <div className="flex justify-between"><span className="text-neutral-500">Test Samples:</span><span className="font-medium">{m.test_samples}</span></div>
                  </div>
                  <ModelPerformanceMetrics metrics={metrics} />
                  <FeatureImportanceChart importance={m.feature_importance} />
                </div>
              </SectionPanel>
            );
          }

          const m = mergeMlModelInfo(query.data, dummyKey);
          const metrics = m.metrics || {};

          return (
            <SectionPanel key={name} title={name} subtitle={`Algorithm: ${m.algorithm || 'Untrained'}`}>
              <div className="space-y-6">
                {/* Status Badges */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-neutral-500 uppercase">Status</span>
                  <div className="flex items-center gap-2">
                    {canTrain && (
                      <button
                        type="button"
                        disabled={!!training}
                        onClick={() => trainModel(trainKey, trainEndpoint)}
                        className="text-xs px-2.5 py-1 rounded-md bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 flex items-center gap-1"
                      >
                        {training === trainKey ? <RefreshCw size={12} className="animate-spin" /> : null}
                        {training === trainKey ? 'Training…' : 'Train'}
                      </button>
                    )}
                    <Badge variant={m.trained ? 'green' : 'neutral'}>
                      {m.trained ? 'Active & Trained' : 'Untrained'}
                    </Badge>
                  </div>
                </div>

                {/* Model Metadata */}
                <div className="bg-neutral-50 rounded p-4 space-y-2 text-xs">
                  <div className="flex justify-between"><span className="text-neutral-500">Version:</span><span className="font-medium">{m.version || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-neutral-500">Last Trained:</span><span className="font-medium">{m.last_trained ? new Date(m.last_trained).toLocaleString() : '—'}</span></div>
                  <div className="flex justify-between"><span className="text-neutral-500">Train Samples:</span><span className="font-medium">{m.train_samples || 0}</span></div>
                  <div className="flex justify-between"><span className="text-neutral-500">Test Samples:</span><span className="font-medium">{m.test_samples || 0}</span></div>
                </div>

                <ModelPerformanceMetrics metrics={metrics} />

                <FeatureImportanceChart importance={m.feature_importance} />
              </div>
            </SectionPanel>
          );
        })}
      </div>
    </div>
  );
}
