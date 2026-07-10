import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const TITLES = {
  '/': 'Dashboard',
  '/internal': 'Internal Customers',
  '/external': 'External Leads',
  '/ml': 'ML Monitoring',
  '/explainability': 'Explainable AI',
  '/engagement': 'Engagement Center',
  '/voice': 'Voice Console',
};

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const { pathname } = useLocation();

  const base = '/' + pathname.split('/')[1];
  const title = TITLES[base] || TITLES[pathname] || 'TARA';

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
