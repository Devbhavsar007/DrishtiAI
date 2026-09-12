import React from 'react';
import {
  Eye,
  Sparkles,
  LayoutDashboard,
  Database,
  Package,
  Cpu,
  ShieldCheck,
  Activity,
  CheckSquare,
  ScrollText,
  Server,
  ArrowLeft,
  ShieldAlert,
  SlidersHorizontal,
} from 'lucide-react';
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

const NAV_ITEMS: { id: AdminView; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'dashboard', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'data', label: 'Data & Ingestion', icon: <Database className="w-4 h-4" /> },
  { id: 'datasets', label: 'Dataset Registry', icon: <Package className="w-4 h-4" /> },
  { id: 'training', label: 'Training Jobs', icon: <Cpu className="w-4 h-4" /> },
  { id: 'models', label: 'Model Registry', icon: <ShieldCheck className="w-4 h-4" /> },
  { id: 'drift', label: 'Drift & Discordance', icon: <Activity className="w-4 h-4" /> },
  { id: 'approvals', label: 'Clinical Approvals', icon: <CheckSquare className="w-4 h-4" /> },
  { id: 'audit', label: 'Audit Trail', icon: <ScrollText className="w-4 h-4" /> },
  { id: 'system', label: 'System & Workers', icon: <Server className="w-4 h-4" /> },
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
    <div className="min-h-screen bg-[#619FE8] text-white flex flex-col font-sans selection:bg-[#E1FA4A] selection:text-black relative grain-overlay">
      {/* Top Clinical Header Bar */}
      <header
        className="sticky top-0 z-40 w-full min-h-[72px] bg-[#619FE8]/85 backdrop-blur-2xl border-b border-white/10 text-white flex items-center shadow-sm"
        role="region"
        aria-label="Intelligence Control Plane Header"
      >
        <div className="w-full px-4 sm:px-8 py-2.5 flex flex-wrap items-center justify-between gap-4">
          {/* Brand & Suite Subtitle */}
          <div className="flex items-center gap-3.5 select-none">
            <div className="w-9 h-9 bg-sky-100 border border-sky-300 rounded-xl flex items-center justify-center shrink-0 shadow-sm">
              <Eye className="w-5 h-5 text-[#1E54B7] stroke-[2]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span
                  className="text-xl font-bold tracking-tight text-white"
                  style={{ fontFamily: 'var(--font-heading)' }}
                >
                  DrishtiAI
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-[#E1FA4A] text-black shadow-sm">
                  <Sparkles className="w-3 h-3" />
                  MLOps Control Plane
                </span>
              </div>
              <span className="text-[10px] uppercase tracking-[0.12em] text-white/80 font-bold">
                Model Lifecycle, Governance & Drift Telemetry
              </span>
            </div>
          </div>

          {/* Right Role Switcher & Back to Clinical Suite Action */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Role Selector */}
            <div className="flex items-center gap-2 bg-white/15 backdrop-blur-md border border-white/25 rounded-xl px-3 py-1.5 shadow-sm">
              <SlidersHorizontal className="w-3.5 h-3.5 text-white/80" />
              <span className="text-xs text-white/80 font-medium">Role:</span>
              <select
                value={adminRole}
                aria-label="Active Administrative Role"
                onChange={(e) => onRoleChange(e.target.value as AdminRole)}
                className="bg-transparent text-xs font-bold text-white focus:outline-none cursor-pointer pr-1"
              >
                {ADMIN_ROLES.map((role) => (
                  <option key={role} value={role} className="bg-[#1E54B7] text-white">
                    {role.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>

            {/* Back to Clinical Workspace Button */}
            <button
              onClick={onExitAdmin}
              className="flex items-center gap-1.5 px-4 h-9 rounded-xl font-bold text-xs uppercase tracking-wider bg-[#E1FA4A] hover:bg-[#d6f236] active:scale-95 text-black shadow-[0_2px_8px_rgba(22,163,74,0.25)] transition-all cursor-pointer btn-clinical"
              title="Return to Clinical Screening Suite"
            >
              <ArrowLeft className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>Clinical Suite</span>
            </button>
          </div>
        </div>
      </header>

      {/* Primary Workspace: Sidebar + Main Views */}
      <div className="flex-1 flex flex-row relative">
        {/* Desktop Sidebar (matching clinical Navigation.tsx) */}
        <aside
          className="hidden md:flex flex-col w-64 shrink-0 bg-white/10 backdrop-blur-2xl border-r border-white/15 min-h-[calc(100vh-72px)] p-4 gap-2 select-none text-white"
          aria-label="MLOps Navigation Menu"
        >
          <div className="space-y-1.5">
            <div className="px-3 py-1 text-[10px] font-bold tracking-wider uppercase text-white/60">
              Control Planes
            </div>
            {NAV_ITEMS.map((item, idx) => {
              const isActive = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectView(item.id)}
                  style={{ animationDelay: `${idx * 40}ms` }}
                  className={`animate-slide-up flex items-center w-full gap-3 p-3 rounded-xl font-semibold btn-clinical cursor-pointer transition-all duration-200 ${
                    isActive
                      ? 'bg-white text-[#1E54B7] shadow-[0_4px_12px_rgba(8,145,178,0.15)] font-bold'
                      : 'text-white/80 hover:bg-white/12 hover:text-white active:bg-white/20'
                  } focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#1E54B7]`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <div
                    className={`transition-colors duration-150 ${
                      isActive ? 'text-[#1E54B7]' : 'text-white/75'
                    }`}
                  >
                    {item.icon}
                  </div>

                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] font-semibold tracking-tight truncate block">
                        {item.label}
                      </span>
                      {item.badge && (
                        <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full font-mono font-bold bg-[#E1FA4A] text-black shadow-sm">
                          {item.badge}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* System Telemetry Box in Sidebar Footer */}
          <div className="mt-auto space-y-2.5">
            <div className="p-3.5 rounded-2xl bg-white/15 border border-white/20 text-white space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-white/70 uppercase tracking-[0.1em]">
                  Plane Engine
                </span>
                <span className="inline-flex items-center gap-1.5 text-[10px] text-[#E1FA4A] font-mono font-black">
                  <span className="w-2 h-2 rounded-full bg-[#E1FA4A] animate-pulse"></span>
                  ONLINE
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-white/15 text-[10px] font-mono text-white/80">
                <span>Active Model</span>
                <span className="font-bold text-white">ResNet50 v2.2</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono text-white/70">
                <span>Safety Gate</span>
                <span className="text-[#E1FA4A] font-bold">SAFE-1.0</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Primary Content View Container */}
        <main
          className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 pb-24 md:pb-12 overflow-y-auto"
          role="main"
          id="mlops-content"
        >
          {children}
        </main>
      </div>
    </div>
  );
};

