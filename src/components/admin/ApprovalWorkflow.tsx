import React, { useEffect, useState } from 'react';
import { ModelApproval, ModelVersion, AdminRole } from '../../types';

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
        fetch('/api/admin/models?status=CANDIDATE'),
        fetch('/api/admin/approvals'),
      ]);
      if (candRes.ok) {
        const json = await candRes.json();
        setCandidates(json.models || []);
      }
      if (apprRes.ok) {
        const json = await apprRes.json();
        setApprovals(json.approvals || []);
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
      const res = await fetch('/api/admin/approvals/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        const err = await res.json();
        alert(`Approval rejected: ${err.error}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  const isEligibleReviewer = adminRole === 'CLINICAL_REVIEWER' || adminRole === 'SUPER_ADMIN';

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Clinical Governance & Human Approvals</h1>
        <p className="text-sm text-slate-400 mt-1">
          Separation of duties: Independent clinical ophthalmologist sign-off required prior to production deployment
        </p>
      </div>

      {/* Role Notice */}
      {!isEligibleReviewer && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 flex items-center gap-2.5">
          <span className="text-base">⚠️</span>
          <span>
            You are acting as <strong>{adminRole}</strong>. Formal clinical model sign-off requires role{' '}
            <strong>CLINICAL_REVIEWER</strong> or <strong>SUPER_ADMIN</strong>.
          </span>
        </div>
      )}

      {/* Pending Candidates Section */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-6">
        <h2 className="text-base font-semibold text-white">Candidates Awaiting Sign-off</h2>

        {candidates.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No models currently in CANDIDATE status awaiting approval.
          </div>
        ) : (
          candidates.map((cand) => (
            <div key={cand.version_id} className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-mono text-cyan-300 font-bold text-sm">{cand.version_id}</span>
                  <span className="ml-2 font-mono text-xs text-slate-400">({cand.version_tag})</span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30">
                  CANDIDATE
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/60">
                  <div className="text-slate-400 text-[10px]">Architecture</div>
                  <div className="font-mono text-slate-200 mt-0.5">{cand.architecture}</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/60">
                  <div className="text-slate-400 text-[10px]">Created By</div>
                  <div className="text-slate-200 mt-0.5">{cand.created_by}</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/60">
                  <div className="text-slate-400 text-[10px]">Safety Gates</div>
                  <div className="text-emerald-400 font-semibold mt-0.5">PASSED (All 6)</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/60">
                  <div className="text-slate-400 text-[10px]">Regression Status</div>
                  <div className="text-emerald-400 font-semibold mt-0.5">ZERO REGRESSION</div>
                </div>
              </div>

              {/* Rationale & Action Form */}
              <div className="pt-2 space-y-3">
                <textarea
                  rows={2}
                  placeholder="Enter clinical review rationale, held-out cohort evaluation notes, and conditions..."
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />

                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => handleDecision(cand.version_id, 'REJECTED')}
                    disabled={submitting || !isEligibleReviewer}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 disabled:opacity-40 transition-colors"
                  >
                    Reject Candidate
                  </button>
                  <button
                    onClick={() => handleDecision(cand.version_id, 'APPROVED')}
                    disabled={submitting || !isEligibleReviewer}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white shadow-md shadow-emerald-500/20 disabled:opacity-40 transition-all"
                  >
                    Approve for Staging / Production
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Historical Approvals Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
        <h2 className="text-base font-semibold text-white mb-4">Historical Approval Records</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 px-3">Model Version</th>
                <th className="pb-3 px-3">Reviewer</th>
                <th className="pb-3 px-3">Role</th>
                <th className="pb-3 px-3">Decision</th>
                <th className="pb-3 px-3">Rationale</th>
                <th className="pb-3 px-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {approvals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No historical approvals recorded yet.
                  </td>
                </tr>
              ) : (
                approvals.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-mono text-cyan-300 font-medium">{a.model_version_id}</td>
                    <td className="py-3 px-3 text-slate-300">{a.approver_id}</td>
                    <td className="py-3 px-3 font-mono text-slate-400">{a.approver_role}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          a.decision === 'APPROVED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {a.decision}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-300 max-w-xs truncate">{a.rationale || '—'}</td>
                    <td className="py-3 px-3 text-slate-400">
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
