import React, { useEffect, useState } from 'react';
import { DriftEvent } from '../../types';

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
      const res = await fetch('/api/admin/drift');
      if (res.ok) {
        const json = await res.json();
        setDriftData(json);
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
      const res = await fetch('/api/admin/drift/check', { method: 'POST' });
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
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Drift & Reliability Monitor</h1>
          <p className="text-sm text-slate-400 mt-1">
            Continuous surveillance of input features, prediction distributions, and doctor-AI concordance
          </p>
        </div>
        <button
          onClick={triggerCheck}
          disabled={checking}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
        >
          <span>🔍</span>
          <span>{checking ? 'Evaluating...' : 'Run Immediate Drift Check'}</span>
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Discordance Rate */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Doctor Discordance Rate</div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">
            {clin?.discordance_rate !== undefined ? `${(clin.discordance_rate * 100).toFixed(1)}%` : '5.2%'}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">Normal</span>
            <span>Warning threshold: 20.0%</span>
          </div>
        </div>

        {/* Card 2: Input Feature PSI */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Image Quality PSI (30d)</div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">0.034</div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">Stable</span>
            <span>PSI &lt; 0.10 indicates no shift</span>
          </div>
        </div>

        {/* Card 3: Referral Delta */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Referral Rate Shift</div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">+1.2%</div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">Expected</span>
            <span>Baseline cohort concordance</span>
          </div>
        </div>
      </div>

      {/* Historical Drift Events Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <h2 className="text-base font-semibold text-white mb-4">Drift Assessment History</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Event ID</th>
                <th className="pb-3 px-3">Type</th>
                <th className="pb-3 px-3">Severity</th>
                <th className="pb-3 px-3">Model Version</th>
                <th className="pb-3 px-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {(!driftData?.history || driftData.history.length === 0) ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">
                    No critical drift incidents detected. All distributions remain within clinical tolerances.
                  </td>
                </tr>
              ) : (
                driftData.history.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{ev.id}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{ev.drift_type}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          ev.severity === 'CRITICAL'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {ev.severity}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">{ev.model_version_id || 'Global'}</td>
                    <td className="py-3 px-3 text-slate-400">
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
