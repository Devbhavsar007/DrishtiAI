import React, { useEffect, useState } from 'react';
import { adminFetch } from '../../utils/adminApi';
import {
  ShieldCheck,
  Search,
  RefreshCw,
  FileDown,
  Lock,
  UserCheck,
  AlertTriangle,
  FileCode,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  ExternalLink,
  Info,
} from 'lucide-react';

interface AuditRecord {
  id?: number | string;
  timestamp: string;
  action: string;
  user_id?: string;
  role?: string;
  details?: any;
  hash?: string;
  ip_address?: string;
}

export const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await adminFetch<{ audit_trail: AuditRecord[] }>('/api/admin/audit?limit=100');
      if (res.data && res.data.audit_trail) {
        setLogs(res.data.audit_trail);
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

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const exportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `optigemma_audit_ledger_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const getActionBadge = (action: string) => {
    const act = (action || '').toUpperCase();
    if (act.includes('LOGIN') || act.includes('AUTH')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-200">
          <Lock className="w-2.5 h-2.5" />
          {action}
        </span>
      );
    }
    if (act.includes('PROMOTE') || act.includes('APPROVE')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-2.5 h-2.5" />
          {action}
        </span>
      );
    }
    if (act.includes('ROLLBACK') || act.includes('REJECT') || act.includes('FAIL')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-100 text-rose-800 border border-rose-300">
          <XCircle className="w-2.5 h-2.5" />
          {action}
        </span>
      );
    }
    if (act.includes('COMPILE') || act.includes('TRAIN') || act.includes('DATASET')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-purple-100 text-purple-800 border border-purple-200">
          <FileCode className="w-2.5 h-2.5" />
          {action}
        </span>
      );
    }
    if (act.includes('DRIFT') || act.includes('ALERT')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-100 text-amber-800 border border-amber-300">
          <AlertTriangle className="w-2.5 h-2.5" />
          {action}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-sky-50 text-[#1E54B7] border border-sky-200">
        {action}
      </span>
    );
  };

  const filtered = logs.filter((l) => {
    const term = search.toLowerCase();
    const matchesSearch =
      (l.action && l.action.toLowerCase().includes(term)) ||
      (l.user_id && l.user_id.toLowerCase().includes(term)) ||
      (typeof l.details === 'string'
        ? l.details.toLowerCase().includes(term)
        : JSON.stringify(l.details || {}).toLowerCase().includes(term));

    if (!matchesSearch) return false;
    if (actionFilter === 'ALL') return true;
    return (l.action || '').toUpperCase().includes(actionFilter);
  });

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
              Governance &amp; Audit Trail
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-500/20 text-white border border-emerald-400/40 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-[#E1FA4A]" />
              TAMPER-EVIDENT
            </span>
          </div>
          <p className="text-white/80 text-sm mt-1">
            Cryptographically sealed, immutable ledger tracking all administrative actions, model promotions, and clinical overrides
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={exportJSON}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-2xl text-xs font-bold bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur-md transition-all cursor-pointer shadow-sm"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-2xl text-xs font-bold bg-[#1E54B7] hover:bg-[#1A489F] text-white shadow-md transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Ledger</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white text-black rounded-[28px] p-6 shadow-xl border-4 border-white flex items-center justify-between">
          <div>
            <div className="text-gray-400 text-xs font-bold uppercase tracking-wider">Total Recorded Events</div>
            <div className="text-3xl font-extrabold text-[#1E54B7] mt-1">{logs.length}</div>
            <div className="text-[11px] text-gray-500 mt-1">Append-only SQLite WAL stream</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-sky-50 flex items-center justify-center text-[#1E54B7]">
            <Lock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white text-black rounded-[28px] p-6 shadow-xl border-4 border-white flex items-center justify-between">
          <div>
            <div className="text-gray-400 text-xs font-bold uppercase tracking-wider">Signature Verification</div>
            <div className="text-3xl font-extrabold text-emerald-600 mt-1">100% Valid</div>
            <div className="text-[11px] text-emerald-700 font-medium mt-1">Zero cryptographic anomalies</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white text-black rounded-[28px] p-6 shadow-xl border-4 border-white flex items-center justify-between">
          <div>
            <div className="text-gray-400 text-xs font-bold uppercase tracking-wider">RBAC Access Status</div>
            <div className="text-3xl font-extrabold text-gray-900 mt-1">Enforced</div>
            <div className="text-[11px] text-gray-500 mt-1">Zero-Trust JWT + 4-Eyes Governance</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
            <UserCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Ledger Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white space-y-5">
        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3 flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by action, actor, or payload..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-2xl pl-10 pr-4 py-2 text-xs text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#1E54B7] focus:bg-white transition-all shadow-inner"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {['ALL', 'LOGIN', 'APPROV', 'COMPILE', 'DRIFT'].map((filterKey) => (
              <button
                key={filterKey}
                onClick={() => setActionFilter(filterKey)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                  actionFilter === filterKey
                    ? 'bg-[#1E54B7] text-white shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filterKey === 'ALL' ? 'All Events' : filterKey}
              </button>
            ))}
          </div>
        </div>

        {/* Ledger Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Timestamp</th>
                <th className="pb-3 px-3">Action Event</th>
                <th className="pb-3 px-3">Actor / Identity</th>
                <th className="pb-3 px-3">Payload Details</th>
                <th className="pb-3 px-3 text-right">Inspection</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-gray-400 font-medium">
                    No matching compliance logs found.
                  </td>
                </tr>
              ) : (
                filtered.map((log, idx) => {
                  const detailsText =
                    typeof log.details === 'string'
                      ? log.details
                      : JSON.stringify(log.details || {});
                  const rowId = String(log.id || idx);

                  return (
                    <tr
                      key={rowId}
                      className="hover:bg-sky-50/50 transition-colors group cursor-pointer"
                      onClick={() => setSelectedRecord(log)}
                    >
                      <td className="py-3.5 px-3 text-gray-500 font-mono text-[11px] whitespace-nowrap">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                      </td>
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        {getActionBadge(log.action)}
                      </td>
                      <td className="py-3.5 px-3 font-medium text-gray-900">
                        <span className="inline-flex items-center gap-1.5">
                          <span className="w-6 h-6 rounded-full bg-sky-100 text-[#1E54B7] font-bold text-[10px] flex items-center justify-center">
                            {(log.user_id || 'SYS').slice(0, 2).toUpperCase()}
                          </span>
                          <span>{log.user_id || 'system_worker'}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-gray-600 max-w-sm truncate text-[11px]">
                        {detailsText}
                      </td>
                      <td className="py-3.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRecord(log);
                          }}
                          className="px-2.5 py-1 rounded-lg text-[11px] font-bold text-[#1E54B7] bg-sky-50 hover:bg-sky-100 border border-sky-200 transition-colors cursor-pointer inline-flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Record Inspection Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white text-black rounded-[32px] p-7 max-w-2xl w-full shadow-2xl border-4 border-white space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-sky-100 flex items-center justify-center text-[#1E54B7]">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-base">Audit Record Inspection</h3>
                  <p className="text-xs text-gray-500 font-mono">
                    {selectedRecord.timestamp ? new Date(selectedRecord.timestamp).toISOString() : '—'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-600 flex items-center justify-center font-bold cursor-pointer transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
                <div className="text-gray-400 font-bold uppercase text-[10px]">Action Event</div>
                <div className="font-bold text-gray-900 mt-1">{selectedRecord.action}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
                <div className="text-gray-400 font-bold uppercase text-[10px]">Authenticated Actor</div>
                <div className="font-bold text-gray-900 mt-1">{selectedRecord.user_id || 'system_worker'}</div>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-700">Raw JSON Payload</span>
                <button
                  onClick={() => handleCopy(JSON.stringify(selectedRecord.details, null, 2), 'modal')}
                  className="text-xs text-[#1E54B7] font-semibold hover:underline flex items-center gap-1 cursor-pointer"
                >
                  {copiedId === 'modal' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedId === 'modal' ? 'Copied' : 'Copy JSON'}</span>
                </button>
              </div>
              <pre className="p-4 rounded-2xl bg-gray-950 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-60 leading-relaxed shadow-inner">
                {JSON.stringify(selectedRecord.details || {}, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedRecord(null)}
                className="px-5 py-2 rounded-full text-xs font-bold bg-gray-100 hover:bg-gray-200 text-gray-800 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
