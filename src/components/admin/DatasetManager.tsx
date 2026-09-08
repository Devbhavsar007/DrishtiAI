import React, { useEffect, useState } from 'react';
import { TrainingDataset } from '../../types';

export const DatasetManager: React.FC = () => {
  const [datasets, setDatasets] = useState<TrainingDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [datasetName, setDatasetName] = useState('drishti-retina');
  const [valRatio, setValRatio] = useState('0.15');
  const [testRatio, setTestRatio] = useState('0.10');

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/admin/datasets');
      if (res.ok) {
        const json = await res.json();
        setDatasets(json.datasets || []);
      }
    } catch (e) {
      console.error('Failed to load datasets:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleBuildDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setBuilding(true);
      const res = await fetch('/api/admin/datasets/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: datasetName,
          val_ratio: parseFloat(valRatio),
          test_ratio: parseFloat(testRatio),
        }),
      });
      if (res.ok) {
        setShowModal(false);
        await fetchDatasets();
      } else {
        const err = await res.json();
        alert(`Dataset build failed: ${err.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dataset Registry & Versioning</h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable, patient-isolated training sets with SHA-256 manifest verification and zero leakage
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 transition-all flex items-center gap-1.5"
        >
          <span>📦</span>
          <span>Compile New Dataset</span>
        </button>
      </div>

      {/* Dataset Table Card */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Dataset ID</th>
                <th className="pb-3 px-3">Name / Family</th>
                <th className="pb-3 px-3">Version</th>
                <th className="pb-3 px-3">Total Samples</th>
                <th className="pb-3 px-3">Unique Patients</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {datasets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No versioned datasets compiled yet. Click "Compile New Dataset" to generate one from synchronized clinical data.
                  </td>
                </tr>
              ) : (
                datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{ds.id}</td>
                    <td className="py-3 px-3 text-slate-200 font-medium">{ds.name}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{ds.version}</td>
                    <td className="py-3 px-3 font-mono text-slate-200">{ds.total_samples}</td>
                    <td className="py-3 px-3 font-mono text-slate-200">{ds.total_patients}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {ds.status || 'FINALIZED'}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {new Date(ds.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Compile Dataset Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-white text-base">Compile Immutable Dataset</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleBuildDataset} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Dataset Family Name</label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Validation Ratio</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="0.4"
                    value={valRatio}
                    onChange={(e) => setValRatio(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Test Ratio (Locked)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="0.3"
                    value={testRatio}
                    onChange={(e) => setTestRatio(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="p-3 bg-cyan-950/30 border border-cyan-800/40 rounded-xl text-[11px] text-cyan-300">
                Patient-level grouping is enforced: images from the same patient across all visits will never cross split boundaries.
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
                  disabled={building}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 disabled:opacity-50"
                >
                  {building ? 'Compiling Manifest...' : 'Compile Dataset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
