import React, { useEffect, useState } from 'react';
import { TrainingRun, TrainingDataset } from '../../types';

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
        fetch('/api/admin/training'),
        fetch('/api/admin/datasets'),
      ]);
      if (runsRes.ok) {
        const json = await runsRes.json();
        setRuns(json.runs || []);
      }
      if (dsRes.ok) {
        const json = await dsRes.json();
        setDatasets(json.datasets || []);
        if (json.datasets && json.datasets.length > 0 && !datasetId) {
          setDatasetId(json.datasets[0].id);
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
      const res = await fetch('/api/admin/training/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        const err = await res.json();
        alert(`Failed to launch training run: ${err.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Training Orchestrator</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage closed-loop curriculum training, hard-example mining, and model checkpoints
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 transition-all flex items-center gap-1.5"
        >
          <span>⚡</span>
          <span>Launch Training Job</span>
        </button>
      </div>

      {/* Runs Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Run ID</th>
                <th className="pb-3 px-3">Dataset</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3">Duration</th>
                <th className="pb-3 px-3">Sensitivity</th>
                <th className="pb-3 px-3">Specificity</th>
                <th className="pb-3 px-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No training runs submitted yet. Click "Launch Training Job" to begin training.
                  </td>
                </tr>
              ) : (
                runs.map((r) => {
                  const metrics = r.final_metrics_json || {};
                  return (
                    <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{r.id}</td>
                      <td className="py-3 px-3 font-mono text-slate-300">{r.dataset_id}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            r.status === 'COMPLETED'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : r.status === 'RUNNING'
                              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse'
                              : r.status === 'FAILED'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400">
                        {r.duration_seconds ? `${r.duration_seconds}s` : '—'}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">
                        {metrics.sensitivity ? `${(metrics.sensitivity * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">
                        {metrics.specificity ? `${(metrics.specificity * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3 px-3 text-slate-400">
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-white text-base">Launch Training Run</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitRun} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Target Training Dataset</label>
                <select
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 cursor-pointer"
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
                <label className="block text-slate-300 font-medium mb-1">Hyperparameter Preset</label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="quick_test">Quick Test (1 iteration, smoke check)</option>
                  <option value="standard_retina">Standard Retina (4 iterations, full curriculum)</option>
                  <option value="high_precision">High Precision (6 iterations, large batch)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Curriculum Iterations</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Batch Size</label>
                  <input
                    type="number"
                    min="4"
                    max="64"
                    step="4"
                    value={batchSize}
                    onChange={(e) => setBatchSize(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 disabled:opacity-50"
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
