import React, { useState } from 'react';
import InternalCustomers from './InternalCustomers';
import ExternalLeads from './ExternalLeads';
import PageHeader from '../components/ui/PageHeader';

export default function CustomerRegistry() {
  const [activeTab, setActiveTab] = useState('internal');

  const tabs = [
    { id: 'internal', label: 'Internal Customers' },
    { id: 'external', label: 'External Leads' }
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Registry"
        subtitle="Manage and view internal customers and external leads."
      />

      <div className="flex border-b border-neutral-200 mb-6 overflow-x-auto custom-scrollbar">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab ${activeTab === tab.id ? 'tab-active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="animate-fade-in pb-12">
        {activeTab === 'internal' ? <InternalCustomers /> : <ExternalLeads />}
      </div>
    </div>
  );
}
