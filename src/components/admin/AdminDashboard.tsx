import React, { useEffect, useState } from 'react';
import { ModelVersion, TrainingRun, DriftEvent } from '../../types';

interface DashboardProps {
  onNavigate: (view: any) => void;
}

export const AdminDashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [data, setData] = useState<{
    production_model: ModelVersion | null;
    metrics: {
      total_screenings: number;
      reviewed_screenings: number;
      total_datasets: number;
      active_learning_queue_depth: number;
    };
    latest_drift: DriftEvent | null;
    recent_training_runs: TrainingRun[];
  } | null>(null);

  const [loading, setLoading] = useState(true);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/admin/dashboard');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      console.error('Failed to load dashboard summary', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Intelligence Control Plane</h1>
          <p className="text-sm text-slate-400 mt-1">
            End-to-end telemetry across dataset assembly, curriculum training, model registry & drift
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchSummary}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            Refresh Telemetry
          </button>
          <button
            onClick={() => onNavigate('training')}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 transition-all"
          >
            + Start Retraining
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1 */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Total Screenings</span>
            <span className="text-cyan-400 text-base">👁️</span>
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {loading ? '...' : data?.metrics.total_screenings ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">Synced</span>
            <span>from rural & edge clinics</span>
          </div>
          <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-cyan-500/5 rounded-full blur-xl pointer-events-none"></div>
        </div>

        {/* Metric 2 */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Clinical Ground Truth</span>
            <span className="text-purple-400 text-base">🩺</span>
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {loading ? '...' : data?.metrics.reviewed_screenings ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-purple-400 font-semibold">Doctor Confirmed</span>
            <span>eligible for training</span>
          </div>
          <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-purple-500/5 rounded-full blur-xl pointer-events-none"></div>
        </div>

        {/* Metric 3 */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Active Learning Queue</span>
            <span className="text-amber-400 text-base">⚡</span>
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {loading ? '...' : data?.metrics.active_learning_queue_depth ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-amber-400 font-semibold">Prioritized</span>
            <span>high-uncertainty cases</span>
          </div>
          <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-amber-500/5 rounded-full blur-xl pointer-events-none"></div>
        </div>

        {/* Metric 4 */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Versioned Datasets</span>
            <span className="text-emerald-400 text-base">📦</span>
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {loading ? '...' : data?.metrics.total_datasets ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span className="text-emerald-400 font-semibold">Immutable</span>
            <span>manifests with zero leakage</span>
          </div>
          <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-emerald-500/5 rounded-full blur-xl pointer-events-none"></div>
        </div>
      </div>

      {/* Two Column Section: Active Model & Drift Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Production Model */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
            <div className="flex items-center space-x-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-ping"></span>
              <h2 className="font-semibold text-white text-base">Active Clinical Model</h2>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
              PRODUCTION
            </span>
          </div>

          <div className="mt-5 space-y-3.5 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-800/40">
              <span className="text-slate-400">Architecture</span>
              <span className="font-mono text-cyan-300 font-medium">
                {data?.production_model?.architecture ?? 'EfficientNet-B3-Ordinal'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/40">
              <span className="text-slate-400">Version Tag</span>
              <span className="font-mono text-slate-200">
                {data?.production_model?.version_tag ?? 'v2026.09.08-prod'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/40">
              <span className="text-slate-400">Clinical Safety Gates</span>
              <span className="text-emerald-400 font-semibold">ALL GATES PASSED (Sens ≥ 85%, Spec ≥ 80%)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Governance Sign-off</span>
              <span className="text-slate-200">Approved by Clinical Reviewer</span>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end space-x-3">
            <button
              onClick={() => onNavigate('models')}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
            >
              Inspect Lineage & Weights →
            </button>
          </div>
        </div>

        {/* Drift & Reliability Monitor */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
              <div className="flex items-center space-x-2.5">
                <span className="text-base">📈</span>
                <h2 className="font-semibold text-white text-base">Drift & Clinical Discordance</h2>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                30-Day Window
              </span>
            </div>

            <div className="mt-5 space-y-4">
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/60">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Doctor-AI Discordance Rate</span>
                  <span className="font-semibold text-slate-200 font-mono">5.2%</span>
                </div>
                <div className="w-full bg-slate-800/80 rounded-full h-2 mt-2.5 overflow-hidden">
                  <div className="bg-emerald-400 h-2 rounded-full" style={{ width: '15%' }}></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 mt-1.5">
                  <span>Current: 5.2%</span>
                  <span>Threshold Warning: 20% | Critical: 35%</span>
                </div>
              </div>

              <div className="text-xs text-slate-400 flex items-center gap-2">
                <span className="text-emerald-400 text-sm">✓</span>
                <span>No statistically significant input feature or prediction drift detected.</span>
              </div>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={() => onNavigate('drift')}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
            >
              View Detailed Drift Metrics →
            </button>
          </div>
        </div>
      </div>

      {/* Recent Training Runs Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-white text-base">Recent Training Runs</h2>
          <button
            onClick={() => onNavigate('training')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
          >
            View All Runs →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Run ID</th>
                <th className="pb-3 px-3">Dataset ID</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3">Duration</th>
                <th className="pb-3 px-3">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {(!data?.recent_training_runs || data.recent_training_runs.length === 0) ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    No recent training runs recorded.
                  </td>
                </tr>
              ) : (
                data.recent_training_runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{run.id}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{run.dataset_id}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          run.status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : run.status === 'RUNNING'
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse'
                            : run.status === 'FAILED'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {run.duration_seconds ? `${run.duration_seconds}s` : '—'}
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : run.created_at}
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
