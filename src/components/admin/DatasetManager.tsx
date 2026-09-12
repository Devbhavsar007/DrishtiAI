import React, { useEffect, useState } from 'react';
import {
  Package,
  Plus,
  RotateCw,
  CheckCircle2,
  Lock,
  Layers,
  Sparkles,
  X,
  ShieldCheck,
} from 'lucide-react';
import { TrainingDataset } from '../../types';
import { adminFetch } from '../../utils/adminApi';

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
      const res = await adminFetch<{ datasets: TrainingDataset[] }>('/api/admin/datasets');
      if (res.ok && res.data) {
        setDatasets(res.data.datasets || []);
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
      const res = await adminFetch<{ success: boolean; dataset?: any; error?: string }>('/api/admin/datasets/build', {
        method: 'POST',
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
        alert(`Dataset build failed: ${res.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setBuilding(false);
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
              Dataset Registry &amp; Versioning
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <Package className="w-2.5 h-2.5" />
              Patient Isolated
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Immutable training manifests with patient-stratified cross validation and SHA-256 integrity
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchDatasets}
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
            <Plus className="w-4 h-4" />
            <span>Compile New Dataset</span>
          </button>
        </div>
      </div>

      {/* Dataset Table Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Immutable Training Datasets
              </h2>
              <p className="text-xs text-gray-500">Versioned snapshots ready for training orchestrator</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-sky-50 text-[#1E54B7] border border-sky-200">
            {datasets.length} Versions Compiled
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Dataset ID</th>
                <th className="pb-3 px-3">Family Name</th>
                <th className="pb-3 px-3">Version</th>
                <th className="pb-3 px-3">Total Images</th>
                <th className="pb-3 px-3">Patient Cohort</th>
                <th className="pb-3 px-3">Isolation State</th>
                <th className="pb-3 px-3">Compilation Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {datasets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400 font-medium">
                    No versioned datasets compiled yet. Click "Compile New Dataset" to generate one from synchronized clinical records.
                  </td>
                </tr>
              ) : (
                datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-sky-50/50 transition-colors">
                    <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{ds.id}</td>
                    <td className="py-3.5 px-3 text-gray-900 font-bold">{ds.name}</td>
                    <td className="py-3.5 px-3 font-mono text-gray-600 font-semibold">{ds.version}</td>
                    <td className="py-3.5 px-3 font-mono font-bold text-gray-900">{ds.total_samples}</td>
                    <td className="py-3.5 px-3 font-mono text-gray-700">{ds.total_patients} patients</td>
                    <td className="py-3.5 px-3">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        <ShieldCheck className="w-3 h-3" />
                        {ds.status || 'LOCKED_FINAL'}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-gray-600">
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md bg-white text-black rounded-[32px] p-7 shadow-2xl border-4 border-white space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
                  <Package className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-black text-lg">Compile Immutable Dataset</h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-500 hover:text-black transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleBuildDataset} className="space-y-4 text-xs">
              <div>
                <label className="block text-gray-700 font-bold mb-1">Dataset Family Tag</label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-700 font-bold mb-1">Validation Split</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="0.4"
                    value={valRatio}
                    onChange={(e) => setValRatio(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-bold mb-1 flex items-center gap-1">
                    <span>Test Split</span>
                    <Lock className="w-3 h-3 text-gray-400" />
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="0.3"
                    value={testRatio}
                    onChange={(e) => setTestRatio(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-gray-900 font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div className="p-3.5 bg-sky-50 border border-sky-100 rounded-2xl text-[11px] text-[#1E54B7] font-medium flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#1E54B7] shrink-0 mt-0.5" />
                <span>
                  <strong>Strict Patient-Level Partitioning:</strong> Scans from the same patient across all clinical visits will strictly remain in one split to guarantee 0% data leakage.
                </span>
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
                  disabled={building}
                  className="px-5 py-2 rounded-full text-xs font-bold bg-[#1E54B7] hover:bg-[#184496] active:scale-95 text-white shadow-md disabled:opacity-50 transition-all cursor-pointer"
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

