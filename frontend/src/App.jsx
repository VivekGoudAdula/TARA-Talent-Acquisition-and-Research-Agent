import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import InternalCustomers from './pages/InternalCustomers';
import ExternalLeads from './pages/ExternalLeads';
import CustomerDetail from './pages/CustomerDetail';
import MLMonitoring from './pages/MLMonitoring';
import ExplainableAI from './pages/ExplainableAI';
import EngagementCenter from './pages/EngagementCenter';
import VoiceConsole from './pages/VoiceConsole';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="internal" element={<InternalCustomers />} />
        <Route path="external" element={<ExternalLeads />} />
        <Route path="customer/:id" element={<CustomerDetail />} />
        <Route path="lead/:id" element={<CustomerDetail />} />
        <Route path="ml" element={<MLMonitoring />} />
        <Route path="explainability" element={<ExplainableAI />} />
        <Route path="engagement" element={<EngagementCenter />} />
        <Route path="voice" element={<VoiceConsole />} />
      </Route>
    </Routes>
  );
}
