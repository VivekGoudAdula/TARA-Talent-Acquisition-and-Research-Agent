import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Users, UserCheck, User, Brain, Lightbulb,
  MessageSquare, Phone, ChevronRight, Sparkles
} from 'lucide-react';

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/internal', icon: Users, label: 'Internal Customers' },
  { to: '/external', icon: UserCheck, label: 'External Leads' },
  { to: '/ml', icon: Brain, label: 'ML Monitoring' },
  { to: '/explainability', icon: Lightbulb, label: 'Explainable AI' },
  { to: '/engagement', icon: MessageSquare, label: 'Engagement Center' },
  { to: '/voice', icon: Phone, label: 'Voice Console' },
];

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside className={`flex flex-col h-full bg-white border-r border-neutral-200 transition-all duration-200 ${collapsed ? 'w-16' : 'w-60'} shrink-0`}>
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-neutral-100 min-h-[60px]">
        <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center shrink-0">
          <Sparkles size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <div className="text-sm font-bold text-neutral-800">TARA</div>
            <div className="text-[10px] text-neutral-400 font-medium">Intelligence Engine</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 flex flex-col gap-0.5 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? 'sidebar-item-active' : ''} ${collapsed ? 'justify-center px-2' : ''}`
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 py-3 border-t border-neutral-100">
        <button
          onClick={onToggle}
          className="sidebar-item w-full justify-center"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronRight size={16} className={`transition-transform ${collapsed ? '' : 'rotate-180'}`} />
        </button>
      </div>
    </aside>
  );
}
