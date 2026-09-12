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
    <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <button
          onClick={() => setActiveView('patients')}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-white/20 hover:bg-white/30 backdrop-blur-md border border-white/40 text-white font-bold text-xs uppercase tracking-wider transition-all cursor-pointer shadow-sm self-start sm:self-auto"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Directory</span>
        </button>

        <button
          onClick={handleStartScan}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 sm:px-7 py-3 sm:py-3.5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-xs uppercase tracking-wider shadow-xl hover:scale-105 transition-all cursor-pointer"
        >
          <Microscope className="w-4 h-4" />
          <span>Perform New Scan for {activePatient.name.split(' ')[0]} ↗</span>
        </button>
      </div>

      {/* Patient Profile Hero Card */}
      <div className="p-5 sm:p-8 bg-white text-black rounded-3xl sm:rounded-[36px] shadow-2xl border-2 sm:border-4 border-white space-y-5 sm:space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl sm:text-4xl font-black text-black font-sans">
                {activePatient.name}
              </h1>
              <span className="text-xs font-mono font-bold text-[#1E54B7] bg-sky-100 px-3 py-1 rounded-full">
                {activePatient.id}
              </span>
              {latestScan && (
                <DualCodedBadge stage={latestScan.detection.stage} size="sm" showDetails />
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-gray-600 font-medium">
              <span>Age: <strong className="text-black font-bold">{activePatient.age}</strong> ({activePatient.gender})</span>
              <span>•</span>
              <span>Diabetes Duration: <strong className="text-black font-bold">{activePatient.diabetes_duration} Years</strong></span>
              {activePatient.phone && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5 text-[#1E54B7]" /> {activePatient.phone}</span>
                </>
              )}
              {activePatient.location && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5 text-[#1E54B7]" /> {activePatient.location}</span>
                </>
              )}
            </div>
          </div>

          {/* Key Glycemic Metrics */}
          <div className="grid grid-cols-2 gap-3 shrink-0">
            <div className="p-4 rounded-3xl bg-gray-50 border border-gray-200 text-center min-w-[130px]">
              <span className="text-[10px] font-black uppercase text-gray-500 block">HbA1c Level</span>
              <span className="text-3xl font-black text-black font-mono mt-1 block">
                {activePatient.hba1c}%
              </span>
              <span className={`text-[10px] font-bold ${activePatient.hba1c >= 8 ? 'text-rose-600' : 'text-amber-700'}`}>
                {activePatient.hba1c >= 8 ? 'High Glycemic Risk' : 'Borderline Managed'}
              </span>
            </div>

            <div className="p-4 rounded-3xl bg-gray-50 border border-gray-200 text-center min-w-[130px]">
              <span className="text-[10px] font-black uppercase text-gray-500 block">Fasting Glucose</span>
              <span className="text-3xl font-black text-black font-mono mt-1 block">
                {activePatient.sugar_level}
              </span>
              <span className="text-[10px] font-bold text-gray-500">mg / dL</span>
            </div>
          </div>
        </div>

        {activePatient.notes && (
          <div className="p-4 rounded-2xl bg-sky-50 border border-sky-100 text-xs sm:text-sm text-gray-800 flex items-start gap-3">
            <FileText className="w-4 h-4 text-[#1E54B7] shrink-0 mt-0.5" />
            <div>
              <strong className="text-black block mb-0.5">Clinical Case Notes:</strong>
              {activePatient.notes}
            </div>
          </div>
        )}
      </div>

      {/* View Switcher Tabs: Longitudinal Timeline vs Individual Scan Archive */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold text-xs uppercase tracking-wider transition-all cursor-pointer ${
            activeTab === 'timeline'
              ? 'bg-white text-black shadow-lg scale-105'
              : 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-md border border-white/30'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Longitudinal Trajectory & Triage</span>
        </button>

        <button
          onClick={() => setActiveTab('archive')}
          className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold text-xs uppercase tracking-wider transition-all cursor-pointer ${
            activeTab === 'archive'
              ? 'bg-white text-black shadow-lg scale-105'
              : 'bg-white/20 hover:bg-white/30 text-white backdrop-blur-md border border-white/30'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Diagnostic Scan Archive ({scans.length})</span>
        </button>
      </div>

      {/* Main Longitudinal Trajectory Content */}
      {activeTab === 'timeline' ? (
        <div className="p-7 sm:p-8 bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-6">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-black flex items-center gap-2 font-sans">
              <Activity className="w-6 h-6 text-[#1E54B7]" />
              Longitudinal Retinal Progression & Triage
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 mt-1">
              Deterministic progression risk estimation, microvascular trajectory, and specialist referral triage
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
        /* Diagnostic Scan Archive */
        <div className="p-7 sm:p-8 bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-6">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-black flex items-center gap-2 font-sans">
              <History className="w-6 h-6 text-[#1E54B7]" />
              Historical Scan Records
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 mt-1">
              Complete archives of AI heatmap activations, segmented vasculature, and full clinical reports
            </p>
          </div>

          {scans.length === 0 ? (
            <div className="p-8 text-center bg-gray-50 rounded-2xl border border-gray-200 text-gray-500 text-sm">
              No historical scans recorded for this patient yet.
            </div>
          ) : (
            <div className="space-y-6">
              {scans.map((scan) => {
                const meta = DR_STAGES[scan.detection.stage];
                return (
                  <div
                    key={scan.analysis_id}
                    className="p-6 bg-gray-50/70 border border-gray-200 hover:border-[#1E54B7] hover:bg-white rounded-3xl space-y-4 transition-all shadow-sm"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono font-bold text-gray-600 flex items-center gap-1.5">
                            <Calendar className="w-4 h-4 text-[#1E54B7]" />
                            {scan.scan_date}
                          </span>
                          <span className="text-xs text-gray-400 font-mono">
                            ({scan.analysis_id})
                          </span>
                        </div>
                        <h3 className="text-lg font-bold text-black mt-1">
                          Diagnostic Result: {meta.name}
                        </h3>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleInspectScan(scan)}
                          className="px-4 py-2 rounded-full bg-sky-100 hover:bg-[#1E54B7] text-[#1E54B7] hover:text-white text-xs font-black transition-all cursor-pointer"
                        >
                          View Full AI Report →
                        </button>
                        <button
                          onClick={() => generateLargePrintPDF(scan, activePatient)}
                          className="p-2 rounded-full bg-white hover:bg-gray-100 text-gray-700 border border-gray-200 shadow-sm cursor-pointer"
                          title="Download Patient PDF"
                        >
                          <FileDown className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Scan Triptych Thumbnail Preview */}
                    <div className="grid grid-cols-3 gap-3">
                      <div
                        className="aspect-square rounded-2xl bg-black overflow-hidden border-2 border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.original}
                          alt="Original"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                      <div
                        className="aspect-square rounded-2xl bg-black overflow-hidden border-2 border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.vessels}
                          alt="Vessels"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                      <div
                        className="aspect-square rounded-2xl bg-black overflow-hidden border-2 border-white shadow-md cursor-pointer"
                        onClick={() => setSelectedScanForLightbox(scan)}
                      >
                        <img
                          src={scan.images.heatmap}
                          alt="Heatmap"
                          className="w-full h-full object-cover hover:scale-105 transition-transform"
                        />
                      </div>
                    </div>

                    {/* Clinical Summary & Microvascular Vitals */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700 pt-3 border-t border-gray-200">
                      <div>
                        <span className="text-gray-500 font-bold block">AI Plain Language Note:</span>
                        <p className="mt-0.5 line-clamp-2">{scan.report.current_diagnosis.plain_language}</p>
                      </div>
                      <div className="space-y-1 font-mono">
                        <div>Vessel Density: <strong className="text-black">{scan.vessel_stats.vessel_density_percent}%</strong></div>
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
