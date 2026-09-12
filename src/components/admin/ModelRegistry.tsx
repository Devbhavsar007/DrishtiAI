import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { ModelVersion } from '../../types';
import { adminFetch } from '../../utils/adminApi';

export const ModelRegistry: React.FC = () => {
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const res = await adminFetch<{ models: ModelVersion[] }>('/api/admin/models');
      if (res.ok && res.data) {
        setModels(res.data.models || []);
      }
    } catch (e) {
      console.error('Failed to load models:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handlePromote = async (versionId: string) => {
    if (!confirm(`Are you sure you want to promote ${versionId} to active PRODUCTION?`)) return;
    try {
      setActionInProgress(true);
      const res = await adminFetch<{ success: boolean; error?: string }>('/api/admin/releases/promote', {
        method: 'POST',
        body: JSON.stringify({ model_version_id: versionId }),
      });
      if (res.ok) {
        alert('Model successfully promoted to active PRODUCTION!');
        await fetchModels();
      } else {
        alert(`Promotion blocked: ${res.error}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRollback = async () => {
    const reason = prompt('Enter authorized incident reason for emergency rollback:');
    if (!reason) return;

    try {
      setActionInProgress(true);
      const res = await adminFetch<{ success: boolean; error?: string }>('/api/admin/releases/rollback', {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
      if (res.ok) {
        alert('Emergency rollback completed successfully!');
        await fetchModels();
      } else {
        alert(`Rollback failed: ${res.error}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionInProgress(false);
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
              Model Registry &amp; Lifecycle
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <ShieldCheck className="w-2.5 h-2.5" />
              Safety Certified
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Immutable artifact versions, clinical safety thresholds, and governed production promotions
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={fetchModels}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleRollback}
            disabled={actionInProgress}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-rose-100 hover:bg-rose-200 text-rose-900 border border-rose-300 shadow-md transition-all cursor-pointer disabled:opacity-50"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-700" />
            <span>Emergency Rollback</span>
          </button>
        </div>
      </div>

      {/* Models Table Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Governed Model Versions
              </h2>
              <p className="text-xs text-gray-500">Cryptographically signed weights and clinical validation gates</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-sky-50 text-[#1E54B7] border border-sky-200">
            {models.length} Versions Registered
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Version ID</th>
                <th className="pb-3 px-3">Release Tag</th>
                <th className="pb-3 px-3">Architecture</th>
                <th className="pb-3 px-3">Lifecycle State</th>
                <th className="pb-3 px-3">Author / Pipeline</th>
                <th className="pb-3 px-3">Registration</th>
                <th className="pb-3 px-3 text-right">Promotion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400 font-medium">
                    No models registered in catalog yet.
                  </td>
                </tr>
              ) : (
                models.map((m) => {
                  const isProd = m.status === 'PRODUCTION';
                  const isAppr = m.status === 'APPROVED' || m.status === 'STAGED';
                  return (
                    <tr key={m.version_id} className="hover:bg-sky-50/50 transition-colors">
                      <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{m.version_id}</td>
                      <td className="py-3.5 px-3 font-mono text-gray-900 font-semibold">{m.version_tag}</td>
                      <td className="py-3.5 px-3 font-medium text-gray-700">{m.architecture}</td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold ${
                            isProd
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : m.status === 'APPROVED'
                              ? 'bg-sky-100 text-[#1E54B7] border border-sky-300'
                              : m.status === 'CANDIDATE'
                              ? 'bg-purple-100 text-purple-800 border border-purple-300'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {isProd && <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>}
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-gray-600">{m.created_by}</td>
                      <td className="py-3.5 px-3 text-gray-600">
                        {new Date(m.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-3 text-right">
                        {isAppr && !isProd && (
                          <button
                            onClick={() => handlePromote(m.version_id)}
                            disabled={actionInProgress}
                            className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-extrabold bg-[#1E54B7] hover:bg-[#184496] active:scale-95 text-white shadow-sm transition-all cursor-pointer"
                          >
                            <span>Promote to Prod</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        )}
                        {isProd && (
                          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-700 font-extrabold">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                            <span>Serving Live</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

