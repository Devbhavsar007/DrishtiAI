import React, { useState } from 'react';
import {
  Users,
  AlertTriangle,
  Hospital,
  Target,
  Microscope,
  ArrowRight,
  TrendingUp,
  Filter,
  Eye,
  X,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { DR_STAGES, DRStage, ScanAnalysis } from '../types';
import { DualCodedBadge } from './DualCodedBadge';

export const DashboardView: React.FC = () => {
  const { dashboardStats, setActiveView, setActiveScan, setActivePatient, patients } = useMedicalData();
  const [selectedStageFilter, setSelectedStageFilter] = useState<DRStage | 'all'>('all');

  const filteredScans =
    selectedStageFilter === 'all'
      ? dashboardStats.recent_scans
      : dashboardStats.recent_scans.filter(
          (scan) => scan.detection.stage === selectedStageFilter
        );

  const handleOpenScan = (scan: ScanAnalysis) => {
    setActiveScan(scan);
    const matchedPatient = patients.find((p) => p.id === scan.patient_id);
    if (matchedPatient) {
      setActivePatient(matchedPatient);
    }
    setActiveView('new-scan');
  };

  const handleOpenPatientDetail = (patientId: string) => {
    const matched = patients.find((p) => p.id === patientId);
    if (matched) {
      setActivePatient(matched);
      setActiveView('patient-detail');
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
      {/* 1. Header Banner & Quick Action */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-white" style={{ fontFamily: 'var(--font-heading)' }}>
            Clinical Overview
          </h1>
          <p className="text-white/80 text-xs sm:text-base font-normal max-w-2xl mt-0.5">
            Real-time screening metrics, microvascular risk distribution, and urgent ophthalmology triage queue.
          </p>
        </div>

        <button
          onClick={() => {
            setActiveScan(null);
            setActiveView('new-scan');
          }}
          className="bg-[#E1FA4A] hover:bg-[#d6f236] text-black px-6 sm:px-8 h-11 sm:h-12 rounded-xl font-semibold text-sm flex items-center justify-center gap-2.5 btn-clinical shrink-0 cursor-pointer shadow-[0_4px_12px_rgba(22,163,74,0.25)] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#E1FA4A] w-full sm:w-auto"
          aria-label="Start new retinal scan analysis"
        >
          <Microscope className="w-4.5 h-4.5 stroke-[2]" />
          <span>Start New Scan</span>
        </button>
      </header>

      {/* 2. Key Metrics Row (4 Enamel White Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4" data-reveal-stagger>
        {/* Card 1: Total Patients Screened */}
        <div className="bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-6 shadow-2xl border-2 sm:border-4 border-white flex flex-col justify-between hover:scale-[1.01] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Total Screened
              </p>
              <span className="w-9 h-9 rounded-2xl bg-sky-100 text-[#1E54B7] flex items-center justify-center font-bold">
                <Users className="w-4 h-4" />
              </span>
            </div>
            <p className="text-3xl sm:text-4xl font-extrabold font-mono text-black mt-3 animate-count-up">
              {dashboardStats.total_patients.toLocaleString()}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-emerald-600 text-xs font-bold">
            <TrendingUp className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>+12% volume this month</span>
          </div>
        </div>

        {/* Card 2: High Risk Cases (Stage 2+) */}
        <div className="bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-6 shadow-2xl border-2 sm:border-4 border-white relative overflow-hidden flex flex-col justify-between hover:scale-[1.01] transition-all">
          <div className="absolute top-4 right-4 flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-100 text-rose-700 text-[10px] font-black uppercase tracking-wide">
            <span className="w-1.5 h-1.5 bg-rose-600 rounded-full animate-pulse"></span>
            <span>Urgent</span>
          </div>
          <div>
            <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
              High Risk Cases
            </p>
            <p className="text-3xl sm:text-4xl font-extrabold font-mono text-[#D55E00] mt-3 animate-count-up">
              {dashboardStats.high_risk_cases}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 text-rose-600 text-xs font-bold flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Stages 3 & 4 detected</span>
          </div>
        </div>

        {/* Card 3: Referrals Pending */}
        <div className="bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-6 shadow-2xl border-2 sm:border-4 border-white flex flex-col justify-between hover:scale-[1.01] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Referrals Pending
              </p>
              <span className="w-9 h-9 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                <Hospital className="w-4 h-4" />
              </span>
            </div>
            <p className="text-3xl sm:text-4xl font-extrabold font-mono text-black mt-3 animate-count-up">
              {dashboardStats.referrals_needed}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 text-gray-500 text-xs font-medium">
            Avg triage turnaround: <strong className="text-black font-bold">48h</strong>
          </div>
        </div>

        {/* Card 4: AI Accuracy */}
        <div className="bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-6 shadow-2xl border-2 sm:border-4 border-white flex flex-col justify-between hover:scale-[1.01] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Model Accuracy
              </p>
              <span className="w-9 h-9 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <Target className="w-4 h-4" />
              </span>
            </div>
            <p className="text-3xl sm:text-4xl font-extrabold font-mono text-[#009E73] mt-3 animate-count-up">
              {dashboardStats.diagnostic_accuracy}%
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 text-gray-500 text-xs font-medium">
            EyePACS &amp; Messidor-2 Verified
          </div>
        </div>
      </div>

      {/* 3. Stage Distribution & Recent Scans Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6">
        {/* DR Stage Distribution */}
        <div className="lg:col-span-5 bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-7 shadow-2xl border-2 sm:border-4 border-white flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
                  <Eye className="w-4 h-4 stroke-[2.5]" />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-black font-sans">
                  DR Stage Distribution
                </h2>
              </div>
              {selectedStageFilter !== 'all' && (
                <button
                  onClick={() => setSelectedStageFilter('all')}
                  className="inline-flex items-center gap-1 text-xs font-black text-[#1E54B7] bg-sky-100 hover:bg-sky-200 px-3 py-1 rounded-full transition-all cursor-pointer"
                >
                  <span>Clear Filter</span>
                  <X className="w-3.5 h-3.5 stroke-[2.5]" />
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-5 leading-relaxed">
              Click any clinical stage below to filter active screening records in real time.
            </p>

            <div className="space-y-3.5">
              {([0, 1, 2, 3, 4] as DRStage[]).map((stageNum) => {
                const meta = DR_STAGES[stageNum];
                const dist = dashboardStats.stage_distribution[stageNum] || {
                  count: 0,
                  percentage: 0,
                };
                const isSelected = selectedStageFilter === stageNum;

                return (
                  <div
                    key={stageNum}
                    onClick={() =>
                      setSelectedStageFilter((prev) => (prev === stageNum ? 'all' : stageNum))
                    }
                    className={`flex flex-col gap-1.5 p-3 rounded-2xl transition-all cursor-pointer border ${
                      isSelected
                        ? 'bg-sky-50 border-[#1E54B7] shadow-md scale-[1.01]'
                        : 'bg-gray-50/80 hover:bg-gray-100 border-gray-200/80'
                    }`}
                  >
                    <div className="flex justify-between text-xs font-bold">
                      <span className="flex items-center gap-2 text-black">
                        <span
                          className="w-4 h-4 rounded-md flex items-center justify-center text-[10px] font-black text-white shadow-sm"
                          style={{ backgroundColor: meta.color }}
                        >
                          {meta.icon}
                        </span>
                        <span>{meta.name}</span>
                      </span>
                      <span className="font-mono text-gray-600 font-bold">{dist.count} patients ({dist.percentage}%)</span>
                    </div>

                    <div className="h-4 bg-gray-200 rounded-full overflow-hidden flex p-0.5">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.max(dist.percentage, 8)}%`,
                          backgroundColor: meta.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500 font-medium">
            <span>WCAG 2.2 AAA Dual-Coded</span>
            <span className="font-mono font-bold text-gray-700">Okabe-Ito Palette</span>
          </div>
        </div>

        {/* Recent Patient Scans Table */}
        <div className="lg:col-span-7 bg-white text-black rounded-3xl sm:rounded-[36px] p-5 sm:p-7 shadow-2xl border-2 sm:border-4 border-white flex flex-col space-y-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
                <Target className="w-4 h-4 stroke-[2.5]" />
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-black">
                Recent Patient Scans
              </h2>
            </div>
            <button
              onClick={() => setActiveView('patients')}
              className="text-xs font-black text-[#1E54B7] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>View All Records</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-x-auto touch-momentum no-scrollbar">
            <table className="w-full text-left border-collapse min-w-[480px]">
              <thead>
                <tr className="bg-gray-100/80 text-gray-700 text-[11px] font-black uppercase tracking-wider">
                  <th className="px-4 py-3 rounded-l-xl">Patient Name</th>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Scan Date</th>
                  <th className="px-4 py-3 rounded-r-xl text-right">AI Classification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {filteredScans.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-gray-500 text-xs font-medium">
                      No recent scans matching the selected stage filter.
                    </td>
                  </tr>
                ) : (
                  filteredScans.map((scan) => {
                    const meta = DR_STAGES[scan.detection.stage];
                    return (
                      <tr
                        key={scan.analysis_id}
                        onClick={() => handleOpenScan(scan)}
                        className="hover:bg-sky-50/80 cursor-pointer transition-colors group"
                      >
                        <td className="px-4 py-3.5 font-bold text-gray-950 group-hover:text-[#1E54B7]">
                          {scan.patient_name || 'Patient'}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-gray-500">
                          {scan.patient_id}
                        </td>
                        <td className="px-4 py-3.5 text-xs font-medium text-gray-600">
                          {scan.scan_date}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black text-white shadow-sm"
                            style={{ backgroundColor: meta.color }}
                          >
                            <span>{meta.icon}</span>
                            <span>{meta.name}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs text-gray-500">
            <span>Showing recent triage queue</span>
            <button
              onClick={() => {
                setActiveScan(null);
                setActiveView('batch-screening');
              }}
              className="text-[#1E54B7] font-black hover:underline cursor-pointer"
            >
              Open Batch Screening Queue ↗
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
