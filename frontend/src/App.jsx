import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import InternalCustomers from './pages/InternalCustomers';
import ExternalLeads from './pages/ExternalLeads';
import CustomerDetail from './pages/CustomerDetail';
import CustomerRegistry from './pages/CustomerRegistry';
import OutreachPrograms from './pages/OutreachPrograms';
import OutreachDetail from './pages/OutreachDetail';
import MLMonitoring from './pages/MLMonitoring';
import ExplainableAI from './pages/ExplainableAI';
import EngagementCenter from './pages/EngagementCenter';
import VoiceConsole from './pages/VoiceConsole';
import LiveContactMonitor from './pages/LiveContactMonitor';
import InteractionHistory from './pages/InteractionHistory';
import InteractionDetail from './pages/InteractionDetail';
import GovernanceAudit from './pages/GovernanceAudit';
import AuditDetail from './pages/AuditDetail';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="registry" element={<CustomerRegistry />} />
        <Route path="outreach" element={<OutreachPrograms />} />
        <Route path="outreach/:id" element={<OutreachDetail />} />
        <Route path="customer/:id" element={<CustomerDetail />} />
        <Route path="lead/:id" element={<CustomerDetail />} />
        <Route path="ml" element={<MLMonitoring />} />
        <Route path="explainability" element={<ExplainableAI />} />
        <Route path="engagement" element={<EngagementCenter />} />
        <Route path="voice" element={<VoiceConsole />} />
        <Route path="monitor" element={<LiveContactMonitor />} />
        <Route path="history" element={<InteractionHistory />} />
        <Route path="history/:id" element={<InteractionDetail />} />
        <Route path="governance" element={<GovernanceAudit />} />
        <Route path="governance/:id" element={<AuditDetail />} />
      </Route>
    </Routes>
  );
}
