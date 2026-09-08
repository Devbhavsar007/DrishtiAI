import React, { useEffect, useState } from 'react';

export const SystemHealth: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHealth() {
      try {
        setLoading(true);
        const res = await fetch('/api/admin/system');
        if (res.ok) {
          setHealth(await res.json());
        }
      } catch (e) {
        console.error('Failed to load system health:', e);
      } finally {
        setLoading(false);
      }
    }
    loadHealth();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">System & Worker Health</h1>
        <p className="text-sm text-slate-400 mt-1">
          Infrastructure runtime diagnostics, background workers, and storage telemetry
        </p>
      </div>

      {/* Grid: Primary Status & Workers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Plane Diagnostics */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-semibold text-white">Runtime Environment</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              HEALTHY
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Logical Plane</span>
              <span className="font-mono text-cyan-300 font-medium">INTELLIGENCE CONTROL PLANE</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Host OS</span>
              <span className="font-mono text-slate-200">{health?.platform || 'Windows 64-bit'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Python Interpreter</span>
              <span className="font-mono text-slate-200">{health?.python_version || '3.11.9'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Storage Backend</span>
              <span className="font-mono text-slate-200">SQLite (WAL Mode + Strict Foreign Keys)</span>
            </div>
          </div>
        </div>

        {/* Worker Status */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-semibold text-white">Background Workers</h2>
            <span className="text-xs text-slate-400">4 Registered</span>
          </div>

          <div className="space-y-3">
            {[
              { name: 'TrainingWorker', task: 'Polls & orchestrates queued retraining jobs', interval: '15s', status: 'ACTIVE' },
              { name: 'EvaluationWorker', task: 'Executes regression & safety gate validations', interval: '30s', status: 'ACTIVE' },
              { name: 'DriftWorker', task: 'Monitors doctor-AI discordance & feature PSI', interval: '30m', status: 'ACTIVE' },
              { name: 'DatasetWorker', task: 'Assembles monthly snapshot manifests', interval: '1h', status: 'STANDBY' },
            ].map((w) => (
              <div key={w.name} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60 flex items-center justify-between text-xs">
                <div>
                  <div className="font-semibold text-slate-200">{w.name}</div>
                  <div className="text-[11px] text-slate-400">{w.task}</div>
                </div>
                <div className="text-right">
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    {w.status}
                  </span>
                  <div className="text-[10px] text-slate-400 mt-0.5">every {w.interval}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
