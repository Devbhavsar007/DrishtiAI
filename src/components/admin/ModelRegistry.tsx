import React, { useEffect, useState } from 'react';
import { ModelVersion } from '../../types';

export const ModelRegistry: React.FC = () => {
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/admin/models');
      if (res.ok) {
        const json = await res.json();
        setModels(json.models || []);
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
      const res = await fetch('/api/admin/releases/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_version_id: versionId }),
      });
      if (res.ok) {
        alert('Model successfully promoted to active PRODUCTION!');
        await fetchModels();
      } else {
        const err = await res.json();
        alert(`Promotion blocked: ${err.error}`);
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
      const res = await fetch('/api/admin/releases/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (res.ok) {
        alert('Emergency rollback completed successfully!');
        await fetchModels();
      } else {
        const err = await res.json();
        alert(`Rollback failed: ${err.error}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionInProgress(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Model Registry & Lifecycle</h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable artifact versions, clinical safety gates, and governed production releases
          </p>
        </div>
        <button
          onClick={handleRollback}
          disabled={actionInProgress}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 shadow-md transition-all flex items-center gap-1.5"
        >
          <span>🚨</span>
          <span>Emergency Rollback</span>
        </button>
      </div>

      {/* Models Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Version ID</th>
                <th className="pb-3 px-3">Tag</th>
                <th className="pb-3 px-3">Architecture</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3">Created By</th>
                <th className="pb-3 px-3">Registered At</th>
                <th className="pb-3 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No models registered in the catalog yet.
                  </td>
                </tr>
              ) : (
                models.map((m) => {
                  const isProd = m.status === 'PRODUCTION';
                  const isAppr = m.status === 'APPROVED' || m.status === 'STAGED';
                  return (
                    <tr key={m.version_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{m.version_id}</td>
                      <td className="py-3 px-3 font-mono text-slate-200">{m.version_tag}</td>
                      <td className="py-3 px-3 text-slate-300">{m.architecture}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            isProd
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ring-1 ring-emerald-500/20'
                              : m.status === 'APPROVED'
                              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                              : m.status === 'CANDIDATE'
                              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-400">{m.created_by}</td>
                      <td className="py-3 px-3 text-slate-400">
                        {new Date(m.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {isAppr && !isProd && (
                          <button
                            onClick={() => handlePromote(m.version_id)}
                            disabled={actionInProgress}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 transition-colors"
                          >
                            Promote to Prod
                          </button>
                        )}
                        {isProd && (
                          <span className="text-[11px] text-emerald-400 font-semibold flex items-center justify-end gap-1">
                            <span>●</span> Serving Live
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
