import React, { useEffect, useState } from 'react';
import {
  Cpu,
  Zap,
  RotateCw,
  Clock,
  Sparkles,
  X,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { TrainingRun, TrainingDataset } from '../../types';
import { adminFetch } from '../../utils/adminApi';

export const TrainingRuns: React.FC = () => {
  const [runs, setRuns] = useState<TrainingRun[]>([]);
  const [datasets, setDatasets] = useState<TrainingDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [datasetId, setDatasetId] = useState('');
  const [preset, setPreset] = useState('standard_retina');
  const [maxIterations, setMaxIterations] = useState('4');
  const [batchSize, setBatchSize] = useState('8');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [runsRes, dsRes] = await Promise.all([
        adminFetch<{ runs: TrainingRun[] }>('/api/admin/training'),
        adminFetch<{ datasets: TrainingDataset[] }>('/api/admin/datasets'),
      ]);
      if (runsRes.ok && runsRes.data) {
        setRuns(runsRes.data.runs || []);
      }
      if (dsRes.ok && dsRes.data) {
        const dss = dsRes.data.datasets || [];
        setDatasets(dss);
        if (dss.length > 0 && !datasetId) {
          setDatasetId(dss[0].id);
        }
      }
    } catch (e) {
      console.error('Failed to load training runs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmitRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId) {
      alert('Please select or compile a dataset first');
      return;
    }

    try {
      setSubmitting(true);
      const res = await adminFetch<{ success: boolean; run_id?: string; error?: string }>('/api/admin/training/submit', {
        method: 'POST',
        body: JSON.stringify({
          dataset_id: datasetId,
          max_iterations: parseInt(maxIterations),
          batch_size: parseInt(batchSize),
        }),
      });
      if (res.ok) {
        setShowModal(false);
        await fetchData();
      } else {
        alert(`Failed to launch training run: ${res.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

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
              Training Orchestration Engine
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <Cpu className="w-2.5 h-2.5" />
              Curriculum Loop
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Hard-example mining, model checkpointing, and ordinal classification convergence
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-[#E1FA4A] hover:bg-[#d6f236] active:scale-95 text-black shadow-[0_2px_10px_rgba(22,163,74,0.3)] transition-all cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Launch Training Job</span>
          </button>
        </div>
      </div>

      {/* Runs Table Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Active &amp; Historical Training Runs
              </h2>
              <p className="text-xs text-gray-500">Telemetry across training runs and automated test gates</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-sky-50 text-[#1E54B7] border border-sky-200">
            {runs.length} Total Runs
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Run Identifier</th>
                <th className="pb-3 px-3">Dataset Reference</th>
                <th className="pb-3 px-3">State</th>
                <th className="pb-3 px-3">Runtime</th>
                <th className="pb-3 px-3">Sensitivity</th>
                <th className="pb-3 px-3">Specificity</th>
                <th className="pb-3 px-3">Triggered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400 font-medium">
                    No training runs submitted yet. Click "Launch Training Job" to begin training on active datasets.
                  </td>
                </tr>
              ) : (
                runs.map((r) => {
                  const metrics = r.final_metrics_json || {};
                  return (
                    <tr key={r.id} className="hover:bg-sky-50/50 transition-colors">
                      <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{r.id}</td>
                      <td className="py-3.5 px-3 font-mono text-gray-700">{r.dataset_id}</td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-extrabold ${
                            r.status === 'COMPLETED'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : r.status === 'RUNNING'
                              ? 'bg-sky-100 text-[#1E54B7] border border-sky-300 animate-pulse'
                              : r.status === 'FAILED'
                              ? 'bg-rose-100 text-rose-800 border border-rose-300'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-gray-600">
                        {r.duration_seconds ? `${r.duration_seconds}s` : '—'}
                      </td>
                      <td className="py-3.5 px-3 font-mono font-bold text-emerald-700">
                        {metrics.sensitivity ? `${(metrics.sensitivity * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3.5 px-3 font-mono font-bold text-sky-700">
                        {metrics.specificity ? `${(metrics.specificity * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3.5 px-3 text-gray-600">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Launch Job Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md bg-white text-black rounded-[32px] p-7 shadow-2xl border-4 border-white space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
                  <Zap className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-black text-lg">Launch Training Job</h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-500 hover:text-black transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitRun} className="space-y-4 text-xs">
              <div>
                <label className="block text-gray-700 font-bold mb-1">Target Training Dataset</label>
                <select
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all cursor-pointer"
                  required
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.version}) — {d.total_samples} samples
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-700 font-bold mb-1">Hyperparameter Preset</label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all cursor-pointer"
                >
                  <option value="quick_test">Quick Test (1 iteration, smoke check)</option>
                  <option value="standard_retina">Standard Retina (4 iterations, full curriculum)</option>
                  <option value="high_precision">High Precision (6 iterations, large batch)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-700 font-bold mb-1">Curriculum Iterations</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-bold mb-1">Batch Size</label>
                  <input
                    type="number"
                    min="4"
                    max="64"
                    step="4"
                    value={batchSize}
                    onChange={(e) => setBatchSize(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-full text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-full text-xs font-bold bg-[#1E54B7] hover:bg-[#184496] active:scale-95 text-white shadow-md disabled:opacity-50 transition-all cursor-pointer"
                >
                  {submitting ? 'Submitting...' : 'Launch Training'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

