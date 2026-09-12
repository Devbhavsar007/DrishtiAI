import React, { useState } from 'react';
import {
  Users,
  Search,
  UserPlus,
  ArrowRight,
  Filter,
  Microscope,
  Calendar,
  Activity,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { DR_STAGES, DRStage, Patient } from '../types';
import { DualCodedBadge } from './DualCodedBadge';

type SeverityFilter = 'all' | 'no-dr' | 'mild-mod' | 'high-risk';

export const PatientDirectoryView: React.FC = () => {
  const { patients, setActivePatient, setActiveView, setActiveScan } = useMedicalData();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<SeverityFilter>('all');

  const filteredPatients = patients.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.id.toLowerCase().includes(search.toLowerCase()) ||
      (p.notes && p.notes.toLowerCase().includes(search.toLowerCase()));

    if (!matchesSearch) return false;

    const latestScan = p.scans && p.scans.length > 0 ? p.scans[0] : null;
    const stage = latestScan ? latestScan.detection.stage : null;

    if (filter === 'no-dr') return stage === 0;
    if (filter === 'mild-mod') return stage === 1 || stage === 2;
    if (filter === 'high-risk') return stage === 3 || stage === 4;
    return true;
  });

  const handleSelectPatient = (patient: Patient) => {
    setActivePatient(patient);
    setActiveView('patient-detail');
  };

  const handleStartScanForPatient = (patient: Patient) => {
    setActivePatient(patient);
    setActiveScan(null);
    setActiveView('new-scan');
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 sm:p-7 bg-white text-black rounded-3xl sm:rounded-[36px] shadow-2xl border-2 sm:border-4 border-white">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-[#1E54B7] text-xs font-black">
            <Users className="w-4 h-4" />
            <span>Comprehensive Clinical Directory</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-black flex items-center gap-3 font-sans">
            Patient Records Directory
          </h1>
          <p className="text-xs sm:text-base text-gray-600 font-medium">
            Longitudinal diabetic ophthalmology profiles, scan histories, and HbA1c tracking
          </p>
        </div>

        <button
          onClick={() => {
            setActivePatient(null);
            setActiveScan(null);
            setActiveView('new-scan');
          }}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 sm:px-7 py-3 sm:py-3.5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-xs uppercase tracking-wider shadow-lg hover:scale-105 transition-all shrink-0 min-h-[46px] cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          <span>Register &amp; Scan Patient</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="p-5 sm:p-7 bg-white text-black rounded-3xl sm:rounded-[36px] space-y-5 sm:space-y-6 shadow-2xl border-2 sm:border-4 border-white">
        <div className="flex flex-col md:flex-row gap-3 sm:gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3.5 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by patient name, ID, clinical notes..."
              className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-black placeholder-gray-400 font-medium focus:border-[#1E54B7] focus:ring-2 focus:ring-sky-100 focus:outline-none transition-all"
            />
          </div>

          {/* Filter Chips (Horizontal Swipe on Mobile) */}
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1 touch-momentum -mx-1 px-1">
            <button
              onClick={() => setFilter('all')}
              className={`px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'all'
                  ? 'bg-black text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All Records ({patients.length})
            </button>
            <button
              onClick={() => setFilter('no-dr')}
              className={`inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'no-dr'
                  ? 'bg-[#009E73] text-white shadow-md'
                  : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>No DR / Healthy</span>
            </button>
            <button
              onClick={() => setFilter('mild-mod')}
              className={`inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'mild-mod'
                  ? 'bg-[#E69F00] text-black shadow-md'
                  : 'bg-amber-50 text-amber-900 hover:bg-amber-100'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Mild / Moderate</span>
            </button>
            <button
              onClick={() => setFilter('high-risk')}
              className={`inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'high-risk'
                  ? 'bg-[#D55E00] text-white shadow-md'
                  : 'bg-rose-50 text-rose-900 hover:bg-rose-100'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>High Risk (Severe/PDR)</span>
            </button>
          </div>
        </div>

        {/* Results List */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 pt-2">
          {filteredPatients.map((patient) => {
            const latestScan = patient.scans && patient.scans.length > 0 ? patient.scans[0] : null;

            return (
              <div
                key={patient.id}
                onClick={() => handleSelectPatient(patient)}
                className="p-6 bg-gray-50/70 border border-gray-200/90 hover:border-[#1E54B7] hover:bg-white rounded-3xl cursor-pointer transition-all hover:shadow-xl space-y-4 group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-lg text-black group-hover:text-[#1E54B7] transition-colors truncate">
                      {patient.name}
                    </span>
                    <span className="text-xs font-mono font-bold text-[#1E54B7] bg-sky-100 px-2.5 py-0.5 rounded-full shrink-0">
                      {patient.id}
                    </span>
                  </div>

                  <div className="text-xs text-gray-500 mt-1 flex items-center gap-2 font-medium">
                    <span>Age: {patient.age} ({patient.gender})</span>
                    <span>•</span>
                    <span>Diabetes: {patient.diabetes_duration} yrs</span>
                  </div>

                  {/* Vitals Summary */}
                  <div className="grid grid-cols-2 gap-2 mt-3.5 p-3 bg-white rounded-2xl border border-gray-200/80 text-xs font-mono">
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">HbA1c</span>
                      <strong className="text-black text-sm">{patient.hba1c}%</strong>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">Fasting Sugar</span>
                      <strong className="text-black text-sm">{patient.sugar_level} mg/dL</strong>
                    </div>
                  </div>

                  {/* Latest Diagnostic Status */}
                  <div className="mt-3.5">
                    <span className="text-[11px] font-bold text-gray-500 uppercase block mb-1">
                      Latest Retinal Diagnosis:
                    </span>
                    {latestScan ? (
                      <DualCodedBadge stage={latestScan.detection.stage} size="sm" showDetails />
                    ) : (
                      <span className="text-xs text-gray-400 italic">No prior scans recorded</span>
                    )}
                  </div>
                </div>

                {/* Card Actions */}
                <div className="flex items-center justify-between pt-3.5 border-t border-gray-200 text-xs">
                  <span className="text-gray-500 font-mono font-medium">
                    {patient.scans?.length || 0} scans on file
                  </span>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartScanForPatient(patient);
                      }}
                      className="p-2 rounded-full bg-sky-100 hover:bg-[#E1FA4A] text-[#1E54B7] hover:text-black transition-all font-bold cursor-pointer"
                      title="Run new scan for this patient"
                    >
                      <Microscope className="w-4 h-4" />
                    </button>

                    <span className="inline-flex items-center gap-1 font-black text-[#1E54B7] group-hover:translate-x-1 transition-transform">
                      Profile <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
