import React, { useState } from 'react';
import {
  Eye,
  Volume2,
  VolumeX,
  Sun,
  Moon,
  Contrast,
  Type,
  Settings,
  Sparkles,
} from 'lucide-react';
import { useAccessibility, FontSizeScale } from '../context/AccessibilityContext';
import { useMedicalData } from '../context/MedicalDataContext';
import { BackendSettingsModal } from './BackendSettingsModal';

export const AccessibilityToolbar: React.FC = () => {
  const {
    theme,
    fontSize,
    highContrast,
    isSpeaking,
    toggleTheme,
    setFontSize,
    toggleContrast,
    speak,
    stopSpeech,
  } = useAccessibility();

  const { activeView, setActiveView, activePatient, activeScan, dashboardStats, backendStatus } = useMedicalData();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleReadScreen = () => {
    if (isSpeaking) {
      stopSpeech();
      return;
    }

    let speechText = '';
    if (activeView === 'dashboard') {
      speechText = `DrishtiAI Clinical Dashboard. Total patients screened: ${dashboardStats.total_patients}. High risk cases requiring immediate attention: ${dashboardStats.high_risk_cases}. Treatment referrals needed: ${dashboardStats.referrals_needed}. AI Diagnostic Accuracy: ${dashboardStats.diagnostic_accuracy} percent. To begin screening, select Start New Scan.`;
    } else if (activeView === 'new-scan') {
      if (activeScan) {
        speechText = `Retinal Analysis Results for ${activeScan.patient_name || 'Patient'}. Diagnosis: ${activeScan.detection.stage_name}. Confidence: ${activeScan.detection.confidence} percent. Clinical Urgency: ${activeScan.report.urgency}. ${activeScan.report.current_diagnosis.plain_language} Recommended follow up: ${activeScan.report.recommended_follow_up}.`;
      } else {
        speechText = `DrishtiAI New Retinal Scan Screening Workflow. Step 1: Assign a patient. Step 2: Upload or drag and drop a retinal fundus image or choose a preset case. Then select Run Full AI Analysis.`;
      }
    } else if (activeView === 'batch-screening') {
      speechText = `DrishtiAI Mobile Camp Batch Screening Queue. Manage multiple patient retinal scans simultaneously with real-time queue processing.`;
    } else if (activeView === 'patients') {
      speechText = `Patient Records Directory. Search and filter patients by Diabetic Retinopathy severity and review longitudinal HbA1c histories.`;
    } else if (activeView === 'patient-detail' && activePatient) {
      speechText = `Patient Profile for ${activePatient.name}. Age ${activePatient.age}. Diabetes duration: ${activePatient.diabetes_duration} years. Latest fasting sugar: ${activePatient.sugar_level} mg per dL. HbA1c: ${activePatient.hba1c} percent. Past retinal scans on record: ${activePatient.scans?.length || 0}.`;
    } else {
      speechText = `Welcome to DrishtiAI, an accessible medical AI dashboard for Diabetic Retinopathy screening.`;
    }

    speak(speechText);
  };

  return (
    <>
      <header
        className="sticky top-0 z-40 w-full min-h-[64px] sm:min-h-[72px] bg-[#619FE8]/85 backdrop-blur-2xl border-b border-white/10 text-white flex items-center transition-all pt-safe"
        role="region"
        aria-label="Accessibility and Primary Toolbar"
      >
        <div className="w-full px-3 sm:px-6 lg:px-8 py-2 flex items-center justify-between gap-2 sm:gap-4">
          {/* Brand & Suite Subtitle */}
          <div
            onClick={() => setActiveView(activeView === 'landing' ? 'dashboard' : 'landing')}
            className="flex items-center gap-2.5 sm:gap-3.5 cursor-pointer group select-none min-w-0"
            title="Click to view Product Landing Page"
          >
            <div className="w-8 h-8 sm:w-9 sm:h-9 bg-sky-100 border border-sky-300 group-hover:scale-105 rounded-xl flex items-center justify-center shrink-0 transition-transform shadow-sm">
              <Eye className="w-4 h-4 sm:w-4.5 sm:h-4.5 text-[#1E54B7] stroke-[2]" />
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="text-lg sm:text-xl font-bold tracking-tight text-white truncate" style={{ fontFamily: 'var(--font-heading)' }}>
                  DrishtiAI
                </span>
                <span className="inline-flex items-center gap-1 text-[8px] sm:text-[9px] font-semibold uppercase tracking-wider px-1.5 sm:px-2 py-0.5 rounded-md bg-sky-100 text-[#22D3EE] border border-sky-200 shrink-0">
                  <Sparkles className="w-2.5 h-2.5" />
                  Gemma-4
                </span>
              </div>
              <span className="hidden sm:block text-[9px] uppercase tracking-[0.12em] text-white/60 font-medium truncate">
                Diabetic Retinopathy Clinical Suite
              </span>
            </div>
          </div>

          {/* Right-Aligned Accessibility & Mode Controls */}
          <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
            {/* Font Scale Switcher: [STD] [A+] [A++] */}
            <div
              className="flex bg-white/10 backdrop-blur-md rounded-lg border border-white/15 p-0.5"
              role="group"
              aria-label="Font size scaling"
            >
              <button
                onClick={() => setFontSize('standard')}
                className={`px-2 sm:px-3 py-1 text-[10px] sm:text-xs font-black rounded-md transition-all cursor-pointer ${
                  fontSize === 'standard'
                    ? 'bg-[#1E54B7] text-white shadow-sm'
                    : 'text-white/70 font-medium hover:text-white hover:bg-white/10'
                }`}
                aria-pressed={fontSize === 'standard'}
                title="Standard Text Size"
              >
                STD
              </button>
              <button
                onClick={() => setFontSize('large')}
                className={`px-2 sm:px-3 py-1 text-[10px] sm:text-xs font-black rounded-md transition-all cursor-pointer ${
                  fontSize === 'large'
                    ? 'bg-[#1E54B7] text-white shadow-sm'
                    : 'text-white/70 font-medium hover:text-white hover:bg-white/10'
                }`}
                aria-pressed={fontSize === 'large'}
                title="Large Text Size (A+)"
              >
                A+
              </button>
              <button
                onClick={() => setFontSize('xlarge')}
                className={`px-2 sm:px-3 py-1 text-[10px] sm:text-xs font-black rounded-md transition-all cursor-pointer ${
                  fontSize === 'xlarge'
                    ? 'bg-[#1E54B7] text-white shadow-sm'
                    : 'text-white/70 font-medium hover:text-white hover:bg-white/10'
                }`}
                aria-pressed={fontSize === 'xlarge'}
                title="Extra Large Text Size (A++)"
              >
                A++
              </button>
            </div>

            {/* High Contrast Mode Toggle */}
            <button
              onClick={toggleContrast}
              className={`flex items-center justify-center gap-1 px-2.5 sm:px-3 h-8 sm:h-9 rounded-lg font-semibold text-[11px] uppercase tracking-wider transition-all cursor-pointer btn-clinical ${
                highContrast
                  ? 'bg-amber-400 text-black border border-amber-500'
                  : 'bg-white/10 hover:bg-white/15 border border-white/15 text-white/80'
              }`}
              aria-pressed={highContrast}
              title="Toggle High Contrast Mode"
            >
              <Contrast className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Contrast</span>
            </button>

            {/* Read Screen Speech Synthesizer Button */}
            <button
              onClick={handleReadScreen}
              className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 h-8 sm:h-9 rounded-lg font-bold text-[10px] sm:text-[11px] uppercase tracking-wider btn-clinical cursor-pointer ${
                isSpeaking
                  ? 'bg-[#DC2626] text-white animate-pulse'
                  : 'bg-[#E1FA4A] hover:bg-[#d6f236] text-black shadow-[0_2px_8px_rgba(22,163,74,0.3)]'
              }`}
              aria-label={isSpeaking ? 'Stop reading screen' : 'Read screen aloud'}
              title="Screen reader text-to-speech"
            >
              {isSpeaking ? (
                <>
                  <VolumeX className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline">Stop</span>
                </>
              ) : (
                <>
                  <Volume2 className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline">Read Screen</span>
                </>
              )}
            </button>

            {/* Settings Opener */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-white/10 hover:bg-white/20 border border-white/15 text-white/80 hover:text-white transition-all cursor-pointer btn-clinical"
              title="Backend & AI Settings"
              aria-label="Backend Connection Settings"
            >
              <Settings className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Backend Settings Modal */}
      <BackendSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
};
