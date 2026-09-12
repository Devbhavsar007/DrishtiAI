import React, { useState } from 'react';
import {
  LayoutDashboard,
  Microscope,
  Layers,
  Users,
  MoreHorizontal,
  X,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Radio,
  ChevronRight,
  Database,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { ActiveView } from '../types';

interface NavItem {
  id: ActiveView;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  description: string;
}

export const Navigation: React.FC = () => {
  const { activeView, setActiveView, batchQueue } = useMedicalData();
  const [isMoreOpen, setIsMoreOpen] = useState(false);

  const navItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Clinical Dashboard',
      shortLabel: 'Dashboard',
      icon: <LayoutDashboard className="w-5 h-5" />,
      description: 'Screening metrics & risk distribution',
    },
    {
      id: 'new-scan',
      label: 'New Retinal Scan',
      shortLabel: 'New Scan',
      icon: <Microscope className="w-5 h-5" />,
      description: 'AI fundus analysis & Grad-CAM',
    },
    {
      id: 'batch-screening',
      label: 'Batch Screening',
      shortLabel: 'Batch Queue',
      icon: <Layers className="w-5 h-5" />,
      description: 'Mobile eye camp queue management',
    },
    {
      id: 'patients',
      label: 'Patient Directory',
      shortLabel: 'Patients',
      icon: <Users className="w-5 h-5" />,
      description: 'Longitudinal records & HbA1c history',
    },
  ];

  return (
    <>
      {/* Desktop Left Sidebar (Responsive w-60 on tablet / w-64 on desktop) */}
      <aside
        className="hidden md:flex flex-col w-60 lg:w-64 shrink-0 bg-white/10 backdrop-blur-2xl border-r border-white/15 min-h-[calc(100vh-72px)] p-4 gap-2 select-none text-white transition-all"
        aria-label="Main Navigation Menu"
      >
        <div className="space-y-1.5">
          {navItems.map((item, idx) => {
            const isActive = activeView === item.id || (item.id === 'patients' && activeView === 'patient-detail');
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                style={{ animationDelay: `${idx * 60}ms` }}
                className={`animate-slide-up flex items-center w-full gap-3 p-3 rounded-xl font-semibold btn-clinical cursor-pointer transition-all duration-200 ${
                  isActive
                    ? 'bg-white text-[#1E54B7] shadow-[0_4px_12px_rgba(8,145,178,0.15)] font-bold'
                    : 'text-white/80 hover:bg-white/12 hover:text-white active:bg-white/20'
                } focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#1E54B7]`}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className={`transition-colors duration-150 ${isActive ? 'text-[#1E54B7]' : 'text-white/75'}`}>
                  {item.icon}
                </div>

                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-semibold tracking-tight truncate block">{item.shortLabel}</span>
                    {item.id === 'batch-screening' && batchQueue.length > 0 && (
                      <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full font-mono font-bold bg-[#E1FA4A] text-black shadow-sm">
                        {batchQueue.length}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Clinical Accreditation / Clinic Mode Footer Box in Sidebar */}
        <div className="mt-auto space-y-2.5">
          <button
            onClick={() => setActiveView('admin')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-white/15 hover:bg-white/25 active:bg-white/30 border border-white/25 text-xs font-bold text-white btn-clinical cursor-pointer shadow-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#1E54B7]"
            title="Open DrishtiAI MLOps & Model Control Plane"
          >
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#E1FA4A] animate-pulse"></span>
              <span>MLOps Platform</span>
            </div>
            <span className="text-[#E1FA4A] font-mono text-[11px] font-bold">Control ⚡</span>
          </button>

          <button
            onClick={() => setActiveView('landing')}
            className="w-full flex items-center justify-between p-2.5 rounded-xl bg-white/10 hover:bg-white/18 active:bg-white/25 border border-white/15 text-xs font-medium text-white/90 btn-clinical cursor-pointer focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#1E54B7]"
          >
            <span>Landing Page</span>
            <span className="text-white/70 font-semibold text-[11px]">Overview ↗</span>
          </button>

          <div className="p-3.5 rounded-2xl bg-white/15 border border-white/20 text-white space-y-1.5 backdrop-blur-md">
            <p className="text-[10px] font-bold text-white/70 uppercase tracking-[0.1em]">
              Active Camp / Clinic
            </p>
            <p className="text-xs font-semibold text-white leading-snug">
              General Hospital - Mumbai
            </p>
            <div className="flex items-center justify-between pt-2 border-t border-white/15 text-[10px] font-mono text-white/70">
              <span>Gemma-4 AI</span>
              <span className="text-[#E1FA4A] font-bold">WCAG AAA</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile & Tablet Bottom Sticky Navigation Bar with Safe Area Support */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#619FE8]/95 backdrop-blur-2xl border-t border-white/30 px-2 sm:px-4 py-2 pb-safe flex items-center justify-around shadow-2xl"
        role="navigation"
        aria-label="Mobile Clinical Navigation"
      >
        {navItems.map((item) => {
          const isActive = activeView === item.id || (item.id === 'patients' && activeView === 'patient-detail');
          return (
            <button
              key={item.id}
              onClick={() => {
                setIsMoreOpen(false);
                setActiveView(item.id);
              }}
              className={`relative flex flex-col items-center justify-center min-w-[62px] xs:min-w-[68px] min-h-[48px] py-1 px-2 rounded-2xl transition-all ${
                isActive
                  ? 'text-[#1E54B7] bg-white font-black shadow-lg scale-105'
                  : 'text-white/80 hover:text-white active:scale-95'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                {item.icon}
                {item.id === 'batch-screening' && batchQueue.length > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 w-4 h-4 rounded-full bg-[#E1FA4A] text-black text-[9px] font-mono font-black flex items-center justify-center shadow-sm">
                    {batchQueue.length}
                  </span>
                )}
              </div>
              <span className="text-[10px] xs:text-[11px] mt-0.5 font-bold tracking-tight whitespace-nowrap">
                {item.shortLabel}
              </span>
            </button>
          );
        })}

        {/* 5th Button: More / System Drawer for mobile */}
        <button
          onClick={() => setIsMoreOpen((prev) => !prev)}
          className={`relative flex flex-col items-center justify-center min-w-[62px] xs:min-w-[68px] min-h-[48px] py-1 px-2 rounded-2xl transition-all ${
            isMoreOpen || activeView === 'admin'
              ? 'text-[#1E54B7] bg-[#E1FA4A] font-black shadow-lg scale-105'
              : 'text-white/80 hover:text-white active:scale-95'
          }`}
          aria-label="More Navigation Options"
          aria-expanded={isMoreOpen}
        >
          <MoreHorizontal className="w-5 h-5" />
          <span className="text-[10px] xs:text-[11px] mt-0.5 font-bold tracking-tight whitespace-nowrap">
            More
          </span>
        </button>
      </nav>

      {/* Mobile "More" Drawer Action Sheet */}
      {isMoreOpen && (
        <div
          className="md:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex flex-col justify-end"
          onClick={() => setIsMoreOpen(false)}
        >
          <div
            className="w-full bg-[#1E54B7] border-t-2 border-white/25 rounded-t-[32px] p-6 pb-safe shadow-2xl animate-sheet-up space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Sheet Handle and Title */}
            <div className="flex items-center justify-between pb-2 border-b border-white/15">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#E1FA4A]" />
                <span className="font-bold text-sm text-white uppercase tracking-wider">
                  DrishtiAI Quick Switcher
                </span>
              </div>
              <button
                onClick={() => setIsMoreOpen(false)}
                className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center text-white/80 hover:text-white hover:bg-white/25 transition-all cursor-pointer"
                aria-label="Close menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Actions List */}
            <div className="space-y-2.5">
              <button
                onClick={() => {
                  setIsMoreOpen(false);
                  setActiveView('admin');
                }}
                className="w-full flex items-center justify-between p-3.5 rounded-2xl bg-white/15 hover:bg-white/25 active:bg-white/30 border border-white/25 text-white transition-all cursor-pointer shadow-sm"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#E1FA4A] text-black flex items-center justify-center font-bold shadow-sm">
                    ⚡
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold flex items-center gap-2">
                      <span>MLOps Platform</span>
                      <span className="w-2 h-2 rounded-full bg-[#E1FA4A] animate-pulse"></span>
                    </div>
                    <div className="text-[11px] text-white/75">
                      Model registry, training jobs, drift telemetry &amp; approvals
                    </div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-[#E1FA4A]" />
              </button>

              <button
                onClick={() => {
                  setIsMoreOpen(false);
                  setActiveView('landing');
                }}
                className="w-full flex items-center justify-between p-3.5 rounded-2xl bg-white/10 hover:bg-white/20 active:bg-white/25 border border-white/20 text-white transition-all cursor-pointer shadow-sm"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-white/20 text-white flex items-center justify-center font-bold">
                    <ExternalLink className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold">Product Landing Page</div>
                    <div className="text-[11px] text-white/75">
                      Clinical proof points, live demo, FAQ &amp; specifications
                    </div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-white/60" />
              </button>
            </div>

            {/* Clinic Info & Offline Status Card */}
            <div className="p-4 rounded-2xl bg-white/10 border border-white/15 space-y-2 text-white">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-white/70">
                  Active Clinical Session
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] text-[#E1FA4A] font-mono font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#E1FA4A] animate-pulse"></span>
                  Gemma-4 Connected
                </span>
              </div>
              <p className="text-xs font-bold text-white">General Hospital - Mumbai</p>
              <div className="flex items-center justify-between pt-2 border-t border-white/15 text-[10px] font-mono text-white/80">
                <span>PWA Local Sync: OK</span>
                <span className="text-[#E1FA4A] font-bold">WCAG AAA Compliant</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

