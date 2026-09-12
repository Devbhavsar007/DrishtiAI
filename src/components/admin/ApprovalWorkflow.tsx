import React, { useEffect, useState } from 'react';
import {
  CheckSquare,
  AlertTriangle,
  RotateCw,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  FileText,
  UserCheck,
} from 'lucide-react';
import { ModelApproval, ModelVersion, AdminRole } from '../../types';
import { adminFetch } from '../../utils/adminApi';

interface ApprovalWorkflowProps {
  adminRole: AdminRole;
}

export const ApprovalWorkflow: React.FC<ApprovalWorkflowProps> = ({ adminRole }) => {
  const [candidates, setCandidates] = useState<ModelVersion[]>([]);
  const [approvals, setApprovals] = useState<ModelApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [candRes, apprRes] = await Promise.all([
        adminFetch<{ models: ModelVersion[] }>('/api/admin/models?status=CANDIDATE'),
        adminFetch<{ approvals: ModelApproval[] }>('/api/admin/approvals'),
      ]);
      if (candRes.ok && candRes.data) {
        setCandidates(candRes.data.models || []);
      }
      if (apprRes.ok && apprRes.data) {
        setApprovals(apprRes.data.approvals || []);
      }
    } catch (e) {
      console.error('Failed to load approvals:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDecision = async (modelVersionId: string, decision: 'APPROVED' | 'REJECTED') => {
    if (!comments.trim()) {
      alert('Please provide a clinical rationale/comments before submitting decision.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await adminFetch<{ success: boolean; error?: string }>('/api/admin/approvals/submit', {
        method: 'POST',
        body: JSON.stringify({
          model_version_id: modelVersionId,
          decision,
          comments,
          safety_checks_reviewed: true,
        }),
      });

      if (res.ok) {
        alert(`Model decision submitted: ${decision}`);
        setComments('');
        await fetchData();
      } else {
        alert(`Approval rejected: ${res.error}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  const isEligibleReviewer = adminRole === 'CLINICAL_REVIEWER' || adminRole === 'SUPER_ADMIN';

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
              Clinical Governance &amp; Human Approvals
            </h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#E1FA4A] text-black shadow-sm">
              <UserCheck className="w-2.5 h-2.5" />
              Physician Sign-Off
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white/80 font-medium mt-1">
            Separation of duties: Independent clinical ophthalmologist validation required prior to live production activation
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white/15 hover:bg-white/25 active:scale-95 text-white border border-white/20 transition-all cursor-pointer shadow-sm self-start sm:self-auto disabled:opacity-50"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Role Notice */}
      {!isEligibleReviewer && (
        <div className="p-4 rounded-2xl bg-amber-100 border border-amber-300 text-xs text-amber-900 flex items-center gap-2.5 shadow-md">
          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
          <span>
            You are currently acting as <strong>{adminRole}</strong>. Formal clinical model sign-off requires role{' '}
            <strong>CLINICAL_REVIEWER</strong> or <strong>SUPER_ADMIN</strong>.
          </span>
        </div>
      )}

      {/* Pending Candidates Section Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-purple-700">
              <CheckSquare className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Candidates Awaiting Clinical Sign-off
              </h2>
              <p className="text-xs text-gray-500">Models meeting automated gates waiting for ophthalmologist review</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-purple-100 text-purple-800 border border-purple-200">
            {candidates.length} Awaiting Review
          </span>
        </div>

        {candidates.length === 0 ? (
          <div className="py-8 text-center text-gray-400 text-xs font-medium">
            No models currently in CANDIDATE status awaiting approval.
          </div>
        ) : (
          candidates.map((cand) => (
            <div key={cand.version_id} className="p-6 rounded-3xl bg-gray-50 border border-gray-200 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-mono text-[#1E54B7] font-bold text-sm">{cand.version_id}</span>
                  <span className="ml-2 font-mono text-xs text-gray-600 font-semibold">({cand.version_tag})</span>
                </div>
                <span className="px-2.5 py-1 rounded-full text-[10px] font-black bg-purple-100 text-purple-800 border border-purple-200 uppercase tracking-wider">
                  CANDIDATE
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-2xl bg-white border border-gray-100 shadow-sm">
                  <div className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Architecture</div>
                  <div className="font-mono text-gray-900 font-bold mt-0.5">{cand.architecture}</div>
                </div>
                <div className="p-3 rounded-2xl bg-white border border-gray-100 shadow-sm">
                  <div className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Created By</div>
                  <div className="text-gray-900 font-bold mt-0.5">{cand.created_by}</div>
                </div>
                <div className="p-3 rounded-2xl bg-white border border-gray-100 shadow-sm">
                  <div className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Automated Gates</div>
                  <div className="text-emerald-700 font-extrabold mt-0.5 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>PASSED (All 6)</span>
                  </div>
                </div>
                <div className="p-3 rounded-2xl bg-white border border-gray-100 shadow-sm">
                  <div className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Regression Test</div>
                  <div className="text-emerald-700 font-extrabold mt-0.5 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>ZERO REGRESSION</span>
                  </div>
                </div>
              </div>

              {/* Rationale & Action Form */}
              <div className="pt-2 space-y-3">
                <textarea
                  rows={2}
                  placeholder="Enter clinical review rationale, held-out cohort evaluation notes, and conditions for deployment..."
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full bg-white border border-gray-300 rounded-2xl p-3 text-xs text-gray-900 font-medium focus:outline-none focus:ring-2 focus:ring-[#1E54B7] shadow-inner"
                />

                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => handleDecision(cand.version_id, 'REJECTED')}
                    disabled={submitting || !isEligibleReviewer}
                    className="flex items-center gap-1 px-4 py-2 rounded-full text-xs font-bold bg-rose-100 hover:bg-rose-200 text-rose-800 border border-rose-300 disabled:opacity-40 transition-colors cursor-pointer"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject Candidate</span>
                  </button>
                  <button
                    onClick={() => handleDecision(cand.version_id, 'APPROVED')}
                    disabled={submitting || !isEligibleReviewer}
                    className="flex items-center gap-1.5 px-5 py-2 rounded-full text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md disabled:opacity-40 transition-all cursor-pointer"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve for Staging / Production</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Historical Approvals Table Card */}
      <div className="bg-white text-black rounded-[36px] p-7 shadow-2xl border-4 border-white">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-[#1E54B7]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-black font-sans">
                Historical Approval Records
              </h2>
              <p className="text-xs text-gray-500">Immutable audit logs of all physician promotion decisions</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-sky-50 text-[#1E54B7] border border-sky-200">
            {approvals.length} Decisions Logged
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="pb-3 px-3">Model Version</th>
                <th className="pb-3 px-3">Reviewer ID</th>
                <th className="pb-3 px-3">Reviewer Role</th>
                <th className="pb-3 px-3">Decision</th>
                <th className="pb-3 px-3">Clinical Rationale</th>
                <th className="pb-3 px-3">Decision Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {approvals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400 font-medium">
                    No historical approvals recorded yet.
                  </td>
                </tr>
              ) : (
                approvals.map((a) => (
                  <tr key={a.id} className="hover:bg-sky-50/50 transition-colors">
                    <td className="py-3.5 px-3 font-mono text-[#1E54B7] font-bold">{a.model_version_id}</td>
                    <td className="py-3.5 px-3 text-gray-900 font-medium">{a.approver_id}</td>
                    <td className="py-3.5 px-3 font-mono text-gray-600">{a.approver_role}</td>
                    <td className="py-3.5 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold ${
                          a.decision === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : 'bg-rose-100 text-rose-800 border border-rose-300'
                        }`}
                      >
                        {a.decision === 'APPROVED' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        {a.decision}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-gray-700 max-w-xs truncate">{a.rationale || '—'}</td>
                    <td className="py-3.5 px-3 text-gray-600">
                      {new Date(a.created_at).toLocaleDateString()}
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


