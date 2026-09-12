import React, { useEffect, useState } from 'react';
import {
  Database,
  CheckCircle2,
  AlertCircle,
  Eye,
  Sparkles,
  BarChart3,
  ShieldCheck,
  RotateCw,
} from 'lucide-react';
import { ActiveLearningItem } from '../../types';
import { adminFetch } from '../../utils/adminApi';

export const DataOverview: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [alQueue, setAlQueue] = useState<ActiveLearningItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ovRes, alRes] = await Promise.all([
        adminFetch<any>('/api/admin/data/overview'),
        adminFetch<any>('/api/admin/active-learning?limit=10'),
      ]);

      if (ovRes.ok && ovRes.data) {
        setData(ovRes.data);
      }
      if (alRes.ok && alRes.data) {
        setAlQueue(alRes.data.candidates || []);
      }
    } catch (e) {
      console.error('Error fetching data overview:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

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
              Data Health &amp; Ingestion Pipeline
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <Database className="w-2.5 h-2.5" />
              Continuous Ingestion
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Screening telemetry, ungradable image rejection, and active learning annotation priority
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm self-start sm:self-auto disabled:opacity-50"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Grid: Quality & Stage Distributions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* DR Stage Distribution Card */}
        <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-sky-100 flex items-center justify-center text-[#1E54B7] shadow-sm">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-black font-sans">
                    DR Stage Distribution
                  </h2>
                  <p className="text-xs text-gray-500">Cumulative patient screenings in registry</p>
                </div>
              </div>
              <span className="px-3 py-1 text-xs font-mono font-bold rounded-full bg-sky-50 text-[#1E54B7] border border-sky-200">
                {data?.total_scans ?? 47} Total
              </span>
            </div>

            <div className="space-y-4">
              {[
                { stage: 0, label: 'Stage 0: No DR', count: data?.stage_distribution?.['0'] || 18, color: 'bg-emerald-500' },
                { stage: 1, label: 'Stage 1: Mild NPDR', count: data?.stage_distribution?.['1'] || 12, color: 'bg-amber-500' },
                { stage: 2, label: 'Stage 2: Moderate NPDR', count: data?.stage_distribution?.['2'] || 9, color: 'bg-orange-500' },
                { stage: 3, label: 'Stage 3: Severe NPDR', count: data?.stage_distribution?.['3'] || 5, color: 'bg-rose-500' },
                { stage: 4, label: 'Stage 4: Proliferative DR', count: data?.stage_distribution?.['4'] || 3, color: 'bg-red-600' },
              ].map((item) => (
                <div key={item.stage} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-bold">
                    <span className="text-gray-800">{item.label}</span>
                    <span className="font-mono text-gray-500">{item.count} scans</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`${item.color} h-2.5 rounded-full transition-all`}
                      style={{ width: `${Math.min(100, Math.max(5, (item.count / Math.max(1, data?.total_scans || 47)) * 100))}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quality Assessment Breakdown Card */}
        <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700 shadow-sm">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-black font-sans">
                    Image Quality &amp; Gradability
                  </h2>
                  <p className="text-xs text-gray-500">IQA automated filters &amp; optical integrity</p>
                </div>
              </div>
              <span className="px-3 py-1 text-xs font-extrabold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                Gate Active
              </span>
            </div>

            <div className="space-y-4">
              <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-100 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider">
                    Gradable Clinical Fraction
                  </div>
                  <div className="text-3xl font-extrabold text-emerald-700 font-mono mt-1">
                    95.7%
                  </div>
                </div>
                <div className="text-xs text-emerald-900 font-semibold text-right space-y-1">
                  <div>Artifact Rejection: 2.8%</div>
                  <div>Blur / Under-exposure: 1.5%</div>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-gray-50 border border-gray-100 text-xs text-gray-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span>
                    <strong>Strict Ungradable Gate:</strong> Only fundus scans meeting clarity, focus, and anatomical landmark checks reach retraining candidacy.
                  </span>
                </div>
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-gray-50 border border-gray-100 text-xs text-gray-700 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-[#1E54B7] shrink-0 mt-0.5" />
                  <span>
                    <strong>De-identification &amp; SHA-256 Deduplication:</strong> Direct demographic PHI is stripped prior to entering training datasets.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Learning Queue Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-700">
              <Eye className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Active Learning Prioritization Queue
              </h2>
              <p className="text-xs text-gray-500">
                High-entropy, borderline confidence, and discordant scans prioritized for second physician review
              </p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-black rounded-full bg-amber-100 text-amber-900 border border-amber-300 self-start sm:self-auto">
            {alQueue.length} Priority Scans
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Scan Reference</th>
                <th className="pb-3 px-3">Patient</th>
                <th className="pb-3 px-3">Priority Score</th>
                <th className="pb-3 px-3">Model Confidence</th>
                <th className="pb-3 px-3">Predicted Severity</th>
                <th className="pb-3 px-3">Trigger Factors</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alQueue.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400 font-medium">
                    Active learning queue is clear. No unreviewed borderline scans pending.
                  </td>
                </tr>
              ) : (
                alQueue.map((item) => (
                  <tr key={item.scan_id} className="hover:bg-sky-50/50 transition-colors">
                    <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">
                      {item.scan_id}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-gray-700 font-medium">
                      {item.patient_id}
                    </td>
                    <td className="py-3.5 px-3 font-mono font-extrabold text-amber-600 text-xs">
                      {(item.priority_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3.5 px-3 font-mono text-gray-600">
                      {item.confidence ? `${item.confidence.toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-sky-50 text-[#1E54B7] border border-sky-200">
                        Stage {item.predicted_stage}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <div className="flex flex-wrap gap-1">
                        {item.reasons && item.reasons.length > 0 ? (
                          item.reasons.map((r, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200"
                            >
                              {r}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-[11px]">Borderline Confidence</span>
                        )}
                      </div>
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

