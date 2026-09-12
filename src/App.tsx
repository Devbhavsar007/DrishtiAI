/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { AccessibilityProvider } from './context/AccessibilityContext';
import { MedicalDataProvider, useMedicalData } from './context/MedicalDataContext';
import { AccessibilityToolbar } from './components/AccessibilityToolbar';
import { Navigation } from './components/Navigation';
import { DashboardView } from './components/DashboardView';
import { NewScanView } from './components/NewScanView';
import { BatchScreeningView } from './components/BatchScreeningView';
import { PatientDirectoryView } from './components/PatientDirectoryView';
import { PatientDetailView } from './components/PatientDetailView';
import { LandingPageView } from './components/LandingPageView';
import { VideoSplash } from './components/VideoSplash';

// Intelligence Control Plane components
import { AdminLayout, AdminView } from './components/admin/AdminLayout';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { DataOverview } from './components/admin/DataOverview';
import { DatasetManager } from './components/admin/DatasetManager';
import { TrainingRuns } from './components/admin/TrainingRuns';
import { ModelRegistry } from './components/admin/ModelRegistry';
import { DriftMonitor } from './components/admin/DriftMonitor';
import { ApprovalWorkflow } from './components/admin/ApprovalWorkflow';
import { AuditLog } from './components/admin/AuditLog';
import { SystemHealth } from './components/admin/SystemHealth';
import { AdminRole } from './types';

const MainContent: React.FC = () => {
  const { activeView } = useMedicalData();

  if (activeView === 'landing') {
    return <LandingPageView />;
  }

  return (
    <main
      className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 pb-24 md:pb-12"
      id="main-content"
      role="main"
      aria-label="Clinical AI Workspace"
    >
      {activeView === 'dashboard' && <DashboardView />}
      {activeView === 'new-scan' && <NewScanView />}
      {activeView === 'batch-screening' && <BatchScreeningView />}
      {activeView === 'patients' && <PatientDirectoryView />}
      {activeView === 'patient-detail' && <PatientDetailView />}
    </main>
  );
};

export default function App() {
  return (
    <AccessibilityProvider>
      <MedicalDataProvider>
        <AppBody />
      </MedicalDataProvider>
    </AccessibilityProvider>
  );
}

const AppBody: React.FC = () => {
  const { activeView, setActiveView } = useMedicalData();
  const [adminView, setAdminView] = useState<AdminView>('dashboard');
  const [adminRole, setAdminRole] = useState<AdminRole>('SUPER_ADMIN');

  // Show cinematic video splash once per session
  const [showSplash, setShowSplash] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      // Skip splash if already seen this session, or if user prefers reduced motion
      if (sessionStorage.getItem('drishti_splash_seen') === '1') return false;
      if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return false;
      // Skip splash for admin/mlops views
      if (activeView === 'admin') return false;
    }
    return true;
  });

  // Cinematic intro — plays the DrishtiAI promo video once
  if (showSplash) {
    return <VideoSplash onComplete={() => setShowSplash(false)} />;
  }

  // Intelligence Control Plane Logical View
  if (activeView === 'admin') {
    return (
      <AdminLayout
        currentView={adminView}
        onSelectView={setAdminView}
        adminRole={adminRole}
        onRoleChange={setAdminRole}
        onExitAdmin={() => {
          if (typeof window !== 'undefined' && window.location.port === '3001') {
            window.location.href = `http://${window.location.hostname}:3000`;
          } else {
            setActiveView('dashboard');
          }
        }}
      >
        {adminView === 'dashboard' && <AdminDashboard onNavigate={setAdminView} />}
        {adminView === 'data' && <DataOverview />}
        {adminView === 'datasets' && <DatasetManager />}
        {adminView === 'training' && <TrainingRuns />}
        {adminView === 'models' && <ModelRegistry />}
        {adminView === 'drift' && <DriftMonitor />}
        {adminView === 'approvals' && <ApprovalWorkflow adminRole={adminRole} />}
        {adminView === 'audit' && <AuditLog />}
        {adminView === 'system' && <SystemHealth />}
      </AdminLayout>
    );
  }

  // Clinical Platform Landing View
  if (activeView === 'landing') {
    return (
      <div className="min-h-screen bg-[#619FE8] text-white transition-colors duration-150 font-sans selection:bg-[#E1FA4A] selection:text-black grain-overlay">
        <LandingPageView />
      </div>
    );
  }

  // Clinical Platform Workspace (Doctor / Technician / Health Worker)
  return (
    <div className="min-h-screen bg-[#619FE8] text-white transition-colors duration-150 flex flex-col font-sans selection:bg-[#E1FA4A] selection:text-black relative grain-overlay">
      {/* Skip link for screen-readers and keyboard navigators */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-[#1E54B7] focus:text-white focus:font-bold focus:rounded-lg focus:shadow-xl"
      >
        Skip to primary clinical workspace
      </a>

      {/* Top Accessibility & Action Toolbar */}
      <AccessibilityToolbar />

      {/* Body Container with Sidebar + Content */}
      <div className="flex-1 flex flex-row relative">
        <Navigation />
        <MainContent />
      </div>
    </div>
  );
};
