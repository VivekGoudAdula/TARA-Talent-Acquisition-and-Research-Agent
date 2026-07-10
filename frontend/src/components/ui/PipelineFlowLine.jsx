import React from 'react';
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

const STEP_LABELS = {
  external_enrich: 'Enrich Leads',
  external_analytics: 'Lead Analytics',
  external_intelligence: 'Lead Intelligence',
  internal_build_all: 'Customer 360 Build',
  behaviour_summary: 'Behaviour Summary',
  ml_dataset: 'ML Dataset',
  repayment_train: 'Repayment Model',
  conversion_train: 'Conversion Model',
  scoring_persist: 'Score & Persist',
  explainability: 'Explainability',
  pipeline: 'Pipeline',
};

function labelFor(step) {
  return STEP_LABELS[step] || step.replace(/_/g, ' ');
}

function StepIcon({ status }) {
  if (status === 'running') return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
  if (status === 'ok') return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === 'error') return <XCircle className="h-4 w-4 text-rose-600" />;
  return <Circle className="h-4 w-4 text-neutral-300" />;
}

function statusColor(status) {
  if (status === 'running') return 'border-blue-500 bg-blue-50 text-blue-800';
  if (status === 'ok') return 'border-emerald-500 bg-emerald-50 text-emerald-800';
  if (status === 'error') return 'border-rose-500 bg-rose-50 text-rose-800';
  return 'border-neutral-200 bg-white text-neutral-500';
}

export default function PipelineFlowLine({ steps = [], currentStep, isRunning, className = '' }) {
  if (!steps.length) {
    return (
      <div className={`text-sm text-neutral-400 text-center py-6 ${className}`}>
        Configure and run the pipeline to see live step progress.
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto pb-2 ${className}`}>
      <div className="flex items-start min-w-max px-2 py-2">
        {steps.map((step, index) => {
          const status = step.status === 'pending' && currentStep === step.step ? 'running' : step.status;
          const isLast = index === steps.length - 1;
          return (
            <React.Fragment key={step.step}>
              <div className="flex flex-col items-center w-28 shrink-0">
                <div className={`flex items-center justify-center h-9 w-9 rounded-full border-2 ${statusColor(status)}`}>
                  <StepIcon status={status} />
                </div>
                <div className="mt-2 text-center px-1">
                  <div className="text-[11px] font-semibold text-neutral-800 leading-tight">{labelFor(step.step)}</div>
                  <div className="text-[10px] text-neutral-400 mt-0.5 capitalize">{status}</div>
                  {step.duration_ms > 0 && (
                    <div className="text-[10px] text-neutral-400">{step.duration_ms}ms</div>
                  )}
                </div>
              </div>
              {!isLast && (
                <div className="flex items-center h-9 px-1 shrink-0">
                  <div
                    className={`h-0.5 w-10 sm:w-14 rounded ${
                      step.status === 'ok' ? 'bg-emerald-400' : isRunning ? 'bg-blue-200' : 'bg-neutral-200'
                    }`}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
      {isRunning && (
        <div className="flex items-center gap-2 text-xs text-blue-700 mt-2 px-2">
          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          <span>Pipeline running{currentStep ? ` — ${labelFor(currentStep)}` : '…'}</span>
        </div>
      )}
    </div>
  );
}

export function buildExpectedSteps(target, trainModels) {
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
  return steps.map(step => ({ step, status: 'pending', detail: null, duration_ms: 0 }));
}
