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
  Heart,
  Droplets,
  Clock,
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
    <div className="space-y-4 sm:space-y-6 animate-fadeIn text-white">
      {/* Header — tighter on mobile */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 p-4 sm:p-7 bg-white text-black rounded-2xl sm:rounded-[36px] shadow-2xl border border-gray-100 sm:border-4 sm:border-white">
        <div className="space-y-1 min-w-0">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-100 text-[#1E54B7] text-[10px] sm:text-xs font-black">
            <Users className="w-3.5 h-3.5" />
            <span>Clinical Directory</span>
          </div>
          <h1 className="text-xl sm:text-3xl font-extrabold text-black font-sans truncate">
            Patient Records
          </h1>
          <p className="text-[11px] sm:text-base text-gray-600 font-medium hidden sm:block">
            Longitudinal diabetic ophthalmology profiles, scan histories, and HbA1c tracking
          </p>
        </div>

        <button
          onClick={() => {
            setActivePatient(null);
            setActiveScan(null);
            setActiveView('new-scan');
          }}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 sm:px-7 py-2.5 sm:py-3.5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-[11px] sm:text-xs uppercase tracking-wider shadow-lg hover:scale-105 transition-all shrink-0 cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          <span>Register & Scan</span>
        </button>
      </div>

      {/* Search & Filter Bar — optimized for thumb reach */}
      <div className="p-4 sm:p-7 bg-white text-black rounded-2xl sm:rounded-[36px] space-y-4 sm:space-y-6 shadow-2xl border border-gray-100 sm:border-4 sm:border-white">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 sm:top-3.5 w-4 sm:w-5 h-4 sm:h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients..."
              className="w-full pl-10 sm:pl-12 pr-4 py-2.5 sm:py-3 bg-gray-50 border border-gray-200 rounded-xl sm:rounded-2xl text-black placeholder-gray-400 font-medium text-sm focus:border-[#1E54B7] focus:ring-2 focus:ring-sky-100 focus:outline-none transition-all"
            />
          </div>

          {/* Filter Chips — horizontal scroll on mobile */}
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto no-scrollbar py-0.5 touch-momentum -mx-0.5 px-0.5">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-[11px] sm:text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'all'
                  ? 'bg-black text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All ({patients.length})
            </button>
            <button
              onClick={() => setFilter('no-dr')}
              className={`inline-flex items-center gap-1 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-[11px] sm:text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'no-dr'
                  ? 'bg-[#009E73] text-white shadow-md'
                  : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
              }`}
            >
              <CheckCircle2 className="w-3 h-3" />
              <span>Healthy</span>
            </button>
            <button
              onClick={() => setFilter('mild-mod')}
              className={`inline-flex items-center gap-1 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-[11px] sm:text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'mild-mod'
                  ? 'bg-[#E69F00] text-black shadow-md'
                  : 'bg-amber-50 text-amber-900 hover:bg-amber-100'
              }`}
            >
              <AlertCircle className="w-3 h-3" />
              <span>Mild/Mod</span>
            </button>
            <button
              onClick={() => setFilter('high-risk')}
              className={`inline-flex items-center gap-1 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-[11px] sm:text-xs font-black whitespace-nowrap transition-all cursor-pointer shrink-0 ${
                filter === 'high-risk'
                  ? 'bg-[#D55E00] text-white shadow-md'
                  : 'bg-rose-50 text-rose-900 hover:bg-rose-100'
              }`}
            >
              <AlertTriangle className="w-3 h-3" />
              <span>High Risk</span>
            </button>
          </div>
        </div>

        {/* ═══ Patient Cards — Mobile-Optimized ═══ */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-5 pt-1 sm:pt-2">
          {filteredPatients.map((patient) => {
            const latestScan = patient.scans && patient.scans.length > 0 ? patient.scans[0] : null;

            return (
              <div
                key={patient.id}
                onClick={() => handleSelectPatient(patient)}
                className="p-3.5 sm:p-6 bg-gray-50/70 border border-gray-200/90 hover:border-[#1E54B7] hover:bg-white rounded-xl sm:rounded-3xl cursor-pointer transition-all hover:shadow-xl group flex flex-col justify-between active:scale-[0.98]"
              >
                <div className="space-y-2.5 sm:space-y-0">
                  {/* Patient Name & ID */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-base sm:text-lg text-black group-hover:text-[#1E54B7] transition-colors truncate">
                      {patient.name}
                    </span>
                    <span className="text-[10px] font-mono font-bold text-[#1E54B7] bg-sky-50 px-2 py-0.5 rounded-md shrink-0">
                      {patient.id}
                    </span>
                  </div>

                  {/* Quick Demographics */}
                  <div className="text-[11px] sm:text-xs text-gray-500 flex items-center gap-2 sm:gap-3 font-medium mt-1">
                    <span>{patient.age}, {patient.gender}</span>
                    <span className="text-gray-300">|</span>
                    <span className="inline-flex items-center gap-0.5">
                      <Clock className="w-3 h-3 text-gray-400" />
                      {patient.diabetes_duration}y
                    </span>
                  </div>

                  {/* Vitals — compact inline on mobile */}
                  <div className="flex items-center gap-2 mt-2.5 sm:mt-3.5">
                    <div className="flex-1 p-2 sm:p-3 bg-white rounded-lg sm:rounded-2xl border border-gray-200/80">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400 text-[9px] sm:text-[10px] uppercase font-bold flex items-center gap-1">
                          <Heart className="w-2.5 h-2.5 text-rose-300" />
                          HbA1c
                        </span>
                        <strong className="text-black text-sm sm:text-base font-mono">{patient.hba1c}%</strong>
                      </div>
                    </div>
                    <div className="flex-1 p-2 sm:p-3 bg-white rounded-lg sm:rounded-2xl border border-gray-200/80">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400 text-[9px] sm:text-[10px] uppercase font-bold flex items-center gap-1">
                          <Droplets className="w-2.5 h-2.5 text-blue-300" />
                          Sugar
                        </span>
                        <strong className="text-black text-sm sm:text-base font-mono">{patient.sugar_level}</strong>
                      </div>
                    </div>
                  </div>

                  {/* DR Status Badge */}
                  <div className="mt-2.5 sm:mt-3.5">
                    <span className="text-[10px] sm:text-[11px] font-bold text-gray-500 uppercase block mb-1">
                      Retinal Status:
                    </span>
                    {latestScan ? (
                      <DualCodedBadge stage={latestScan.detection.stage} size="sm" showDetails />
                    ) : (
                      <span className="text-[11px] text-gray-400 italic">No scans recorded</span>
                    )}
                  </div>
                </div>

                {/* Card Footer Actions */}
                <div className="flex items-center justify-between pt-2.5 sm:pt-3.5 mt-2.5 sm:mt-0 border-t border-gray-200 text-[11px] sm:text-xs">
                  <span className="text-gray-500 font-mono font-medium">
                    {patient.scans?.length || 0} scans
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

                    <span className="inline-flex items-center gap-0.5 font-black text-[#1E54B7] group-hover:translate-x-1 transition-transform">
                      <span className="hidden sm:inline">Profile</span> <ArrowRight className="w-3.5 h-3.5" />
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
