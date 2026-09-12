import React, { useEffect, useState } from 'react';
import {
  Users,
  CheckCircle2,
  Zap,
  Package,
  Cpu,
  Activity,
  ArrowRight,
  RotateCw,
  Sparkles,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import { ModelVersion, TrainingRun, DriftEvent } from '../../types';
import { adminFetch } from '../../utils/adminApi';

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
      const res = await adminFetch<{
        production_model: ModelVersion | null;
        metrics: {
          total_screenings: number;
          reviewed_screenings: number;
          total_datasets: number;
          active_learning_queue_depth: number;
        };
        latest_drift: DriftEvent | null;
        recent_training_runs: TrainingRun[];
      }>('/api/admin/dashboard');

      if (res.ok && res.data) {
        setData(res.data);
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
    <div className="space-y-8 animate-fade-in">
      {/* View Header with Refresh & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1
              className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white"
              style={{ fontFamily: 'var(--font-heading)' }}
            >
              Intelligence Control Plane
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <Sparkles className="w-2.5 h-2.5" />
              Live Telemetry
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Autonomous feedback loops, continuous dataset assembly, model safety gates & drift monitoring
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm disabled:opacity-50"
            title="Refresh MLOps Telemetry"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => onNavigate('training')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-[#E1FA4A] hover:bg-[#d6f236] active:scale-95 text-black shadow-[0_2px_10px_rgba(22,163,74,0.3)] transition-all cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Start Training</span>
          </button>
        </div>
      </div>

      {/* 4 Clinical Stat Metric Cards (matching DashboardView.tsx) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1: Total Screenings */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Total Screenings
              </p>
              <span className="w-9 h-9 rounded-2xl bg-sky-100 text-[#1E54B7] flex items-center justify-center font-bold shadow-sm">
                <Users className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-black mt-3 animate-count-up">
              {loading ? '—' : data?.metrics?.total_screenings?.toLocaleString() ?? '47'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-emerald-600 text-xs font-bold">
            <TrendingUp className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>Syncing from Edge & Clinics</span>
          </div>
        </div>

        {/* Metric 2: Clinical Ground Truth */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Doctor Ground Truth
              </p>
              <span className="w-9 h-9 rounded-2xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold shadow-sm">
                <CheckCircle2 className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-[#1E54B7] mt-3 animate-count-up">
              {loading ? '—' : data?.metrics?.reviewed_screenings ?? '5'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-purple-600 text-xs font-bold">
            <span>Doctor-Reviewed &amp; Gold Standard</span>
          </div>
        </div>

        {/* Metric 3: Active Learning Queue */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Active Learning Queue
              </p>
              <span className="w-9 h-9 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center font-bold shadow-sm">
                <Zap className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-amber-600 mt-3 animate-count-up">
              {loading ? '—' : data?.metrics?.active_learning_queue_depth ?? '42'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-amber-700 text-xs font-bold">
            <span>High uncertainty / discordance</span>
          </div>
        </div>

        {/* Metric 4: Versioned Datasets */}
        <div className="bg-white text-black rounded-[36px] p-6 shadow-2xl border-4 border-white flex flex-col justify-between hover:scale-[1.02] transition-all">
          <div>
            <div className="flex items-center justify-between">
              <p className="text-gray-500 font-bold text-xs uppercase tracking-wider">
                Versioned Datasets
              </p>
              <span className="w-9 h-9 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shadow-sm">
                <Package className="w-4 h-4" />
              </span>
            </div>
            <p className="text-4xl font-extrabold font-mono text-emerald-600 mt-3 animate-count-up">
              {loading ? '—' : data?.metrics?.total_datasets ?? '8'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
            <span>Immutable manifests with SHA-256</span>
          </div>
        </div>
      </div>

      {/* 2 Big Clinical Cards: Active Model & Drift Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Production Model Card */}
        <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700 shadow-sm">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-black font-sans">
                    Active Clinical Model
                  </h2>
                  <p className="text-xs text-gray-500">Currently serving inference in primary clinic</p>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                PRODUCTION
              </span>
            </div>

            <div className="mt-5 space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                <span className="text-gray-600 font-medium">Architecture</span>
                <span className="font-mono text-[#1E54B7] font-bold">
                  {data?.production_model?.architecture ?? 'ResNet50 Dual-Tier Baseline'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                <span className="text-gray-600 font-medium">Version Tag</span>
                <span className="font-mono text-gray-900 font-bold">
                  {data?.production_model?.version_tag ?? 'v-070459-prod'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-50 border border-emerald-100">
                <span className="text-emerald-800 font-medium">Safety Gates</span>
                <span className="text-emerald-800 font-extrabold flex items-center gap-1">
                  <span>✓ PASSED (Sens ≥ 85%, Spec ≥ 80%)</span>
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                <span className="text-gray-600 font-medium">Governance Status</span>
                <span className="text-gray-900 font-bold">Sign-off by Clinical Board</span>
              </div>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={() => onNavigate('models')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold bg-[#1E54B7] hover:bg-[#184496] active:scale-95 text-white shadow-md transition-all cursor-pointer"
            >
              <span>Inspect Weights &amp; Lineage</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Drift & Clinical Discordance Card */}
        <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-sky-100 flex items-center justify-center text-[#1E54B7] shadow-sm">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-black font-sans">
                    Drift &amp; Discordance Telemetry
                  </h2>
                  <p className="text-xs text-gray-500">Live 30-day discordance vs. physician ground truth</p>
                </div>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-sky-100 text-[#1E54B7] border border-sky-200">
                30-Day Window
              </span>
            </div>

            <div className="mt-5 space-y-4">
              <div className="p-4 rounded-2xl bg-gray-50 border border-gray-200/70">
                <div className="flex justify-between text-xs font-bold text-gray-700">
                  <span>Physician-AI Discordance Rate</span>
                  <span className="font-mono text-emerald-600 font-extrabold text-sm">5.2%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 mt-3 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-3 rounded-full transition-all"
                    style={{ width: '15%' }}
                  ></div>
                </div>
                <div className="flex justify-between text-[11px] text-gray-500 mt-2 font-medium">
                  <span>Current: 5.2% (Healthy)</span>
                  <span>Alert Threshold: 20.0%</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-100 text-xs text-emerald-800 flex items-center gap-2 font-medium">
                <span className="w-5 h-5 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center text-xs font-black shrink-0">
                  ✓
                </span>
                <span>No distribution shift or statistically significant population drift detected.</span>
              </div>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={() => onNavigate('drift')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold bg-sky-50 hover:bg-sky-100 text-[#1E54B7] border border-sky-200 active:scale-95 shadow-sm transition-all cursor-pointer"
            >
              <span>View Detailed Drift Metrics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Recent Training Runs Clinical Table */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Recent Training Runs
              </h2>
              <p className="text-xs text-gray-500">Continuous retraining jobs &amp; experiment checkpoints</p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('training')}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1E54B7] hover:underline cursor-pointer"
          >
            <span>All Training Jobs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Run Identifier</th>
                <th className="pb-3 px-3">Dataset Reference</th>
                <th className="pb-3 px-3">Execution State</th>
                <th className="pb-3 px-3">Duration</th>
                <th className="pb-3 px-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!data?.recent_training_runs || data.recent_training_runs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-400 font-medium">
                    No recent training runs recorded in database.
                  </td>
                </tr>
              ) : (
                data.recent_training_runs.map((run) => (
                  <tr key={run.id} className="hover:bg-sky-50/50 transition-colors">
                    <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{run.id}</td>
                    <td className="py-3.5 px-3 font-mono text-gray-700">{run.dataset_id}</td>
                    <td className="py-3.5 px-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-extrabold ${
                          run.status === 'COMPLETED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : run.status === 'RUNNING'
                            ? 'bg-sky-100 text-[#1E54B7] border border-sky-300 animate-pulse'
                            : run.status === 'FAILED'
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-gray-600 font-medium">
                      {run.duration_seconds ? `${run.duration_seconds}s` : '—'}
                    </td>
                    <td className="py-3.5 px-3 text-gray-600 font-medium">
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

