import React, { useState, useEffect } from 'react';
import { Bell, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import api from '../../api/client';

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

export default function Topbar({ title }) {
  const qc = useQueryClient();
  const online = useApiHealth();

  return (
    <header className="h-[60px] bg-white border-b border-neutral-200 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-base font-semibold text-neutral-800">{title}</h1>
      <div className="flex items-center gap-3">
        {/* API Health indicator */}
        <div className="flex items-center gap-1.5 text-xs">
          {online === null ? null : online ? (
            <><Wifi size={13} className="text-success-500" /><span className="text-success-500 font-medium">API Online</span></>
          ) : (
            <><WifiOff size={13} className="text-danger-500" /><span className="text-danger-500 font-medium">API Offline</span></>
          )}
        </div>

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
