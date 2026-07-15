import React, { useState, useEffect } from 'react';
import { Bell, RefreshCw, Wifi, WifiOff, Sun, Moon } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import api from '../../api/client';
import { useTheme } from '../../context/ThemeContext';

function useApiHealth() {
  const [online, setOnline] = useState(null);
  useEffect(() => {
    let mounted = true;
    const check = () => api.get('/health').then(() => { if (mounted) setOnline(true); }).catch(() => { if (mounted) setOnline(false); });
    check();
    const id = setInterval(check, 30000);
    return () => { mounted = false; clearInterval(id); };
  }, []);
  return online;
}

export default function Topbar() {
  const qc = useQueryClient();
  const online = useApiHealth();
  const { theme, toggleTheme } = useTheme();

  return (
    <header
      className="h-[60px] bg-surface border-b flex items-center justify-end px-6 shrink-0"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <div className="flex items-center gap-3">
        {/* API Health indicator */}
        <div className="flex items-center gap-1.5 text-xs">
          {online === null ? null : online ? (
            <><Wifi size={13} className="text-success-500" /><span className="text-success-500 font-medium">Backend online</span></>
          ) : (
            <><WifiOff size={13} className="text-danger-500" /><span className="text-danger-500 font-medium">Backend offline</span></>
          )}
        </div>

        <button
          className="btn-ghost btn-sm"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        <button
          className="btn-ghost btn-sm"
          onClick={() => qc.invalidateQueries()}
          title="Refresh all data"
        >
          <RefreshCw size={14} />
        </button>
        <button className="btn-ghost btn-sm" title="Notifications">
          <Bell size={14} />
        </button>
        <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs font-bold">
          RM
        </div>
      </div>
    </header>
  );
}
