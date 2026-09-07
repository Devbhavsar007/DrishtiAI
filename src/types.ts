export type DRStage = 0 | 1 | 2 | 3 | 4;

export interface DRStageMeta {
  stage: DRStage;
  name: string;
  shortName: string;
  icon: string;
  shape: 'circle' | 'rounded-pill' | 'rounded-square' | 'hexagon' | 'diamond';
  color: string;
  textColor: string;
  bgLight: string;
  borderColor: string;
  description: string;
  severity: 'none' | 'mild' | 'moderate' | 'severe' | 'proliferative';
}

export const DR_STAGES: Record<DRStage, DRStageMeta> = {
  0: {
    stage: 0,
    name: 'Stage 0: No DR',
    shortName: 'No DR',
    icon: '✓',
    shape: 'circle',
    color: '#0D9488', // Teal / Cyan
    textColor: '#2DD4BF',
    bgLight: 'rgba(13, 148, 136, 0.15)',
    borderColor: '#0D9488',
    description: 'No retinal microvascular lesions or diabetic changes detected.',
    severity: 'none',
  },
  1: {
    stage: 1,
    name: 'Stage 1: Mild NPDR',
    shortName: 'Mild NPDR',
    icon: '◐',
    shape: 'rounded-pill',
    color: '#D97706', // Amber Gold
    textColor: '#FBBF24',
    bgLight: 'rgba(217, 119, 6, 0.15)',
    borderColor: '#D97706',
    description: 'Microaneurysms only. Early warning state.',
    severity: 'mild',
  },
  2: {
    stage: 2,
    name: 'Stage 2: Moderate NPDR',
    shortName: 'Moderate NPDR',
    icon: '▲',
    shape: 'rounded-square',
    color: '#EA580C', // Coral Orange
    textColor: '#FB923C',
    bgLight: 'rgba(234, 88, 12, 0.15)',
    borderColor: '#EA580C',
    description: 'More than microaneurysms, but less than severe NPDR (cotton wool spots, hemorrhages).',
    severity: 'moderate',
  },
  3: {
    stage: 3,
    name: 'Stage 3: Severe NPDR',
    shortName: 'Severe NPDR',
    icon: '⬢',
    shape: 'hexagon',
    color: '#DC2626', // Crimson Red
    textColor: '#F87171',
    bgLight: 'rgba(220, 38, 38, 0.15)',
    borderColor: '#DC2626',
    description: 'High risk: extensive intraretinal hemorrhages, venous beading, or IRMA.',
    severity: 'severe',
  },
  4: {
    stage: 4,
    name: 'Stage 4: Proliferative DR',
    shortName: 'Proliferative DR',
    icon: '!',
    shape: 'diamond',
    color: '#9333EA', // Vivid Purple
    textColor: '#C084FC',
    bgLight: 'rgba(147, 51, 234, 0.15)',
    borderColor: '#9333EA',
    description: 'Critical ocular emergency: neovascularization, vitreous hemorrhage, high risk of vision loss.',
    severity: 'proliferative',
  },
};

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Male' | 'Female' | 'Other';
  diabetes_duration: number; // in years
  sugar_level: number; // mg/dL
  hba1c: number; // %
  notes?: string;
  created_at: string;
  phone?: string;
  location?: string;
  scans?: ScanAnalysis[];
}

export interface GemmaReport {
  current_diagnosis: {
    stage: DRStage;
    stage_name: string;
    confidence: string;
    plain_language: string;
  };
  visual_findings: {
    heatmap_summary: string;
    vessel_analysis: string;
  };
  risk_prediction: {
    '6_month': {
      progression_risk_percent: string;
      scenario_if_untreated: string;
      scenario_if_managed: string;
    };
    '12_month': {
      progression_risk_percent: string;
      scenario_if_untreated: string;
      scenario_if_managed: string;
    };
  };
  action_plan: string[];
  diet_recommendations: string[];
  urgency: 'ROUTINE' | 'SOON' | 'URGENT' | 'IMMEDIATE';
  recommended_follow_up: string;
  disclaimer: string;
}

export interface ScanAnalysis {
  analysis_id: string;
  patient_id: string;
  patient_name?: string;
  scan_date: string;
  processing_time: number;
  detection: {
    stage: DRStage;
    stage_name: string;
    confidence: number;
    all_probabilities: Record<DRStage, number>;
    severity: string;
    color: string;
    _model: string;
  };
  heatmap_analysis: {
    most_affected_region: string;
    activity_intensity: string;
    region_scores: {
      macula: number;
      optic_disc: number;
      superior_temporal: number;
      inferior_temporal: number;
      nasal: number;
    };
  };
  vessel_stats: {
    vessel_density_percent: number;
    vessel_health_text: string;
    quadrant_density: {
      superior_nasal: number;
      superior_temporal: number;
      inferior_nasal: number;
      inferior_temporal: number;
    };
  };
  report: GemmaReport;
  images: {
    original: string;
    heatmap: string;
    vessels: string;
  };
  eye?: 'OD' | 'OS';
  safety_state?: 'VERIFIED' | 'UNCERTAIN' | 'BLOCKED' | 'REJECTED' | 'ANATOMY_FAILED' | 'QUALITY_FAILED' | 'LATERALITY_CONFLICT' | 'MODEL_FAILURE' | 'OOD_REVIEW';
  automation_level?: 'AUTOMATED_ASSISTANCE' | 'HUMAN_REVIEW_REQUIRED' | 'HUMAN_CONFIRMED' | 'UNABLE_TO_CLASSIFY';
  reason_codes?: string[];
  longitudinal_state?: 'LONGITUDINAL_SUPPORTED' | 'LIMITED_LONGITUDINAL_HISTORY' | 'LONGITUDINAL_UNAVAILABLE';
  progression_availability_message?: string;
}

export interface BatchQueueItem {
  id: string;
  patient_id?: string;
  patient_name: string;
  age: number;
  gender: 'Male' | 'Female' | 'Other';
  diabetes_duration: number;
  sugar_level: number;
  hba1c: number;
  image_url: string;
  file?: File;
  status: 'QUEUED' | 'ANALYZING' | 'COMPLETED' | 'ERROR' | 'REQUIRES_ATTENTION';
  result?: ScanAnalysis;
  error?: string;
  queued_at: string;
}

export interface DashboardStats {
  total_patients: number;
  total_scans: number;
  high_risk_cases: number;
  referrals_needed: number;
  diagnostic_accuracy: number;
  stage_distribution: Record<DRStage, { count: number; percentage: number; name: string }>;
  recent_scans: ScanAnalysis[];
}

export type ReportLanguage = 'english' | 'hindi' | 'gujarati';

export type ActiveView = 'landing' | 'dashboard' | 'new-scan' | 'batch-screening' | 'patients' | 'patient-detail';

export interface ProgressionAssessment {
  engine: string;
  observed_data: {
    current_stage: number;
    previous_stage: number | null;
    stage_delta: number | null;
    current_confidence: number;
  };
  predicted_risk: {
    risk_category: 'LOW' | 'MODERATE' | 'HIGH';
    six_month_risk: number;
    twelve_month_risk: number;
    supporting_factors: string[];
    uncertainty_flags: string[];
  };
  clinical_recommendation: {
    follow_up_priority: 'LOW' | 'MEDIUM' | 'HIGH';
    human_review_recommended: boolean;
    note: string;
  };
}

export interface TriageDecision {
  priority: 'ROUTINE' | 'EARLY' | 'URGENT';
  reasonCodes: string[];
  humanReviewRequired: boolean;
  disclaimer: string;
}

export interface SafetyDecision {
  status: 'PROCEED' | 'UNCERTAIN' | 'RETAKE_REQUIRED';
  overall_quality_score: number;
  model_confidence: number;
  reasons: string[];
  human_review_required: boolean;
  retake_guidance: string | null;
  disclaimer: string;
}

export interface TimelineEvent {
  scan_id: string;
  patient_id: string;
  date: string;
  stage: DRStage;
  stage_name: string;
  confidence: number;
  severity: string;
  stage_delta: number | null;
  progression?: ProgressionAssessment | null;
  referral?: TriageDecision | null;
  doctor_review_status?: string;
  image_thumbnail?: string;
}

export interface PatientTimelineData {
  patient: Patient;
  total_events: number;
  events: TimelineEvent[];
}

export interface DoctorReview {
  id?: string;
  scan_id: string;
  patient_id: string;
  doctor_id: string;
  doctor_name: string;
  decision: 'APPROVED' | 'MODIFIED' | 'REJECTED_RETAKE';
  original_stage: DRStage;
  adjusted_stage?: DRStage | null;
  approved_priority: 'ROUTINE' | 'EARLY' | 'URGENT';
  clinical_notes: string;
  recommended_intervention?: string;
  created_at?: string;
}

export interface ClinicalCitation {
  id: string;
  title: string;
  organization: string;
  year: number;
  section: string;
  citation: string;
  relevance_score: number;
}

export interface GroundedMedicalQueryResponse {
  query: string;
  answer: string;
  citations: ClinicalCitation[];
  confidence: number;
  evidence_found: boolean;
  disclaimer: string;
  metadata?: Record<string, any>;
}
