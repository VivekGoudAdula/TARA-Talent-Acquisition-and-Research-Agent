import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Users, Brain, Lightbulb,
  MessageSquare, Phone, ChevronRight, Megaphone, Radio, History, Shield
} from 'lucide-react';
import taraLogo from '../../images/tara.png';

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/registry', icon: Users, label: 'Customer Registry' },
  { to: '/outreach', icon: Megaphone, label: 'Outreach Programs' },
  { to: '/ml', icon: Brain, label: 'ML Monitoring' },
  { to: '/explainability', icon: Lightbulb, label: 'Explainable AI' },
  { to: '/engagement', icon: MessageSquare, label: 'Engagement Center' },
  { to: '/voice', icon: Phone, label: 'Voice Console' },
  { to: '/monitor', icon: Radio, label: 'Live Contact Monitor' },
  { to: '/history', icon: History, label: 'Interaction History' },
  { to: '/governance', icon: Shield, label: 'Governance & Audit' },
];

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside
      className={`flex flex-col h-full bg-surface-sidebar border-r transition-all duration-200 shrink-0 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
      style={{ borderColor: 'var(--color-border)' }}
    >
      {/* Brand */}
      <div
        className={`flex items-center min-h-[60px] ${collapsed ? 'justify-center px-2 py-3' : 'px-3 py-3'}`}
        style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
      >
        <img
          src={taraLogo}
          alt="TARA — Targeted Acquisition & Reach Agent"
          className={
            collapsed
              ? 'h-9 w-9 object-cover object-left rounded-md shrink-0'
              : 'h-11 w-full object-contain object-left'
          }
          draggable={false}
        />
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
      <div className="px-2 py-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
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
