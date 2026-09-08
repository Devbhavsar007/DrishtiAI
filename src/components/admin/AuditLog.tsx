import React, { useEffect, useState } from 'react';

export const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/admin/audit?limit=100');
      if (res.ok) {
        const json = await res.json();
        setLogs(json.audit_trail || []);
      }
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filtered = logs.filter((l) => {
    const term = search.toLowerCase();
    return (
      (l.action && l.action.toLowerCase().includes(term)) ||
      (l.user_id && l.user_id.toLowerCase().includes(term)) ||
      (l.details && l.details.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Governance Audit Trail</h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable, append-only compliance ledger tracking all administrative and MLOps actions
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Search audit trail..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-64"
          />
          <button
            onClick={fetchLogs}
            className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Audit Log Table Card */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Timestamp</th>
                <th className="pb-3 px-3">Action</th>
                <th className="pb-3 px-3">Actor</th>
                <th className="pb-3 px-3">Payload Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-400">
                    No matching audit entries found.
                  </td>
                </tr>
              ) : (
                filtered.map((log, idx) => (
                  <tr key={log.id || idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-3 font-semibold text-cyan-300 font-mono text-[11px]">
                      {log.action}
                    </td>
                    <td className="py-3 px-3 text-slate-200 font-medium">
                      {log.user_id || 'system'}
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400 max-w-md truncate">
                      {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
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
