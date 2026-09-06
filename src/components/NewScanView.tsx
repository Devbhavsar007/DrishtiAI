import React, { useState, useRef } from 'react';
import {
  Microscope,
  Upload,
  UserCheck,
  UserPlus,
  Zap,
  CheckCircle2,
  AlertTriangle,
  FileDown,
  Volume2,
  VolumeX,
  Languages,
  Maximize2,
  RefreshCw,
  Eye,
  Layers,
  Flame,
  Activity,
  Calendar,
  Sparkles,
  Search,
  CheckSquare,
  Utensils,
  ShieldAlert,
  AlertOctagon,
  ShieldCheck,
  Info,
  FlaskConical,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { useAccessibility } from '../context/AccessibilityContext';
import { PRESET_FUNDUS_CASES, PresetFundusCase } from '../data/sampleFundusPresets';
import { DR_STAGES, DRStage, Patient, ScanAnalysis } from '../types';
import { REPORT_TRANSLATIONS } from '../data/translations';
import { generateLargePrintPDF } from '../utils/pdfGenerator';
import { generateLocalizedDiagnosticSpeechScript, SpeechLanguage } from '../utils/accessibility';
import { DualCodedBadge } from './DualCodedBadge';
import { ImageLightboxModal } from './ImageLightboxModal';
import { DoctorReviewSection } from './DoctorReviewSection';
import { MedicalRAGDrawer } from './MedicalRAGDrawer';
import { BookOpen } from 'lucide-react';

const DEMO_SCENARIOS = [
  { id: 'NORMAL', label: '1. Normal Fundus', stage: 'Stage 0', category: 'Standard', desc: 'Annual recall' },
  { id: 'MILD_NPDR', label: '2. Mild NPDR', stage: 'Stage 1', category: 'Standard', desc: '6-12m follow-up' },
  { id: 'MODERATE_NPDR', label: '3. Moderate NPDR', stage: 'Stage 2', category: 'Standard', desc: 'Specialist referral' },
  { id: 'SEVERE_PDR', label: '4. Proliferative DR', stage: 'Stage 4', category: 'Standard', desc: 'Urgent escalation' },
  { id: 'POOR_QUALITY', label: '5. Quality Reject', stage: 'Safety', category: 'Gate', desc: 'Optical blur block' },
  { id: 'LOW_CONFIDENCE', label: '6. Low Confidence', stage: 'Safety', category: 'Gate', desc: 'Uncertainty flag' },
  { id: 'OOD_NON_FUNDUS', label: '7. Non-Fundus OOD', stage: 'Safety', category: 'Gate', desc: 'Artifact rejection' },
  { id: 'MODEL_DISAGREEMENT', label: '8. Disagreement', stage: 'Safety', category: 'Gate', desc: 'Consensus conflict' },
  { id: 'LATERALITY_MISMATCH', label: '9. Laterality Warning', stage: 'Safety', category: 'Gate', desc: 'OD/OS mismatch' },
  { id: 'OFFLINE_SYNC', label: '10. Offline Sync', stage: 'Reliability', category: 'Sync', desc: 'Ledger sync queue' },
];

type PatientMode = 'existing' | 'new' | 'quick';

export const NewScanView: React.FC = () => {
  const {
    patients,
    activePatient,
    setActivePatient,
    activeScan,
    setActiveScan,
    analyzeScan,
    addPatient,
    reportLanguage,
    setReportLanguage,
    setActiveView,
  } = useMedicalData();

  const { speak, stopSpeech, isSpeaking } = useAccessibility();

  // Workflow State
  const [patientMode, setPatientMode] = useState<PatientMode>('existing');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<PresetFundusCase | null>(PRESET_FUNDUS_CASES[2]);
  const [previewUrl, setPreviewUrl] = useState<string>(PRESET_FUNDUS_CASES[2].originalImage);

  // New Patient Form State
  const [newPatientForm, setNewPatientForm] = useState({
    name: '',
    age: 55,
    gender: 'Male' as 'Male' | 'Female' | 'Other',
    diabetes_duration: 8,
    sugar_level: 160,
    hba1c: 7.8,
    phone: '',
    notes: '',
  });

  // Loading Step Simulation
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);

  // Eye Laterality & Operator Session State
  const [selectedEye, setSelectedEye] = useState<'OD' | 'OS'>('OD');
  const [demoSuiteOpen, setDemoSuiteOpen] = useState(true);

  // Lightbox Modal State
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [ragDrawerOpen, setRagDrawerOpen] = useState(false);

  // Inverted / High contrast preview filter states for the 3 triptych cards
  const [invertOriginal, setInvertOriginal] = useState(false);
  const [invertVessels, setInvertVessels] = useState(false);
  const [invertHeatmap, setInvertHeatmap] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Run isolated demonstration scenario
  const handleRunDemoScenario = async (scenarioId: string) => {
    setIsAnalyzing(true);
    setLoadingStep(1);
    try {
      const res = await fetch('/api/demo/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: scenarioId }),
      });
      const data = await res.json();
      if (data.success && data.result) {
        const sim = data.result;
        const simPatient: Patient = {
          id: sim.patient_id,
          name: sim.scenario.patient?.name || 'Demo Subject',
          age: sim.scenario.patient?.age || 55,
          gender: 'Male',
          diabetes_duration: sim.scenario.patient?.diabetes_duration || 8,
          sugar_level: 160,
          hba1c: sim.scenario.patient?.hba1c || 7.8,
          created_at: new Date().toISOString(),
        };
        setActivePatient(simPatient);
        await analyzeScan(simPatient, {
          preset: selectedPreset || undefined,
          eye: (sim.scenario.operator_eye as 'OD' | 'OS') || selectedEye,
          demoScenario: sim,
        });
        speak(`Loaded demo scenario: ${sim.scenario.title}`);
      } else {
        alert(data.error || 'Failed to run demo scenario.');
      }
    } catch (err) {
      console.error(err);
      alert('Demo API call failed. Ensure backend is running.');
    } finally {
      setIsAnalyzing(false);
      setLoadingStep(0);
    }
  };

  // File Upload Handlers
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setSelectedPreset(null);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setSelectedPreset(null);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSelectPreset = (preset: PresetFundusCase) => {
    setSelectedPreset(preset);
    setSelectedFile(null);
    setPreviewUrl(preset.originalImage);

    // Auto update quick patient form fields if needed
    setNewPatientForm((prev) => ({
      ...prev,
      name: preset.patientName,
      age: preset.age,
      gender: preset.gender,
      diabetes_duration: preset.diabetesDuration,
      sugar_level: preset.sugarLevel,
      hba1c: preset.hba1c,
    }));
  };

  const handleStartAnalysis = async () => {
    // Resolve or create assigned patient
    let patientToUse = activePatient;

    if (patientMode === 'new') {
      if (!newPatientForm.name.trim()) {
        alert('Please enter patient full name');
        return;
      }
      patientToUse = addPatient(newPatientForm);
    } else if (patientMode === 'quick') {
      patientToUse = addPatient({
        name: selectedPreset ? selectedPreset.patientName : 'Screening Patient',
        age: selectedPreset ? selectedPreset.age : 52,
        gender: selectedPreset ? selectedPreset.gender : 'Female',
        diabetes_duration: selectedPreset ? selectedPreset.diabetesDuration : 6,
        sugar_level: selectedPreset ? selectedPreset.sugarLevel : 145,
        hba1c: selectedPreset ? selectedPreset.hba1c : 7.2,
      });
    }

    if (!patientToUse) {
      if (patients.length > 0) {
        patientToUse = patients[0];
        setActivePatient(patientToUse);
      } else {
        alert('Please assign a patient first.');
        return;
      }
    }

    setIsAnalyzing(true);
    setLoadingStep(1);

    // Sequential accessible step progress
    await new Promise((r) => setTimeout(r, 600));
    setLoadingStep(2);
    await new Promise((r) => setTimeout(r, 700));
    setLoadingStep(3);
    await new Promise((r) => setTimeout(r, 700));
    setLoadingStep(4);
    await new Promise((r) => setTimeout(r, 800));

    try {
      const result = await analyzeScan(patientToUse, {
        file: selectedFile || undefined,
        preset: selectedPreset || undefined,
        eye: selectedEye,
      });
      setIsAnalyzing(false);
      setLoadingStep(0);

      // Auto-trigger screen reader alert
      speak(`AI Analysis complete. Diagnosis: ${result.detection.stage_name} with ${result.detection.confidence}% confidence.`);
    } catch (err) {
      console.error(err);
      setIsAnalyzing(false);
      setLoadingStep(0);
      alert('Error analyzing image. Please try again.');
    }
  };

  const handleListenDiagnosis = () => {
    if (!activeScan) return;
    if (isSpeaking) {
      stopSpeech();
      return;
    }

    const langKey: SpeechLanguage =
      reportLanguage === 'hindi' ? 'hi' : reportLanguage === 'gujarati' ? 'gu' : 'en';

    const { script, langCode } = generateLocalizedDiagnosticSpeechScript(
      activePatient?.name || activeScan.patient_name || 'Patient',
      activeScan.detection.stage_name,
      activeScan.detection.confidence.toFixed(1),
      activeScan.report.current_diagnosis.plain_language,
      activeScan.report.urgency,
      activeScan.report.recommended_follow_up,
      activeScan.report.action_plan,
      langKey
    );

    speak(script, { lang: langCode });
  };

  const handleDownloadPDF = () => {
    if (!activeScan) return;
    generateLargePrintPDF(activeScan, activePatient);
  };

  const handleResetScan = () => {
    setActiveScan(null);
    setSelectedFile(null);
    setSelectedPreset(PRESET_FUNDUS_CASES[1]);
    setPreviewUrl(PRESET_FUNDUS_CASES[1].originalImage);
  };

  // Filtered patients for Step 1 search
  const searchedPatients = patients.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const translatedReport = activeScan ? REPORT_TRANSLATIONS[reportLanguage](activeScan.report) : null;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* ─────────────────────────────────────────────────────────────
          SECTION: WORKFLOW FORM (Shown when no scan result is active or during new analysis)
      ────────────────────────────────────────────────────────────── */}
      {!activeScan && !isAnalyzing && (
        <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
          {/* Header */}
          <div className="p-7 bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-[#1E54B7] text-xs font-black mb-1">
              <Microscope className="w-4 h-4" />
              <span>Multi-Modal AI Pipeline</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold text-black flex items-center gap-3 font-sans">
              New Retinal Scan & AI Analysis
            </h1>
            <p className="text-sm sm:text-base text-gray-600 font-medium">
              Instant Diabetic Retinopathy screening with EfficientNet-B3, Grad-CAM explainability, and Gemma-4
            </p>
          </div>

          {/* STEP 1: Patient Assignment */}
          <div className="p-7 sm:p-8 bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl sm:text-2xl font-bold text-black flex items-center gap-3 font-sans">
                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[#1E54B7] text-white text-sm font-black">
                  1
                </span>
                Step 1: Patient Assignment
              </h2>

              {activePatient && (
                <div className="hidden sm:inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-200 text-xs font-black">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                  <span>Assigned: {activePatient.name} ({activePatient.id})</span>
                </div>
              )}
            </div>

            {/* Accessible Mode Tabs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-1.5 bg-gray-100 rounded-full border border-gray-200">
              <button
                type="button"
                onClick={() => setPatientMode('existing')}
                className={`flex items-center justify-center gap-2 py-3 px-4 rounded-full font-black text-xs uppercase tracking-wider transition-all min-h-[44px] cursor-pointer ${
                  patientMode === 'existing'
                    ? 'bg-black text-white shadow-md'
                    : 'text-gray-600 hover:text-black hover:bg-gray-200/60'
                }`}
              >
                <UserCheck className="w-4 h-4" />
                <span>Existing Patient</span>
              </button>

              <button
                type="button"
                onClick={() => setPatientMode('new')}
                className={`flex items-center justify-center gap-2 py-3 px-4 rounded-full font-black text-xs uppercase tracking-wider transition-all min-h-[44px] cursor-pointer ${
                  patientMode === 'new'
                    ? 'bg-black text-white shadow-md'
                    : 'text-gray-600 hover:text-black hover:bg-gray-200/60'
                }`}
              >
                <UserPlus className="w-4 h-4" />
                <span>New Patient Registry</span>
              </button>

              <button
                type="button"
                onClick={() => setPatientMode('quick')}
                className={`flex items-center justify-center gap-2 py-3 px-4 rounded-full font-black text-xs uppercase tracking-wider transition-all min-h-[44px] cursor-pointer ${
                  patientMode === 'quick'
                    ? 'bg-black text-white shadow-md'
                    : 'text-gray-600 hover:text-black hover:bg-gray-200/60'
                }`}
              >
                <Zap className="w-4 h-4" />
                <span>Quick Camp Screening</span>
              </button>
            </div>

            {/* Mode 1: Search Existing Patient */}
            {patientMode === 'existing' && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-4 top-3.5 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by patient name, ID (e.g. Rajesh, P-1001)..."
                    className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-black placeholder-gray-400 font-medium focus:border-[#1E54B7] focus:ring-2 focus:ring-sky-100 focus:outline-none transition-all"
                  />
                </div>

                {/* Patient List */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-60 overflow-y-auto pr-1">
                  {searchedPatients.map((p) => {
                    const isSelected = activePatient?.id === p.id;
                    return (
                      <div
                        key={p.id}
                        onClick={() => setActivePatient(p)}
                        className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-sky-50/90 border-[#1E54B7] shadow-md ring-2 ring-sky-100'
                            : 'bg-gray-50/70 border-gray-200 hover:bg-white hover:border-gray-300 hover:shadow-sm'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-black text-base">{p.name}</span>
                          <span className="text-xs font-mono text-[#1E54B7] font-bold bg-sky-100 px-2.5 py-0.5 rounded-full">
                            {p.id}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 font-medium mt-1">
                          Age: {p.age} | HbA1c: {p.hba1c}% | Sugar: {p.sugar_level} mg/dL
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Mode 2: New Patient Registration Form */}
            {patientMode === 'new' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="space-y-1 sm:col-span-2">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500">
                    Patient Full Name *
                  </label>
                  <input
                    type="text"
                    value={newPatientForm.name}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, name: e.target.value })}
                    placeholder="e.g. Meera Desai"
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black focus:border-[#1E54B7] focus:outline-none"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500">
                    Age & Gender
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      value={newPatientForm.age}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, age: Number(e.target.value) })}
                      className="w-20 px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                    />
                    <select
                      value={newPatientForm.gender}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, gender: e.target.value as any })}
                      className="flex-1 px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500">
                    Diabetes Duration (Years)
                  </label>
                  <input
                    type="number"
                    value={newPatientForm.diabetes_duration}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, diabetes_duration: Number(e.target.value) })}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500">
                    Fasting Blood Sugar (mg/dL)
                  </label>
                  <input
                    type="number"
                    value={newPatientForm.sugar_level}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, sugar_level: Number(e.target.value) })}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500">
                    Latest HbA1c (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={newPatientForm.hba1c}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, hba1c: Number(e.target.value) })}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-black"
                  />
                </div>
              </div>
            )}

            {/* Mode 3: Quick Camp Screening Banner */}
            {patientMode === 'quick' && (
              <div className="p-4 rounded-2xl bg-sky-50 border border-sky-200 text-gray-800 text-sm">
                <span className="font-bold text-black flex items-center gap-1.5 mb-1">
                  <Zap className="w-4 h-4 text-amber-500 fill-amber-500" />
                  <span>Quick Camp Outreach Mode</span>
                </span>
                Quickly process community scans with automated temporary identification. Patient records can be detailed and linked post-diagnosis.
              </div>
            )}

            {/* Active Patient High-Visibility Banner */}
            {activePatient && (
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-emerald-100 text-emerald-800">
                    <UserCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-sm font-bold text-black">
                      Selected: {activePatient.name}
                    </span>
                    <span className="text-xs text-gray-600 ml-2 font-medium">
                      ({activePatient.id} • Age {activePatient.age} • HbA1c {activePatient.hba1c}%)
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setActivePatient(null)}
                  className="text-xs text-[#1E54B7] hover:underline font-bold cursor-pointer"
                >
                  Change Patient
                </button>
              </div>
            )}
          </div>

          {/* STEP 2: Fundus Image Upload & Presets */}
          <div className="p-7 sm:p-8 bg-white text-black rounded-[36px] shadow-2xl border-4 border-white space-y-6">
            <h2 className="text-xl sm:text-2xl font-bold text-black flex items-center gap-3 font-sans">
              <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[#1E54B7] text-white text-sm font-black">
                2
              </span>
              Step 2: Retinal Fundus Image
            </h2>

            {/* Presets Grid for Instant Testing */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-wider text-gray-500">
                  Select Clinical Case Preset or Upload Custom Scan:
                </span>
                <span className="text-xs text-[#1E54B7] font-bold">
                  (5 Benchmark Stages Ready)
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
                {PRESET_FUNDUS_CASES.map((preset) => {
                  const isSelected = selectedPreset?.id === preset.id;
                  const meta = DR_STAGES[preset.stage];
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => handleSelectPreset(preset)}
                      className={`p-3.5 rounded-2xl border-2 text-left transition-all relative overflow-hidden cursor-pointer ${
                        isSelected
                          ? 'bg-sky-50/80 border-[#1E54B7] shadow-lg ring-2 ring-sky-100 scale-[1.02]'
                          : 'bg-gray-50 border-gray-200 hover:border-gray-300 hover:bg-white'
                      }`}
                    >
                      <div className="aspect-square w-full rounded-xl overflow-hidden bg-black mb-2.5 border-2 border-white shadow-sm">
                        <img
                          src={preset.originalImage}
                          alt={preset.clinicalNote}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="text-xs font-bold text-black truncate">
                        {preset.patientName}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span
                          className="w-3.5 h-3.5 rounded-full text-[9px] font-black text-white flex items-center justify-center shrink-0"
                          style={{ backgroundColor: meta.color }}
                        >
                          {meta.icon}
                        </span>
                        <span className="text-[11px] font-bold text-gray-700 truncate">
                          {meta.shortName}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Drag & Drop Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="relative p-8 border-2 border-dashed border-gray-300 hover:border-[#1E54B7] rounded-3xl bg-gray-50 text-center cursor-pointer transition-all hover:bg-sky-50/50 group min-h-[190px] flex flex-col items-center justify-center space-y-3"
              role="button"
              tabIndex={0}
              aria-label="Upload retinal fundus image"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/tiff"
                onChange={handleFileChange}
                className="hidden"
              />

              <div className="p-4 rounded-2xl bg-white border border-gray-200 text-[#1E54B7] shadow-sm group-hover:scale-110 transition-transform">
                <Upload className="w-7 h-7" />
              </div>

              <div>
                <p className="text-base sm:text-lg font-bold text-black">
                  Drop retinal fundus image here, or click to browse
                </p>
                <p className="text-xs text-gray-500 mt-1 font-medium">
                  Supports PNG, JPG, JPEG, TIFF (DICOM compliant up to 20MB)
                </p>
              </div>

              {selectedFile && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-sky-100 text-[#1E54B7] text-xs font-mono font-bold">
                  <span>Selected file: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                </div>
              )}
            </div>

            {/* Eye Laterality Selection & Acquisition Context */}
            <div className="p-4 bg-gray-50 rounded-2xl border border-gray-200 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-xs font-black uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                  <Eye className="w-4 h-4 text-[#1E54B7]" />
                  Eye (Laterality) Selected for Analysis:
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  Operator Verified • Landmark Gate: Enforced
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedEye('OD')}
                  className={`py-3 px-4 rounded-xl font-black text-xs sm:text-sm flex items-center justify-center gap-2 border-2 transition-all cursor-pointer ${
                    selectedEye === 'OD'
                      ? 'bg-[#1E54B7] text-white border-[#1E54B7] shadow-md scale-[1.01]'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span>Right Eye (OD - Oculus Dexter)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedEye('OS')}
                  className={`py-3 px-4 rounded-xl font-black text-xs sm:text-sm flex items-center justify-center gap-2 border-2 transition-all cursor-pointer ${
                    selectedEye === 'OS'
                      ? 'bg-[#1E54B7] text-white border-[#1E54B7] shadow-md scale-[1.01]'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span>Left Eye (OS - Oculus Sinister)</span>
                </button>
              </div>
              <p className="text-[11px] text-gray-500">
                Landmark localization evaluates nasal optic nerve vs temporal fovea geometry to cross-check this operator tag.
              </p>
            </div>

            {/* Hackathon Demo & Safety Simulation Suite */}
            <div className="p-5 bg-gradient-to-br from-indigo-50/70 to-sky-50/70 rounded-3xl border-2 border-indigo-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-indigo-600 text-white">
                    <FlaskConical className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-indigo-950">
                      Evaluator & Red-Team Suite (10 Scenarios)
                    </h3>
                    <p className="text-[11px] text-indigo-700">
                      Isolated synthetic sandbox (<code>DEMO-SIM-</code>) — test safety boundaries with 1 click
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setDemoSuiteOpen((prev) => !prev)}
                  className="p-1.5 rounded-lg hover:bg-indigo-100 text-indigo-800 transition-all cursor-pointer"
                  aria-label="Toggle Demo Suite"
                >
                  {demoSuiteOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>

              {demoSuiteOpen && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 pt-2">
                  {DEMO_SCENARIOS.map((sc) => (
                    <button
                      key={sc.id}
                      type="button"
                      onClick={() => handleRunDemoScenario(sc.id)}
                      className={`p-2.5 rounded-xl border text-left transition-all hover:scale-[1.02] cursor-pointer shadow-sm ${
                        sc.category === 'Standard'
                          ? 'bg-white border-sky-200 hover:border-[#1E54B7]'
                          : sc.category === 'Gate'
                          ? 'bg-rose-50/80 border-rose-200 hover:border-rose-400'
                          : 'bg-amber-50/80 border-amber-200 hover:border-amber-400'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded ${
                          sc.category === 'Standard'
                            ? 'bg-sky-100 text-[#1E54B7]'
                            : sc.category === 'Gate'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {sc.stage}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-gray-900 truncate">
                        {sc.label}
                      </div>
                      <div className="text-[10px] text-gray-500 truncate">
                        {sc.desc}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Run Analysis Big CTA Button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleStartAnalysis}
                className="w-full flex items-center justify-center gap-3 px-8 py-5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-base sm:text-lg uppercase tracking-wider shadow-2xl hover:scale-[1.01] transition-all min-h-[58px] cursor-pointer"
              >
                <Microscope className="w-6 h-6" />
                <span>Run Full AI Diagnostic Analysis ↗</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SECTION: STEP 3 - ACCESSIBLE LOADING STATE
      ────────────────────────────────────────────────────────────── */}
      {isAnalyzing && (
        <div className="p-8 sm:p-12 bg-white text-black border-4 border-white rounded-[36px] shadow-2xl text-center max-w-2xl mx-auto space-y-8 animate-fadeIn">
          <div className="relative flex items-center justify-center">
            <div className="w-20 h-20 rounded-full border-4 border-gray-100 border-t-[#1E54B7] animate-spin" />
            <Microscope className="absolute w-8 h-8 text-[#1E54B7]" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-black font-sans">
              Analyzing Retinal Microvasculature...
            </h2>
            <p className="text-sm text-gray-600 font-medium">
              Running multi-modal ophthalmology pipeline with Grad-CAM explainability
            </p>
          </div>

          {/* Sequential Step Checklist */}
          <div className="space-y-3 text-left max-w-md mx-auto p-5 bg-gray-50 rounded-2xl border border-gray-200 font-medium text-xs sm:text-sm">
            <div className="flex items-center gap-3">
              {loadingStep >= 1 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-dashed border-gray-300 shrink-0" />
              )}
              <span className={loadingStep >= 1 ? 'text-black font-bold' : 'text-gray-400'}>
                Image normalization & CLAHE contrast enhancement
              </span>
            </div>

            <div className="flex items-center gap-3">
              {loadingStep >= 2 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-dashed border-gray-300 shrink-0" />
              )}
              <span className={loadingStep >= 2 ? 'text-black font-bold' : 'text-gray-400'}>
                EfficientNet-B3 Diabetic Retinopathy stage classification
              </span>
            </div>

            <div className="flex items-center gap-3">
              {loadingStep >= 3 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-dashed border-gray-300 shrink-0" />
              )}
              <span className={loadingStep >= 3 ? 'text-black font-bold' : 'text-gray-400'}>
                Retinal blood vessel segmentation & density calculation
              </span>
            </div>

            <div className="flex items-center gap-3">
              {loadingStep >= 4 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-dashed border-gray-300 shrink-0" />
              )}
              <span className={loadingStep >= 4 ? 'text-black font-bold' : 'text-gray-400'}>
                Grad-CAM attention heatmap generation & lesion localization
              </span>
            </div>

            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 text-[#1E54B7] animate-spin shrink-0" />
              <span className="text-[#1E54B7] font-black">
                Gemma-4 formulating empathetic clinical report...
              </span>
            </div>
          </div>

          {/* High-Contrast Progress Bar */}
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#1E54B7] transition-all duration-300 rounded-full"
              style={{ width: `${(loadingStep / 5) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SECTION: STEP 4 - DIAGNOSTIC RESULTS (THE COMPREHENSIVE CLINICAL SUITE)
      ────────────────────────────────────────────────────────────── */}
      {activeScan && !isAnalyzing && (
        <div className="space-y-6 sm:space-y-8 animate-fadeIn text-white">
          {/* 1. TOP HERO DIAGNOSTIC SUMMARY BANNER */}
          <div
            className="p-7 sm:p-8 rounded-[36px] border-4 border-white shadow-2xl relative overflow-hidden space-y-6 bg-white text-black"
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              {/* Left: Large Circular Severity Badge */}
              <div className="flex items-center gap-5">
                <div
                  className="flex flex-col items-center justify-center w-20 h-20 sm:w-24 sm:h-24 rounded-3xl shadow-xl text-white font-black shrink-0 border-4 border-white"
                  style={{ backgroundColor: DR_STAGES[activeScan.detection.stage].color }}
                >
                  <span className="text-2xl sm:text-3xl">
                    {DR_STAGES[activeScan.detection.stage].icon}
                  </span>
                  <span className="text-xs sm:text-sm uppercase tracking-wider font-mono">
                    Stage {activeScan.detection.stage}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-2xl sm:text-4xl font-black text-black font-sans">
                      {DR_STAGES[activeScan.detection.stage].name}
                    </h1>
                    <span
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black border ${
                        activeScan.report.urgency === 'IMMEDIATE' || activeScan.report.urgency === 'URGENT'
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : 'bg-amber-100 text-amber-900 border-amber-200'
                      }`}
                    >
                      {activeScan.report.urgency === 'IMMEDIATE' ? (
                        <>
                          <AlertOctagon className="w-3.5 h-3.5 text-rose-700" />
                          <span>EMERGENCY</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                          <span>{activeScan.report.urgency}</span>
                        </>
                      )}
                    </span>
                  </div>

                  <p className="text-sm sm:text-base text-gray-600 font-medium">
                    Patient: <strong className="text-black font-bold">{activePatient?.name || activeScan.patient_name}</strong> (
                    {activePatient?.id || activeScan.patient_id}) • Screened on {activeScan.scan_date}
                  </p>

                  <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-gray-500 font-mono font-medium">
                    <span>Confidence: <strong className="text-[#1E54B7]">{activeScan.detection.confidence.toFixed(1)}%</strong></span>
                    <span>•</span>
                    <span>Processing: {activeScan.processing_time}s</span>
                    <span>•</span>
                    <span>HbA1c: {activePatient?.hba1c || 7.8}%</span>
                  </div>
                </div>
              </div>

              {/* Right: Quick Action Speech & Reset */}
              <div className="flex flex-wrap items-center gap-3 shrink-0">
                <button
                  type="button"
                  onClick={handleListenDiagnosis}
                  className={`flex items-center gap-2 px-6 py-3.5 rounded-full font-black text-xs uppercase tracking-wider transition-all shadow-md min-h-[46px] cursor-pointer ${
                    isSpeaking
                      ? 'bg-rose-100 text-rose-800 border-2 border-rose-400 animate-pulse'
                      : 'bg-[#E1FA4A] hover:bg-[#d6f236] text-black shadow-lg hover:scale-105'
                  }`}
                  aria-label="Listen to diagnosis report read aloud"
                >
                  {isSpeaking ? <VolumeX className="w-4 h-4 text-rose-600" /> : <Volume2 className="w-4 h-4 text-black" />}
                  <span>{isSpeaking ? 'Stop Audio' : 'Listen to Report'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownloadPDF}
                  className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-gray-100 hover:bg-gray-200 text-black font-black text-xs uppercase tracking-wider transition-all min-h-[46px] cursor-pointer"
                >
                  <FileDown className="w-4 h-4 text-[#1E54B7]" />
                  <span>Large-Print PDF</span>
                </button>

                <button
                  type="button"
                  onClick={() => setRagDrawerOpen(true)}
                  className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-sky-50 hover:bg-sky-100 text-[#1E54B7] border border-sky-200 font-black text-xs uppercase tracking-wider transition-all min-h-[46px] cursor-pointer shadow-sm"
                >
                  <BookOpen className="w-4 h-4 text-[#1E54B7]" />
                  <span>Clinical Guidelines (RAG)</span>
                </button>
              </div>
            </div>
          </div>

          {/* 1.5. SAFETY ARBITRATION & DECISION GATE BANNER */}
          <div className="p-6 sm:p-7 bg-white text-black border-4 border-white rounded-[32px] shadow-2xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-6 h-6 text-[#1E54B7]" />
                <div>
                  <h3 className="text-lg sm:text-xl font-black text-black font-sans">
                    Clinical Safety Gate & Decision Arbitration
                  </h3>
                  <p className="text-xs text-gray-500">
                    Pre-inference verification, anatomical landmarks & multi-gate policy check
                  </p>
                </div>
              </div>
              <span className="text-xs font-mono font-bold px-3 py-1 bg-gray-100 text-gray-700 rounded-full border border-gray-200">
                Policy Version: SAFE-1.0
              </span>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {/* Safety State */}
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">
                  Safety State
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black ${
                  (activeScan.safety_state || 'PASS') === 'PASS'
                    ? 'bg-emerald-100 text-emerald-800'
                    : (activeScan.safety_state || 'PASS') === 'REJECT'
                    ? 'bg-rose-100 text-rose-800'
                    : 'bg-amber-100 text-amber-800'
                }`}>
                  {(activeScan.safety_state || 'PASS') === 'PASS' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  )}
                  {activeScan.safety_state || 'PASS'}
                </span>
              </div>

              {/* Automation Level */}
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">
                  Automation Level
                </span>
                <span className="text-xs font-black text-gray-800">
                  {activeScan.automation_level || 'DECISION_SUPPORT'}
                </span>
              </div>

              {/* Laterality & Landmarks */}
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">
                  Eye (Laterality)
                </span>
                <span className="text-xs font-black text-[#1E54B7]">
                  {activeScan.eye === 'OS' ? 'Left Eye (OS)' : 'Right Eye (OD)'}
                </span>
              </div>

              {/* Longitudinal History */}
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">
                  Longitudinal Data
                </span>
                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-black ${
                  activeScan.longitudinal_state === 'LONGITUDINAL_SUPPORTED'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-sky-100 text-sky-900'
                }`}>
                  {activeScan.longitudinal_state === 'LONGITUDINAL_SUPPORTED'
                    ? 'Cohort History'
                    : 'Single Visit Baseline'}
                </span>
              </div>
            </div>

            {/* Active Reason Codes */}
            {activeScan.reason_codes && activeScan.reason_codes.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">
                  Active Reason Codes:
                </span>
                <div className="flex flex-wrap gap-2">
                  {activeScan.reason_codes.map((rc, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg bg-gray-100 border border-gray-200 text-xs font-mono font-bold text-gray-700"
                    >
                      {rc}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Honest Longitudinal Advisory Banner */}
            {(activeScan.longitudinal_state === 'LIMITED_LONGITUDINAL_HISTORY' ||
              activeScan.longitudinal_state === 'LONGITUDINAL_UNAVAILABLE') && (
              <div className="p-3.5 rounded-2xl bg-sky-50 border border-sky-200 flex items-start gap-2.5 text-xs text-sky-900">
                <Info className="w-4 h-4 text-[#1E54B7] shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-bold mb-0.5">Clinical Honesty Notice (No Fabricated Progression):</strong>
                  Progression risk estimates below are statistical cohort models based on diabetes duration and HbA1c. DrishtiAI does not synthesize temporal progression without verified multi-visit historical scans.
                </div>
              </div>
            )}

            {/* Warning if Review is Required */}
            {(activeScan.safety_state === 'REVIEW_REQUIRED' || activeScan.safety_state === 'REJECT') && (
              <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-300 flex items-start gap-2.5 text-xs text-amber-950">
                <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-bold mb-0.5">Clinical Review Mandatory:</strong>
                  The safety gate flagged an edge case or uncertainty. Ophthalmologist review is required before clinical referral or discharge.
                </div>
              </div>
            )}
          </div>

          {/* 2. IMAGE TRIPTYCH (INTERACTIVE RETINAL VIEWER) */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 font-sans">
                <Eye className="w-6 h-6 text-white" />
                Retinal Multimodal Explainability Triptych
              </h2>
              <button
                type="button"
                onClick={() => setLightboxOpen(true)}
                className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-white hover:underline bg-white/20 px-3.5 py-1.5 rounded-full cursor-pointer"
              >
                <Maximize2 className="w-3.5 h-3.5" />
                <span>Open Fullscreen Lightbox</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1: Original Retinal Fundus Scan */}
              <div className="p-5 bg-white text-black border-4 border-white rounded-[32px] shadow-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-black flex items-center gap-2 font-sans">
                    <Eye className="w-4 h-4 text-[#1E54B7]" />
                    1. Original Retinal Scan
                  </span>
                  <button
                    type="button"
                    onClick={() => setInvertOriginal((v) => !v)}
                    className={`text-xs px-2.5 py-1 rounded-full border font-bold cursor-pointer ${
                      invertOriginal
                        ? 'bg-amber-100 text-amber-900 border-amber-300'
                        : 'bg-gray-100 text-gray-600 border-gray-200'
                    }`}
                  >
                    {invertOriginal ? 'Inverted' : 'Invert'}
                  </button>
                </div>

                <div
                  className="aspect-square w-full rounded-2xl overflow-hidden bg-black border-2 border-white shadow-md cursor-pointer relative group"
                  onClick={() => setLightboxOpen(true)}
                >
                  <img
                    src={activeScan.images.original}
                    alt="Original Fundus Scan"
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    style={{ filter: invertOriginal ? 'invert(1) hue-rotate(180deg)' : 'none' }}
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-bold gap-1">
                    <Maximize2 className="w-4 h-4" /> Click to Zoom
                  </div>
                </div>

                <p className="text-xs text-gray-600 font-medium leading-relaxed">
                  High-definition fundus view depicting optic nerve head and macular vascular topography.
                </p>
              </div>

              {/* Card 2: Vessel Segmentation Map */}
              <div className="p-5 bg-white text-black border-4 border-white rounded-[32px] shadow-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-black flex items-center gap-2 font-sans">
                    <Layers className="w-4 h-4 text-sky-600" />
                    2. Vessel Segmentation Map
                  </span>
                  <span className="text-xs font-mono font-bold text-[#1E54B7] bg-sky-100 px-2.5 py-0.5 rounded-full">
                    {activeScan.vessel_stats.vessel_density_percent}% Density
                  </span>
                </div>

                <div
                  className="aspect-square w-full rounded-2xl overflow-hidden bg-black border-2 border-white shadow-md cursor-pointer relative group"
                  onClick={() => setLightboxOpen(true)}
                >
                  <img
                    src={activeScan.images.vessels}
                    alt="Vessel Segmentation Map"
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    style={{ filter: invertVessels ? 'invert(1) hue-rotate(180deg)' : 'none' }}
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-bold gap-1">
                    <Maximize2 className="w-4 h-4" /> Click to Zoom
                  </div>
                </div>

                <p className="text-xs text-gray-600 font-medium leading-relaxed">
                  {activeScan.vessel_stats.vessel_health_text}
                </p>
              </div>

              {/* Card 3: AI Grad-CAM Heatmap */}
              <div className="p-5 bg-white text-black border-4 border-white rounded-[32px] shadow-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-black flex items-center gap-2 font-sans">
                    <Flame className="w-4 h-4 text-rose-600" />
                    3. AI Grad-CAM Heatmap
                  </span>
                  <span className="text-xs font-mono font-bold text-rose-700 bg-rose-100 px-2.5 py-0.5 rounded-full">
                    {activeScan.heatmap_analysis.activity_intensity}
                  </span>
                </div>

                <div
                  className="aspect-square w-full rounded-2xl overflow-hidden bg-black border-2 border-white shadow-md cursor-pointer relative group"
                  onClick={() => setLightboxOpen(true)}
                >
                  <img
                    src={activeScan.images.heatmap}
                    alt="AI Grad-CAM Heatmap"
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    style={{ filter: invertHeatmap ? 'invert(1) hue-rotate(180deg)' : 'none' }}
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-bold gap-1">
                    <Maximize2 className="w-4 h-4" /> Click to Zoom
                  </div>
                </div>

                <p className="text-xs text-gray-600 font-medium leading-relaxed">
                  Deep activation highlights microvascular damage focused on {activeScan.heatmap_analysis.most_affected_region}.
                </p>
              </div>
            </div>
          </div>

          {/* 3. PROBABILITY DISTRIBUTION BARS */}
          <div className="p-7 sm:p-8 bg-white text-black border-4 border-white rounded-[36px] shadow-2xl space-y-4">
            <h3 className="text-xs font-black uppercase tracking-wider text-gray-500">
              Five-Class Severity Probability Breakdown
            </h3>

            <div className="space-y-3">
              {([0, 1, 2, 3, 4] as DRStage[]).map((stageNum) => {
                const meta = DR_STAGES[stageNum];
                const prob = activeScan.detection.all_probabilities[stageNum] || 0;
                const isPredicted = activeScan.detection.stage === stageNum;

                return (
                  <div
                    key={stageNum}
                    className={`p-3.5 rounded-2xl border transition-all ${
                      isPredicted
                        ? 'bg-sky-50 border-[#1E54B7] shadow-sm ring-1 ring-sky-100'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs sm:text-sm font-semibold mb-1.5">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-4 h-4 rounded-full text-[10px] font-black text-white flex items-center justify-center shrink-0"
                          style={{ backgroundColor: meta.color }}
                        >
                          {meta.icon}
                        </span>
                        <span className={isPredicted ? 'text-black font-bold' : 'text-gray-700'}>
                          {meta.name}
                        </span>
                        {isPredicted && (
                          <span className="text-[10px] uppercase font-black text-[#1E54B7] bg-sky-100 px-2 py-0.5 rounded-full">
                            Predicted
                          </span>
                        )}
                      </div>
                      <span className="font-mono font-bold text-black">{prob.toFixed(1)}%</span>
                    </div>

                    <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.max(prob, 2)}%`,
                          backgroundColor: meta.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 4. GEMMA-4 CLINICAL DIAGNOSTIC REPORT CARD */}
          {translatedReport && (
            <div className="p-7 sm:p-8 bg-white text-black border-4 border-white rounded-[36px] shadow-2xl space-y-6">
              {/* Report Header with Language Switcher & PDF */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-purple-100 text-purple-700">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-black font-sans">
                      Gemma-4 Clinical Diagnostic Intelligence Report
                    </h3>
                    <p className="text-xs text-gray-500">
                      Empathetic, structured evaluation generated by Google Gemma-4 (31B-IT)
                    </p>
                  </div>
                </div>

                {/* Multilingual Selector [ English ] [ हिंदी ] [ ગુજરાતી ] */}
                <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-full border border-gray-200 self-start sm:self-auto">
                  <span className="px-2 text-xs text-gray-500 font-bold hidden md:inline flex items-center gap-1">
                    <Languages className="w-3.5 h-3.5" /> Language:
                  </span>
                  <button
                    onClick={() => setReportLanguage('english')}
                    className={`px-3.5 py-1.5 text-xs font-black rounded-full transition-all cursor-pointer ${
                      reportLanguage === 'english'
                        ? 'bg-black text-white shadow-sm'
                        : 'text-gray-700 hover:text-black hover:bg-gray-200'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => setReportLanguage('hindi')}
                    className={`px-3.5 py-1.5 text-xs font-black rounded-full transition-all cursor-pointer ${
                      reportLanguage === 'hindi'
                        ? 'bg-black text-white shadow-sm'
                        : 'text-gray-700 hover:text-black hover:bg-gray-200'
                    }`}
                  >
                    हिंदी (Hindi)
                  </button>
                  <button
                    onClick={() => setReportLanguage('gujarati')}
                    className={`px-3.5 py-1.5 text-xs font-black rounded-full transition-all cursor-pointer ${
                      reportLanguage === 'gujarati'
                        ? 'bg-black text-white shadow-sm'
                        : 'text-gray-700 hover:text-black hover:bg-gray-200'
                    }`}
                  >
                    ગુજરાતી (Gujarati)
                  </button>
                </div>
              </div>

              {/* a) Current Ocular Status */}
              <div className="space-y-2 p-5 bg-sky-50/70 rounded-3xl border border-sky-100">
                <h4 className="text-base font-bold text-[#1E54B7] flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  1. Current Ocular Status (Plain Language Explanation)
                </h4>
                <p className="text-sm sm:text-base text-gray-800 leading-relaxed font-medium">
                  {translatedReport.plainLanguage}
                </p>
              </div>

              {/* b) Visual Biomarkers */}
              <div className="space-y-3 p-5 bg-gray-50 rounded-3xl border border-gray-200">
                <h4 className="text-base font-bold text-black flex items-center gap-2">
                  <Eye className="w-5 h-5 text-[#1E54B7]" />
                  2. Retinal Biomarkers & Microvascular Density
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs sm:text-sm text-gray-700">
                  <div className="p-4 rounded-2xl bg-white border border-gray-200 space-y-1 shadow-sm">
                    <span className="font-bold text-[#1E54B7] block text-xs uppercase">Grad-CAM Lesion Localization:</span>
                    <p>{translatedReport.visualFindingsHeatmap}</p>
                  </div>
                  <div className="p-4 rounded-2xl bg-white border border-gray-200 space-y-1 shadow-sm">
                    <span className="font-bold text-[#1E54B7] block text-xs uppercase">Capillary Network Perfusion:</span>
                    <p>{translatedReport.visualFindingsVessels}</p>
                  </div>
                </div>
              </div>

              {/* c) Time-Aware Risk Progression */}
              <div className="space-y-3 p-5 bg-amber-50/60 rounded-3xl border border-amber-200">
                <h4 className="text-base font-bold text-amber-950 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-amber-700" />
                  3. Time-Aware Progression Risk Forecast
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 6 Month Card */}
                  <div className="p-4 rounded-2xl bg-white border border-amber-200 space-y-2 shadow-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-amber-900">6-Month Forecast</span>
                      <span className="text-xs font-mono font-black px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900">
                        Risk: {activeScan.report.risk_prediction['6_month'].progression_risk_percent}
                      </span>
                    </div>
                    <div className="text-xs space-y-1.5">
                      <p className="text-rose-700 font-medium">
                        <strong>If Untreated:</strong> {translatedReport.riskUntreated6Mo}
                      </p>
                      <p className="text-emerald-800 font-medium">
                        <strong>If Managed:</strong> {translatedReport.riskManaged6Mo}
                      </p>
                    </div>
                  </div>

                  {/* 12 Month Card */}
                  <div className="p-4 rounded-2xl bg-white border border-amber-200 space-y-2 shadow-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-amber-900">12-Month Forecast</span>
                      <span className="text-xs font-mono font-black px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900">
                        Risk: {activeScan.report.risk_prediction['12_month'].progression_risk_percent}
                      </span>
                    </div>
                    <div className="text-xs space-y-1.5">
                      <p className="text-rose-700 font-medium">
                        <strong>If Untreated:</strong> {translatedReport.riskUntreated12Mo}
                      </p>
                      <p className="text-emerald-800 font-medium">
                        <strong>If Managed:</strong> {translatedReport.riskManaged12Mo}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* d) Clinical Action Plan */}
              <div className="space-y-3 p-5 bg-gray-50 rounded-3xl border border-gray-200">
                <h4 className="text-base font-bold text-black flex items-center gap-2">
                  <CheckSquare className="w-5 h-5 text-emerald-600" />
                  4. Clinical Action Plan Checklist
                </h4>
                <div className="space-y-2">
                  {translatedReport.actionPlan.map((act, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3.5 rounded-2xl bg-white border border-gray-200 text-xs sm:text-sm text-gray-800 shadow-sm"
                    >
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-black shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span>{act}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* e) Diabetic Eye-Care Dietary Guidance */}
              <div className="space-y-3 p-5 bg-teal-50/50 rounded-3xl border border-teal-200">
                <h4 className="text-base font-bold text-teal-950 flex items-center gap-2">
                  <Utensils className="w-5 h-5 text-teal-700" />
                  5. Retinal Nutrition & Dietary Recommendations
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {translatedReport.dietRecommendations.map((diet, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl bg-white border border-teal-100 text-xs sm:text-sm text-gray-700 leading-relaxed flex items-start gap-2 shadow-sm"
                    >
                      <span className="text-teal-600 font-bold">•</span>
                      <span>{diet}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* f) Recommended Follow-Up & g) Disclaimer */}
              <div className="p-4 rounded-2xl bg-sky-50 border border-sky-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm">
                <div className="flex items-center gap-2 font-bold text-[#1E54B7]">
                  <Calendar className="w-5 h-5 text-[#1E54B7]" />
                  <span>Recommended Next Follow-Up Screening: {translatedReport.followUp}</span>
                </div>
                <div className="text-xs text-gray-500 font-medium">
                  Clinical Decision Support • Validated by Gemma-4
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-gray-50 border border-gray-200 flex items-start gap-2 text-xs text-gray-500">
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{translatedReport.disclaimer}</span>
              </div>
            </div>
          )}

          {/* 4.5 CLINICIAN SIGN-OFF & OVERSIGHT (DOCTOR REVIEW WORKFLOW) */}
          <DoctorReviewSection
            scanId={activeScan.analysis_id}
            patientId={activePatient?.id || activeScan.patient_id}
            originalStage={activeScan.detection.stage}
          />

          {/* 5. ACTION FOOTER */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-7 bg-white text-black border-4 border-white rounded-[36px] shadow-2xl">
            <button
              type="button"
              onClick={handleResetScan}
              className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-gray-100 hover:bg-gray-200 text-black font-black text-xs uppercase tracking-wider transition-all min-h-[46px] cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Scan Another Patient</span>
            </button>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  if (activePatient) setActiveView('patient-detail');
                }}
                className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-sky-50 hover:bg-sky-100 text-[#1E54B7] font-black text-xs uppercase tracking-wider border border-sky-200 transition-all min-h-[46px] cursor-pointer"
              >
                <span>View Longitudinal Profile →</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 px-7 py-3.5 rounded-full bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-black text-xs uppercase tracking-wider shadow-lg hover:scale-105 transition-all min-h-[46px] cursor-pointer"
              >
                <FileDown className="w-4 h-4" />
                <span>Save &amp; Print Clinical Report</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Lightbox Modal */}
      {activeScan && (
        <ImageLightboxModal
          isOpen={lightboxOpen}
          onClose={() => setLightboxOpen(false)}
          originalUrl={activeScan.images.original}
          vesselUrl={activeScan.images.vessels}
          heatmapUrl={activeScan.images.heatmap}
          title="Multimodal Retinal Fundus Inspection"
          patientName={activePatient?.name || activeScan.patient_name}
          stageName={activeScan.detection.stage_name}
        />
      )}

      {/* Clinical Guidelines Intelligence Drawer (Medical RAG) */}
      <MedicalRAGDrawer
        isOpen={ragDrawerOpen}
        onClose={() => setRagDrawerOpen(false)}
        initialStage={activeScan?.detection.stage}
        initialHbA1c={activePatient?.hba1c}
      />
    </div>
  );
};
