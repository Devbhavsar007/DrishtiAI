import React, { useState } from 'react';
import {
  Layers,
  Play,
  Trash2,
  FileSpreadsheet,
  PlusCircle,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Eye,
  UserPlus,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { useAccessibility } from '../context/AccessibilityContext';
import { DualCodedBadge } from './DualCodedBadge';
import { createFundusDataUrl } from '../data/sampleFundusPresets';
import { BatchQueueItem } from '../types';

export const BatchScreeningView: React.FC = () => {
  const {
    batchQueue,
    processBatchQueue,
    removeFromBatchQueue,
    clearBatchQueue,
    addToBatchQueue,
    setActiveScan,
    setActivePatient,
    setActiveView,
    patients,
  } = useMedicalData();

  const { speak } = useAccessibility();

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [showAddModal, setShowAddModal] = useState(false);

  const [quickForm, setQuickForm] = useState({
    patient_name: '',
    age: 58,
    gender: 'Male' as 'Male' | 'Female' | 'Other',
    diabetes_duration: 8,
    sugar_level: 175,
    hba1c: 8.2,
  });

  const queuedCount = batchQueue.filter((q) => q.status === 'QUEUED').length;
  const completedCount = batchQueue.filter((q) => q.status === 'COMPLETED' || q.status === 'REQUIRES_ATTENTION').length;
  const highRiskCount = batchQueue.filter((q) => q.status === 'REQUIRES_ATTENTION').length;

  const handleStartBatch = async () => {
    if (batchQueue.length === 0) return;
    setIsProcessing(true);
    speak(`Starting batch screening of ${batchQueue.length} patient scans.`);

    await processBatchQueue((current, total) => {
      setProgress({ current, total });
    });

    setIsProcessing(false);
    speak('Batch screening complete. All queued scans processed.');
  };

  const handleInspectResult = (item: BatchQueueItem) => {
    if (item.result) {
      setActiveScan(item.result);
      const matched = patients.find((p) => p.id === item.patient_id);
      if (matched) setActivePatient(matched);
      setActiveView('new-scan');
    }
  };

  const handleAddPatientToQueue = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickForm.patient_name.trim()) return;

    // Select random preset fundus image based on glucose level
    const stage = quickForm.hba1c >= 9 ? 3 : quickForm.hba1c >= 7.5 ? 2 : 1;
    const imageUrl = createFundusDataUrl(stage, 'original');

    addToBatchQueue({
      ...quickForm,
      image_url: imageUrl,
    });

    setQuickForm({
      patient_name: '',
      age: 55,
      gender: 'Male',
      diabetes_duration: 6,
      sugar_level: 150,
      hba1c: 7.2,
    });
    setShowAddModal(false);
  };

  const handleExportCSV = () => {
    const headers = ['Patient Name', 'Age', 'Gender', 'HbA1c', 'Blood Sugar', 'Duration', 'Status', 'Diagnosis', 'Confidence'];
    const rows = batchQueue.map((item) => [
      item.patient_name,
      item.age,
      item.gender,
      `${item.hba1c}%`,
      `${item.sugar_level} mg/dL`,
      `${item.diabetes_duration} yrs`,
      item.status,
      item.result ? item.result.detection.stage_name : 'Pending',
      item.result ? `${item.result.detection.confidence}%` : 'N/A',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `DrishtiAI_Batch_Screening_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 sm:p-7 bg-white text-black rounded-3xl sm:rounded-[36px] shadow-2xl border-2 sm:border-4 border-white">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-[#1E54B7] text-xs font-black">
            <Layers className="w-4 h-4" />
            <span>High-Throughput Mobile Van Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-black flex items-center gap-3 font-sans">
            Batch Screening Queue
          </h1>
          <p className="text-xs sm:text-base text-gray-600 font-medium">
            High-throughput pipeline for community outreach vans and rural screening camps
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 w-full sm:w-auto">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 sm:px-5 py-2.5 sm:py-3 rounded-full bg-gray-100 hover:bg-gray-200 text-black font-black text-xs uppercase tracking-wider transition-all min-h-[44px] cursor-pointer"
          >
            <UserPlus className="w-4 h-4 text-[#1E54B7]" />
            <span>Add Patient</span>
          </button>

          <button
            onClick={handleStartBatch}
            disabled={isProcessing || queuedCount === 0}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 sm:px-7 py-2.5 sm:py-3 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] disabled:opacity-40 text-black font-black text-xs uppercase tracking-wider shadow-lg hover:scale-105 transition-all min-h-[44px] cursor-pointer"
          >
            {isProcessing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            <span>{isProcessing ? 'Processing...' : `Process All (${queuedCount})`}</span>
          </button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 sm:gap-5">
        <div className="p-5 sm:p-6 bg-white text-black rounded-2xl sm:rounded-[28px] border-2 sm:border-4 border-white shadow-xl flex items-center justify-between">
          <div>
            <span className="text-[11px] sm:text-xs font-black uppercase tracking-wider text-gray-500 block">
              Waiting in Queue
            </span>
            <span className="text-3xl sm:text-4xl font-black text-[#1E54B7] font-mono mt-1 block">
              {queuedCount}
            </span>
          </div>
          <div className="p-3 sm:p-3.5 rounded-2xl bg-sky-100 text-[#1E54B7]">
            <Clock className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>

        <div className="p-5 sm:p-6 bg-white text-black rounded-2xl sm:rounded-[28px] border-2 sm:border-4 border-white shadow-xl flex items-center justify-between">
          <div>
            <span className="text-[11px] sm:text-xs font-black uppercase tracking-wider text-gray-500 block">
              Successfully Analyzed
            </span>
            <span className="text-3xl sm:text-4xl font-black text-emerald-700 font-mono mt-1 block">
              {completedCount}
            </span>
          </div>
          <div className="p-3 sm:p-3.5 rounded-2xl bg-emerald-100 text-emerald-700">
            <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>

        <div className="p-5 sm:p-6 bg-white text-black rounded-2xl sm:rounded-[28px] border-2 sm:border-4 border-rose-200/80 shadow-xl flex items-center justify-between">
          <div>
            <span className="text-[11px] sm:text-xs font-black uppercase tracking-wider text-gray-500 block">
              High Risk / Urgent
            </span>
            <span className="text-3xl sm:text-4xl font-black text-rose-600 font-mono mt-1 block">
              {highRiskCount}
            </span>
          </div>
          <div className="p-3 sm:p-3.5 rounded-2xl bg-rose-100 text-rose-600">
            <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>
      </div>

      {/* Active Processing Progress Bar */}
      {isProcessing && (
        <div className="p-6 bg-white text-black rounded-[28px] border-4 border-white space-y-3 shadow-2xl">
          <div className="flex items-center justify-between text-sm font-bold">
            <span className="flex items-center gap-2 text-black">
              <RefreshCw className="w-4 h-4 text-[#1E54B7] animate-spin" />
              Batch Inference Pipeline in Progress...
            </span>
            <span className="font-mono text-[#1E54B7] font-black">
              {progress.current} of {progress.total} Completed
            </span>
          </div>

          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#1E54B7] to-teal-500 rounded-full transition-all duration-300"
              style={{ width: `${(progress.current / Math.max(progress.total, 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Queue Table */}
      <div className="p-5 sm:p-7 bg-white text-black rounded-3xl sm:rounded-[36px] shadow-2xl border-2 sm:border-4 border-white space-y-5 sm:space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-lg sm:text-xl font-bold text-black">Queued Patient Records ({batchQueue.length})</h2>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleExportCSV}
              disabled={batchQueue.length === 0}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-black transition-all cursor-pointer"
            >
              <FileSpreadsheet className="w-4 h-4 text-[#1E54B7]" />
              <span>Export CSV</span>
            </button>

            <button
              onClick={clearBatchQueue}
              disabled={batchQueue.length === 0}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-black transition-all cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear Queue</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-gray-200 touch-momentum no-scrollbar">
          <table className="w-full text-left border-collapse min-w-[560px]" role="table">
            <thead>
              <tr className="bg-gray-100 text-gray-700 text-[11px] uppercase tracking-wider border-b border-gray-200">
                <th className="p-4 font-black">Scan Preview</th>
                <th className="p-4 font-black">Patient Details</th>
                <th className="p-4 font-black">Vitals</th>
                <th className="p-4 font-black">Status</th>
                <th className="p-4 font-black">AI Diagnosis</th>
                <th className="p-4 font-black text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {batchQueue.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-400 font-medium text-xs">
                    No scans in the queue. Click "Add Patient" above.
                  </td>
                </tr>
              ) : (
                batchQueue.map((item) => (
                  <tr key={item.id} className="hover:bg-sky-50/80 transition-colors">
                    <td className="p-4">
                      <div className="w-12 h-12 rounded-xl bg-black overflow-hidden border border-gray-300 shadow-sm shrink-0">
                        <img
                          src={item.image_url}
                          alt="Fundus thumb"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </td>

                    <td className="p-4">
                      <div className="font-bold text-black">{item.patient_name}</div>
                      <span className="text-xs text-gray-500">
                        {item.age} yrs • {item.gender}
                      </span>
                    </td>

                    <td className="p-4 text-xs font-mono text-gray-700">
                      <div>HbA1c: <strong className="text-black">{item.hba1c}%</strong></div>
                      <div>Sugar: {item.sugar_level} mg/dL</div>
                    </td>

                    <td className="p-4">
                      {item.status === 'QUEUED' && (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-black font-mono">
                          <Clock className="w-3.5 h-3.5" /> Queued
                        </span>
                      )}
                      {item.status === 'ANALYZING' && (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-sky-100 text-[#1E54B7] text-xs font-black">
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Analyzing
                        </span>
                      )}
                      {item.status === 'COMPLETED' && (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-black">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                        </span>
                      )}
                      {item.status === 'REQUIRES_ATTENTION' && (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-100 text-rose-700 text-xs font-black">
                          <AlertTriangle className="w-3.5 h-3.5" /> High Risk
                        </span>
                      )}
                    </td>

                    <td className="p-4">
                      {item.result ? (
                        <DualCodedBadge stage={item.result.detection.stage} size="sm" />
                      ) : (
                        <span className="text-xs text-gray-400 font-mono">Pending inference</span>
                      )}
                    </td>

                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {item.result && (
                          <button
                            onClick={() => handleInspectResult(item)}
                            className="p-2 rounded-full bg-sky-100 hover:bg-[#1E54B7] text-[#1E54B7] hover:text-white transition-all cursor-pointer"
                            title="Inspect Diagnosis"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => removeFromBatchQueue(item.id)}
                          className="p-2 rounded-full bg-rose-50 hover:bg-rose-100 text-rose-600 transition-all cursor-pointer"
                          title="Remove from Queue"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Patient Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-white text-black border-4 border-white rounded-[32px] shadow-2xl overflow-hidden p-7 space-y-5">
            <h3 className="text-2xl font-bold text-black font-sans">Add Patient to Batch Queue</h3>

            <form onSubmit={handleAddPatientToQueue} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-500 mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={quickForm.patient_name}
                  onChange={(e) => setQuickForm({ ...quickForm, patient_name: e.target.value })}
                  placeholder="e.g. Ramesh Chandra"
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black focus:border-[#1E54B7] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Age</label>
                  <input
                    type="number"
                    value={quickForm.age}
                    onChange={(e) => setQuickForm({ ...quickForm, age: Number(e.target.value) })}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-500 mb-1">HbA1c (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={quickForm.hba1c}
                    onChange={(e) => setQuickForm({ ...quickForm, hba1c: Number(e.target.value) })}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-5 py-2.5 rounded-full bg-gray-100 text-gray-700 font-bold text-xs uppercase tracking-wider cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-7 py-2.5 rounded-full bg-[#E1FA4A] text-black font-black text-xs uppercase tracking-wider shadow-md hover:scale-105 transition-all cursor-pointer"
                >
                  Add to Queue
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
