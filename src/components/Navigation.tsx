import React from 'react';
import { LayoutDashboard, Microscope, Layers, Users } from 'lucide-react';
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
      {/* Desktop Left Sidebar (240px wide) */}
      <aside
        className="hidden md:flex flex-col w-64 shrink-0 bg-white/10 backdrop-blur-2xl border-r border-white/15 min-h-[calc(100vh-72px)] p-4 gap-2 select-none text-white"
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
            onClick={() => setActiveView('landing')}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-white/10 hover:bg-white/18 active:bg-white/25 border border-white/15 text-xs font-semibold text-white/90 btn-clinical cursor-pointer focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#1E54B7]"
          >
            <span>Landing Page</span>
            <span className="text-[#E1FA4A] font-bold">Overview ↗</span>
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

      {/* Mobile & Tablet Bottom Sticky Navigation Bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#619FE8]/95 backdrop-blur-2xl border-t border-white/30 px-3 py-2 flex items-center justify-around shadow-2xl"
        role="navigation"
        aria-label="Mobile Navigation"
      >
        {navItems.map((item) => {
          const isActive = activeView === item.id || (item.id === 'patients' && activeView === 'patient-detail');
          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`relative flex flex-col items-center justify-center min-w-[70px] min-h-[50px] py-1 px-2.5 rounded-2xl transition-all ${
                isActive
                  ? 'text-[#1E54B7] bg-white font-black shadow-lg scale-105'
                  : 'text-white/80 hover:text-white'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                {item.icon}
                {item.id === 'batch-screening' && batchQueue.length > 0 && (
                  <span className="absolute -top-1.5 -right-2 w-4 h-4 rounded-full bg-[#E1FA4A] text-black text-[9px] font-mono font-black flex items-center justify-center shadow-sm">
                    {batchQueue.length}
                  </span>
                )}
              </div>
              <span className="text-[11px] mt-0.5 font-bold tracking-tight whitespace-nowrap">
                {item.shortLabel}
              </span>
            </button>
          );
        })}
      </nav>
    </>
  );
};
