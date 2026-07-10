import React from 'react';
export function Spinner({ size = 'md', className = '' }) {
  const sz = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' }[size];
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className={`${sz} animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500`} />
    </div>
  );
}

export function PageSpinner() {
  return <div className="flex items-center justify-center h-64"><Spinner size="lg" /></div>;
}

export function ErrorState({ message = 'Something went wrong', retry }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-center">
      <div className="text-2xl">⚠️</div>
      <p className="text-sm text-neutral-500">{message}</p>
      {retry && <button className="btn btn-secondary btn-sm" onClick={retry}>Try again</button>}
    </div>
  );
}

export function EmptyState({ icon = '📭', title = 'No data', message = '', action }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-2 text-center">
      <div className="text-3xl">{icon}</div>
      <p className="font-medium text-neutral-700">{title}</p>
      {message && <p className="text-xs text-neutral-400">{message}</p>}
      {action}
    </div>
  );
}
