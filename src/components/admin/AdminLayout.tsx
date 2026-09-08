import React from 'react';
import { AdminRole } from '../../types';

export type AdminView =
  | 'dashboard'
  | 'data'
  | 'datasets'
  | 'training'
  | 'models'
  | 'drift'
  | 'approvals'
  | 'audit'
  | 'system';

interface AdminLayoutProps {
  currentView: AdminView;
  onSelectView: (view: AdminView) => void;
  adminRole: AdminRole;
  onRoleChange: (role: AdminRole) => void;
  onExitAdmin: () => void;
  children: React.ReactNode;
}

const NAV_ITEMS: { id: AdminView; label: string; icon: string; badge?: string }[] = [
  { id: 'dashboard', label: 'Overview', icon: '📊' },
  { id: 'data', label: 'Data & Ingestion', icon: '🧬' },
  { id: 'datasets', label: 'Dataset Registry', icon: '📦' },
  { id: 'training', label: 'Training Jobs', icon: '⚡' },
  { id: 'models', label: 'Model Registry', icon: '🛡️' },
  { id: 'drift', label: 'Drift & Discordance', icon: '📈' },
  { id: 'approvals', label: 'Clinical Approvals', icon: '⚖️' },
  { id: 'audit', label: 'Audit Trail', icon: '📜' },
  { id: 'system', label: 'System & Workers', icon: '⚙️' },
];

const ADMIN_ROLES: AdminRole[] = [
  'SUPER_ADMIN',
  'ML_ENGINEER',
  'DATA_STEWARD',
  'CLINICAL_REVIEWER',
  'SECURITY_ADMIN',
  'AUDITOR',
];

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  currentView,
  onSelectView,
  adminRole,
  onRoleChange,
  onExitAdmin,
  children,
}) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      {/* Top Header Banner */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-xl sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
            <span className="text-white font-black text-lg tracking-wider">D</span>
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="font-bold tracking-tight text-white text-base">DrishtiAI</span>
              <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                Intelligence Control Plane
              </span>
            </div>
            <p className="text-xs text-slate-400">Model Governance, Training Orchestration & Drift</p>
          </div>
        </div>

        {/* Role Selector & Actions */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-800/50 border border-slate-700/60 rounded-xl px-3 py-1.5">
            <span className="text-xs text-slate-400 font-medium">Acting Role:</span>
            <select
              value={adminRole}
              onChange={(e) => onRoleChange(e.target.value as AdminRole)}
              className="bg-transparent text-xs font-semibold text-cyan-300 focus:outline-none cursor-pointer"
            >
              {ADMIN_ROLES.map((role) => (
                <option key={role} value={role} className="bg-slate-900 text-slate-200">
                  {role.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={onExitAdmin}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all hover:border-slate-600"
          >
            <span>←</span>
            <span>Clinical Platform</span>
          </button>
        </div>
      </header>

      {/* Main App Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-64 border-r border-slate-800/80 bg-slate-900/30 backdrop-blur-md flex flex-col justify-between p-4 shrink-0">
          <div className="space-y-1">
            <div className="px-3 py-2 text-[11px] font-semibold tracking-wider uppercase text-slate-400">
              Navigation
            </div>
            {NAV_ITEMS.map((item) => {
              const active = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectView(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    active
                      ? 'bg-gradient-to-r from-cyan-500/15 to-indigo-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* System Badge */}
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 text-[11px] space-y-1.5">
            <div className="flex items-center justify-between text-slate-400">
              <span>Plane Engine</span>
              <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ACTIVE
              </span>
            </div>
            <div className="text-[10px] text-slate-400 flex justify-between">
              <span>Safety Policy</span>
              <span className="text-slate-300 font-mono">SAFE-1.0</span>
            </div>
          </div>
        </aside>

        {/* Primary Content View */}
        <main className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-slate-950 via-slate-900/30 to-slate-950">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};
