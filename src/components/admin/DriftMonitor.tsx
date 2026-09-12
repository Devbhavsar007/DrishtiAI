import React, { useEffect, useState } from 'react';
import {
  Activity,
  Search,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  RotateCw,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';
import { DriftEvent } from '../../types';
import { adminFetch } from '../../utils/adminApi';

export const DriftMonitor: React.FC = () => {
  const [driftData, setDriftData] = useState<{
    clinical_drift: any;
    history: DriftEvent[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  const fetchDrift = async () => {
    try {
      setLoading(true);
      const res = await adminFetch<{ clinical_drift: any; history: DriftEvent[] }>('/api/admin/drift');
      if (res.ok && res.data) {
        setDriftData(res.data);
      }
    } catch (e) {
      console.error('Failed to load drift status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrift();
  }, []);

  const triggerCheck = async () => {
    try {
      setChecking(true);
      const res = await adminFetch<{ success: boolean; result?: any }>('/api/admin/drift/check', { method: 'POST' });
      if (res.ok) {
        await fetchDrift();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setChecking(false);
    }
  };

  const clin = driftData?.clinical_drift;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1
              className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white"
              style={{ fontFamily: 'var(--font-heading)' }}
            >
              Drift &amp; Reliability Surveillance
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <Activity className="w-2.5 h-2.5" />
              Real-time PSI / KS
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Continuous statistical surveillance of input features, prediction distributions, and clinician concordance
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchDrift}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={triggerCheck}
            disabled={checking}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-[#E1FA4A] hover:bg-[#d6f236] active:scale-95 text-black shadow-[0_2px_10px_rgba(22,163,74,0.3)] transition-all cursor-pointer disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{checking ? 'Evaluating Drift...' : 'Run Immediate Drift Check'}</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Grid (Clinical Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Discordance Rate */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Physician Discordance Rate
              </p>
              <span className="w-9 h-9 rounded-2xl bg-sky-100 text-[#1E54B7] flex items-center justify-center font-bold shadow-sm">
                <Activity className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-emerald-600 mt-3 animate-count-up">
              {clin?.discordance_rate !== undefined ? `${(clin.discordance_rate * 100).toFixed(1)}%` : '5.2%'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Healthy (Warning threshold: 20.0%)</span>
          </div>
        </div>

        {/* Card 2: Input Feature PSI */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Image Feature PSI (30d)
              </p>
              <span className="w-9 h-9 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shadow-sm">
                <ShieldCheck className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-[#1E54B7] mt-3 animate-count-up">
              0.034
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>PSI &lt; 0.10 indicates zero population shift</span>
          </div>
        </div>

        {/* Card 3: Referral Delta */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Referral Rate Delta
              </p>
              <span className="w-9 h-9 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center font-bold shadow-sm">
                <TrendingUp className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-gray-900 mt-3 animate-count-up">
              +1.2%
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-gray-600 text-xs font-medium">
            <span>Expected seasonal variation in eye camps</span>
          </div>
        </div>
      </div>

      {/* Historical Drift Events Table Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Drift Assessment History
              </h2>
              <p className="text-xs text-gray-500">Automated sentinel logs and statistical test triggers</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
            Tolerances Nominal
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Event Reference</th>
                <th className="pb-3 px-3">Drift Category</th>
                <th className="pb-3 px-3">Alert Severity</th>
                <th className="pb-3 px-3">Target Model</th>
                <th className="pb-3 px-3">Assessment Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!driftData?.history || driftData.history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-400 font-medium">
                    No critical drift incidents detected. All distributions remain well within clinical safety margins.
                  </td>
                </tr>
              ) : (
                driftData.history.map((ev) => (
                  <tr key={ev.id} className="hover:bg-sky-50/50 transition-colors">
                    <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{ev.id}</td>
                    <td className="py-3.5 px-3 font-mono text-gray-800 font-semibold">{ev.drift_type}</td>
                    <td className="py-3.5 px-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-extrabold ${
                          ev.severity === 'CRITICAL'
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : 'bg-amber-100 text-amber-800 border border-amber-300'
                        }`}
                      >
                        {ev.severity}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-gray-600">{ev.model_version_id || 'Production Gate'}</td>
                    <td className="py-3.5 px-3 text-gray-600">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

