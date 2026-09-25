import React, { useState } from 'react';
import {
  ArrowLeft,
  Microscope,
  Calendar,
  Activity,
  FileDown,
  Phone,
  MapPin,
  FileText,
  History,
  ShieldCheck,
  Heart,
  Droplets,
  User,
  Clock,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { DR_STAGES, ScanAnalysis, TimelineEvent } from '../types';
import { DualCodedBadge } from './DualCodedBadge';
import { generateLargePrintPDF } from '../utils/pdfGenerator';
import { ImageLightboxModal } from './ImageLightboxModal';
import { PatientTimeline } from './PatientTimeline';

export const PatientDetailView: React.FC = () => {
  const {
    activePatient,
    setActiveView,
    setActiveScan,
  } = useMedicalData();

  const [selectedScanForLightbox, setSelectedScanForLightbox] = useState<ScanAnalysis | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'archive'>('timeline');

  if (!activePatient) {
    return (
      <div className="p-8 text-center bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-4">
        <p className="text-gray-600 font-bold">No patient selected.</p>
        <button
          onClick={() => setActiveView('patients')}
          className="px-6 py-3 rounded-full bg-[#E1FA4A] text-black font-black text-xs uppercase tracking-wider shadow-md hover:scale-105 transition-all cursor-pointer"
        >
          Return to Patient Directory
        </button>
      </div>
    );
  }

  const scans = activePatient.scans || [];
  const latestScan = scans.length > 0 ? scans[0] : null;

  // Convert scans into chronological timeline events (oldest to newest)
  const sortedScans = [...scans].reverse();
  const timelineEvents: TimelineEvent[] = sortedScans.map((scan, idx) => {
    const prevScan = idx > 0 ? sortedScans[idx - 1] : null;
    const stageDelta = prevScan ? scan.detection.stage - prevScan.detection.stage : null;
    const isReferable = scan.detection.stage >= 2;
    const isUrgent = scan.detection.stage >= 3;

    const baseRisk = scan.detection.stage === 0 ? 0.10 : scan.detection.stage === 1 ? 0.18 : scan.detection.stage === 2 ? 0.40 : scan.detection.stage === 3 ? 0.65 : 0.82;
    const hba1cRisk = (activePatient.hba1c >= 8.0 ? 0.08 : 0.0) + (stageDelta && stageDelta > 0 ? 0.12 : 0.0);
    const sixM = Math.min(0.95, baseRisk + hba1cRisk);
    const twelveM = Math.min(0.98, sixM + 0.10);
    const riskCat = sixM >= 0.60 ? 'HIGH' : sixM >= 0.30 ? 'MODERATE' : 'LOW';

    return {
      scan_id: scan.analysis_id,
      patient_id: activePatient.id,
      date: scan.scan_date,
      stage: scan.detection.stage,
      stage_name: scan.detection.stage_name,
      confidence: scan.detection.confidence,
      severity: scan.detection.severity,
      stage_delta: stageDelta,
      progression: {
        engine: 'deterministic_progression_v1',
        observed_data: {
          current_stage: scan.detection.stage,
          previous_stage: prevScan ? prevScan.detection.stage : null,
          stage_delta: stageDelta,
          current_confidence: scan.detection.confidence,
        },
        predicted_risk: {
          risk_category: riskCat,
          six_month_risk: Number(sixM.toFixed(3)),
          twelve_month_risk: Number(twelveM.toFixed(3)),
          supporting_factors: [
            ...(stageDelta && stageDelta > 0 ? ['Worsening retinal grade'] : ['Current retinal grade']),
            ...(activePatient.hba1c >= 8.0 ? ['Suboptimal glycemic control (HbA1c >= 8.0)'] : []),
            ...(activePatient.diabetes_duration >= 10 ? ['Diabetes duration >= 10 years'] : []),
          ],
          uncertainty_flags: prevScan ? [] : ['Limited longitudinal history'],
        },
        clinical_recommendation: {
          follow_up_priority: isUrgent ? 'HIGH' : isReferable ? 'MEDIUM' : 'LOW',
          human_review_recommended: isReferable || !prevScan,
          note: 'Assistive screening progression estimate. Clinician oversight required.',
        },
      },
      referral: {
        priority: isUrgent ? 'URGENT' : isReferable ? 'EARLY' : 'ROUTINE',
        reasonCodes: [
          ...(scan.detection.stage >= 4 ? ['STAGE_PROLIFERATIVE'] : scan.detection.stage >= 3 ? ['STAGE_SEVERE'] : scan.detection.stage >= 2 ? ['STAGE_REFERABLE'] : ['STAGE_LOW']),
          ...(riskCat === 'HIGH' ? ['PROGRESSION_HIGH_RISK'] : []),
          'DOCTOR_REVIEW_PENDING',
        ],
        humanReviewRequired: isReferable,
        disclaimer: 'Triage priority is a decision-support policy recommendation.',
      },
      image_thumbnail: scan.images.original,
    };
  });

  const handleStartScan = () => {
    setActiveScan(null);
    setActiveView('new-scan');
  };

  const handleInspectScan = (scan: ScanAnalysis) => {
    setActiveScan(scan);
    setActiveView('new-scan');
  };

  return (
    <div className="space-y-4 sm:space-y-6 animate-fadeIn text-white">
      {/* Top Breadcrumb & Actions — compact on mobile */}
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={() => setActiveView('patients')}
          className="inline-flex items-center gap-1.5 px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-full bg-white/20 hover:bg-white/30 backdrop-blur-md border border-white/40 text-white font-bold text-[11px] sm:text-xs uppercase tracking-wider transition-all cursor-pointer shadow-sm"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span className="hidden xs:inline">Back</span>
          <span className="xs:hidden">←</span>
        </button>

        <button
          onClick={handleStartScan}
          className="inline-flex items-center gap-1.5 px-4 sm:px-7 py-2.5 sm:py-3.5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-[11px] sm:text-xs uppercase tracking-wider shadow-xl hover:scale-105 transition-all cursor-pointer"
        >
          <Microscope className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          <span className="hidden sm:inline">New Scan for {activePatient.name.split(' ')[0]} ↗</span>
          <span className="sm:hidden">New Scan ↗</span>
        </button>
      </div>

      {/* ═══ Patient Profile Hero Card — Mobile-First Redesign ═══ */}
      <div className="bg-white text-black rounded-2xl sm:rounded-[36px] shadow-2xl border border-gray-100 sm:border-4 sm:border-white overflow-hidden">
        {/* Patient Identity Header */}
        <div className="p-4 sm:p-8 space-y-4 sm:space-y-6">
          {/* Name Row */}
          <div className="space-y-2.5">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h1 className="text-xl sm:text-4xl font-black text-black font-sans leading-tight truncate">
                  {activePatient.name}
                </h1>
                <span className="inline-block text-[10px] sm:text-xs font-mono font-bold text-[#1E54B7] bg-sky-50 px-2 py-0.5 rounded-md mt-1">
                  {activePatient.id}
                </span>
              </div>
              {latestScan && (
                <div className="shrink-0">
                  <DualCodedBadge stage={latestScan.detection.stage} size="sm" showDetails />
                </div>
              )}
            </div>

            {/* Demographics — clean stacked rows on mobile */}
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] sm:text-sm text-gray-500 font-medium">
              <span className="inline-flex items-center gap-1">
                <User className="w-3 h-3 text-gray-400" />
                <strong className="text-black">{activePatient.age}</strong>, {activePatient.gender}
              </span>
              <span className="inline-flex items-center gap-1">
                <Clock className="w-3 h-3 text-gray-400" />
                Diabetes: <strong className="text-black">{activePatient.diabetes_duration}y</strong>
              </span>
              {activePatient.phone && (
                <span className="inline-flex items-center gap-1">
                  <Phone className="w-3 h-3 text-[#1E54B7]" />
                  {activePatient.phone}
                </span>
              )}
              {activePatient.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-[#1E54B7]" />
                  {activePatient.location}
                </span>
              )}
            </div>
          </div>

          {/* ── Glycemic Vitals — Card-in-card with proper mobile sizing ── */}
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            <div className="p-3 sm:p-4 rounded-xl sm:rounded-3xl bg-gradient-to-br from-gray-50 to-gray-100/50 border border-gray-200/60">
              <div className="flex items-center gap-1.5 mb-1">
                <Heart className="w-3 h-3 text-rose-400" />
                <span className="text-[9px] sm:text-[10px] font-black uppercase text-gray-500 tracking-wider">HbA1c</span>
              </div>
              <span className="text-2xl sm:text-3xl font-black text-black font-mono block leading-none">
                {activePatient.hba1c}%
              </span>
              <span className={`text-[9px] sm:text-[10px] font-bold mt-1 block ${activePatient.hba1c >= 8 ? 'text-rose-600' : 'text-amber-600'}`}>
                {activePatient.hba1c >= 8 ? 'High Risk' : 'Managed'}
              </span>
            </div>

            <div className="p-3 sm:p-4 rounded-xl sm:rounded-3xl bg-gradient-to-br from-gray-50 to-gray-100/50 border border-gray-200/60">
              <div className="flex items-center gap-1.5 mb-1">
                <Droplets className="w-3 h-3 text-blue-400" />
                <span className="text-[9px] sm:text-[10px] font-black uppercase text-gray-500 tracking-wider">Glucose</span>
              </div>
              <span className="text-2xl sm:text-3xl font-black text-black font-mono block leading-none">
                {activePatient.sugar_level}
              </span>
              <span className="text-[9px] sm:text-[10px] font-bold text-gray-500 mt-1 block">mg/dL fasting</span>
            </div>
          </div>

          {/* Clinical Notes — collapsible feel */}
          {activePatient.notes && (
            <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-sky-50/80 border border-sky-100 text-[11px] sm:text-sm text-gray-700 flex items-start gap-2.5">
              <FileText className="w-3.5 h-3.5 text-[#1E54B7] shrink-0 mt-0.5" />
              <div className="min-w-0">
                <strong className="text-black text-[11px] sm:text-xs block mb-0.5">Notes</strong>
                <p className="leading-relaxed">{activePatient.notes}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ View Switcher — Short mobile labels ═══ */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar -mx-1 px-1">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-1.5 px-4 sm:px-6 py-2.5 sm:py-3 rounded-full font-bold text-[11px] sm:text-xs uppercase tracking-wider transition-all cursor-pointer whitespace-nowrap shrink-0 ${
            activeTab === 'timeline'
              ? 'bg-white text-black shadow-lg scale-105'
              : 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-md border border-white/30'
          }`}
        >
          <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          <span className="hidden sm:inline">Longitudinal Trajectory & Triage</span>
          <span className="sm:hidden">Trajectory</span>
        </button>

        <button
          onClick={() => setActiveTab('archive')}
          className={`flex items-center gap-1.5 px-4 sm:px-6 py-2.5 sm:py-3 rounded-full font-bold text-[11px] sm:text-xs uppercase tracking-wider transition-all cursor-pointer whitespace-nowrap shrink-0 ${
            activeTab === 'archive'
              ? 'bg-white text-black shadow-lg scale-105'
              : 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-md border border-white/30'
          }`}
        >
          <History className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          <span className="hidden sm:inline">Diagnostic Scan Archive ({scans.length})</span>
          <span className="sm:hidden">Scans ({scans.length})</span>
        </button>
      </div>

      {/* ═══ Main Content Area ═══ */}
      {activeTab === 'timeline' ? (
        <div className="p-4 sm:p-8 bg-white text-black rounded-2xl sm:rounded-[36px] shadow-2xl border border-gray-100 sm:border-4 sm:border-white space-y-4 sm:space-y-6">
          <div>
            <h2 className="text-lg sm:text-2xl font-bold text-black flex items-center gap-2 font-sans">
              <Activity className="w-5 h-5 sm:w-6 sm:h-6 text-[#1E54B7]" />
              <span className="hidden sm:inline">Longitudinal Retinal Progression & Triage</span>
              <span className="sm:hidden">Progression & Triage</span>
            </h2>
            <p className="text-[11px] sm:text-sm text-gray-500 mt-1 leading-relaxed">
              <span className="hidden sm:inline">Deterministic progression risk estimation, microvascular trajectory, and specialist referral triage</span>
              <span className="sm:hidden">Risk progression and specialist referral triage</span>
            </p>
          </div>

          <PatientTimeline
            events={timelineEvents}
            onSelectScan={(scanId) => {
              const target = scans.find((s) => s.analysis_id === scanId);
              if (target) handleInspectScan(target);
            }}
          />
        </div>
      ) : (
        /* ═══ Diagnostic Scan Archive ═══ */
        <div className="p-4 sm:p-8 bg-white text-black rounded-2xl sm:rounded-[36px] shadow-2xl border border-gray-100 sm:border-4 sm:border-white space-y-4 sm:space-y-6">
          <div>
            <h2 className="text-lg sm:text-2xl font-bold text-black flex items-center gap-2 font-sans">
              <History className="w-5 h-5 sm:w-6 sm:h-6 text-[#1E54B7]" />
              <span className="hidden sm:inline">Historical Scan Records</span>
              <span className="sm:hidden">Scan History</span>
            </h2>
            <p className="text-[11px] sm:text-sm text-gray-500 mt-1">
              <span className="hidden sm:inline">Complete archives of AI heatmap activations, segmented vasculature, and full clinical reports</span>
              <span className="sm:hidden">AI heatmaps, vasculature & clinical reports</span>
            </p>
          </div>

          {scans.length === 0 ? (
            <div className="p-6 sm:p-8 text-center bg-gray-50 rounded-xl sm:rounded-2xl border border-gray-200 text-gray-500 text-sm">
              No historical scans recorded yet.
            </div>
          ) : (
            <div className="space-y-4 sm:space-y-6">
              {scans.map((scan) => {
                const meta = DR_STAGES[scan.detection.stage];
                return (
                  <div
                    key={scan.analysis_id}
                    className="p-3.5 sm:p-6 bg-gray-50/70 border border-gray-200 hover:border-[#1E54B7] hover:bg-white rounded-xl sm:rounded-3xl space-y-3 sm:space-y-4 transition-all shadow-sm"
                  >
                    {/* Scan Header — stacked on mobile */}
                    <div className="space-y-2 sm:space-y-0 sm:flex sm:items-center sm:justify-between sm:gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] sm:text-xs font-mono font-bold text-gray-600 flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-[#1E54B7]" />
                            {scan.scan_date}
                          </span>
                          <span className="text-[10px] text-gray-400 font-mono hidden sm:inline">
                            ({scan.analysis_id})
                          </span>
                        </div>
                        <h3 className="text-sm sm:text-lg font-bold text-black mt-0.5">
                          {meta.name}
                        </h3>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleInspectScan(scan)}
                          className="flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-full bg-sky-100 hover:bg-[#1E54B7] text-[#1E54B7] hover:text-white text-[11px] sm:text-xs font-black transition-all cursor-pointer text-center"
                        >
                          <span className="hidden sm:inline">View Full AI Report →</span>
                          <span className="sm:hidden">AI Report →</span>
                        </button>
                        <button
                          onClick={() => generateLargePrintPDF(scan, activePatient)}
                          className="p-2 rounded-full bg-white hover:bg-gray-100 text-gray-700 border border-gray-200 shadow-sm cursor-pointer shrink-0"
                          title="Download Patient PDF"
                        >
                          <FileDown className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Scan Images — 3-up grid with smaller gap on mobile */}
                    <div className="grid grid-cols-3 gap-1.5 sm:gap-3">
                      <div
                        className="aspect-square rounded-lg sm:rounded-2xl bg-black overflow-hidden border border-white/50 sm:border-2 sm:border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.original}
                          alt="Original"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                      <div
                        className="aspect-square rounded-lg sm:rounded-2xl bg-black overflow-hidden border border-white/50 sm:border-2 sm:border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.vessels}
                          alt="Vessels"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                      <div
                        className="aspect-square rounded-lg sm:rounded-2xl bg-black overflow-hidden border border-white/50 sm:border-2 sm:border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.heatmap}
                          alt="Heatmap"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                    </div>

                    {/* Clinical Summary — stacked on mobile */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 text-[11px] sm:text-xs text-gray-700 pt-2.5 sm:pt-3 border-t border-gray-200">
                      <div>
                        <span className="text-gray-500 font-bold block text-[10px] sm:text-xs">AI Note:</span>
                        <p className="mt-0.5 line-clamp-2 leading-relaxed">{scan.report.current_diagnosis.plain_language}</p>
                      </div>
                      <div className="flex gap-3 sm:block sm:space-y-1 font-mono text-[10px] sm:text-xs">
                        <div>Density: <strong className="text-black">{scan.vessel_stats.vessel_density_percent}%</strong></div>
                        <div>Urgency: <strong className="text-amber-800">{scan.report.urgency}</strong></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lightbox for History Scans */}
      {selectedScanForLightbox && (
        <ImageLightboxModal
          isOpen={!!selectedScanForLightbox}
          onClose={() => setSelectedScanForLightbox(null)}
          originalUrl={selectedScanForLightbox.images.original}
          vesselUrl={selectedScanForLightbox.images.vessels}
          heatmapUrl={selectedScanForLightbox.images.heatmap}
          title={`Historical Scan Inspection (${selectedScanForLightbox.scan_date})`}
          patientName={activePatient.name}
          stageName={selectedScanForLightbox.detection.stage_name}
        />
      )}
    </div>
  );
};
