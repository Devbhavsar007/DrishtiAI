import { Patient, ScanAnalysis, DRStage, DR_STAGES } from '../types';
import { createFundusDataUrl } from './sampleFundusPresets';

export function buildSyntheticScan(
  patientId: string,
  patientName: string,
  stage: DRStage,
  dateStr: string,
  confidence: number = 88.5
): ScanAnalysis {
  const stageMeta = DR_STAGES[stage];

  const probabilities: Record<DRStage, number> = {
    0: stage === 0 ? confidence : Number(((100 - confidence) * 0.1).toFixed(1)),
    1: stage === 1 ? confidence : stage === 0 ? Number(((100 - confidence) * 0.7).toFixed(1)) : Number(((100 - confidence) * 0.15).toFixed(1)),
    2: stage === 2 ? confidence : Number(((100 - confidence) * 0.25).toFixed(1)),
    3: stage === 3 ? confidence : Number(((100 - confidence) * 0.3).toFixed(1)),
    4: stage === 4 ? confidence : Number(((100 - confidence) * 0.1).toFixed(1)),
  };

  const urgency = stage === 4 ? 'IMMEDIATE' : stage === 3 ? 'URGENT' : stage === 2 ? 'SOON' : 'ROUTINE';
  const followUp = stage === 4 ? 'Within 24-48 Hours (Ophthalmology Emergency)' : stage === 3 ? 'Within 1-2 Weeks' : stage === 2 ? '3-4 Months' : stage === 1 ? '6-9 Months' : '12 Months (Annual Screening)';

  const vesselDensity = stage === 0 ? 18.6 : stage === 1 ? 16.4 : stage === 2 ? 14.2 : stage === 3 ? 10.8 : 8.1;

  const plainDescriptions: Record<DRStage, string> = {
    0: 'Your retinal scan shows healthy, clear blood vessels with no signs of diabetes-related eye damage. Continue your healthy blood sugar routine.',
    1: 'Mild non-proliferative retinopathy detected with tiny early micro-swellings in blood vessels. Good glycemic control can reverse or prevent further changes.',
    2: 'Moderate diabetic retinopathy identified with scattered retinal dot hemorrhages and lipid exudate deposits. Closer monitoring and blood pressure/sugar control are needed.',
    3: 'Severe diabetic changes observed including extensive bleeding spots and compromised capillary flow. Prompt specialist laser or injection evaluation is recommended to safeguard sight.',
    4: 'Critical proliferative retinopathy showing fragile new abnormal blood vessels at risk of bleeding or retinal detachment. Immediate ophthalmic intervention required.',
  };

  const actionPlans: Record<DRStage, string[]> = {
    0: [
      'Maintain target fasting blood glucose between 80–120 mg/dL.',
      'Schedule routine annual comprehensive dilated retinal eye examination.',
      'Keep blood pressure within optimal range (<130/80 mmHg).',
      'Report any new floaters, blurry vision, or dark spots immediately.',
    ],
    1: [
      'Strict glycemic control: aim for HbA1c < 7.0% under primary physician guidance.',
      'Schedule a follow-up retinal photography screening in 6 to 9 months.',
      'Monitor and control blood lipids (cholesterol & triglycerides).',
      'Engage in daily 30-minute moderate physical activity.',
    ],
    2: [
      'Consult an ophthalmologist or retina specialist within 3 to 4 months for optical coherence tomography (OCT) macular check.',
      'Intensify diabetes medication regimen to reduce vascular micro-leakage.',
      'Daily self-assessment using an Amsler grid to detect macular distortion.',
      'Avoid heavy weight straining that increases intraocular venous pressure.',
    ],
    3: [
      'Urgent in-person retina specialist referral within 1 to 2 weeks.',
      'Prepare for possible panretinal photocoagulation (laser) or anti-VEGF therapy.',
      'Check kidney function (microalbuminuria) as retinal and renal microvasculature share pathology.',
      'Strictly avoid smoking and maintain tight blood pressure control.',
    ],
    4: [
      'IMMEDIATE ophthalmic referral within 24–48 hours for anti-VEGF injection and PRP laser.',
      'Avoid bending below waist level or intense exertion to prevent vitreous hemorrhage.',
      'Sleep with head slightly elevated on two pillows.',
      'Emergency plan: go to eye casualty if sudden dark curtain or red haze appears.',
    ],
  };

  const diets: Record<DRStage, string[]> = {
    0: [
      'Leafy greens (spinach, kale) rich in lutein and zeaxanthin to protect the macula.',
      'Omega-3 fatty acids (flaxseeds, walnuts, oily fish) to maintain retinal capillary flexibility.',
      'Low-glycemic legumes and whole grains for steady insulin release.',
    ],
    1: [
      'Antioxidant-rich berries (blueberries, amla) to fight vascular oxidative stress.',
      'High-fiber vegetables (fenugreek, bitter gourd, broccoli) to prevent glucose spikes.',
      'Limit high-sodium processed foods to protect delicate retinal arterioles.',
    ],
    2: [
      'Dark green leafy vegetables twice daily for bioflavonoid capillary reinforcement.',
      'Vitamin C & E rich foods (citrus, almonds, bell peppers) to reduce lipid peroxidation.',
      'Zero added sugars, carbonated soft drinks, or deep-fried trans-fats.',
    ],
    3: [
      'Strict low-sodium, heart-healthy diabetic diet to minimize edema risk.',
      'Lycopene and anthocyanin sources (cooked tomatoes, purple cabbage).',
      'Consult a clinical dietitian for tailored carbohydrate counting.',
    ],
    4: [
      'Strict renal-retinal diabetic meal plan with controlled potassium, sodium, and glycemic index.',
      'Adequate hydration without fluid overload.',
      'Eliminate all refined carbohydrates and sweetened beverages immediately.',
    ],
  };

  return {
    analysis_id: `scan-${Date.now()}-${Math.floor(Math.random() * 9000 + 1000)}`,
    patient_id: patientId,
    patient_name: patientName,
    scan_date: dateStr,
    processing_time: 0.42,
    detection: {
      stage,
      stage_name: stageMeta.name,
      confidence,
      all_probabilities: probabilities,
      severity: stageMeta.severity,
      color: stageMeta.color,
      _model: 'EfficientNet-B3 + Gemma-4 Medical Intelligence',
    },
    heatmap_analysis: {
      most_affected_region: stage >= 2 ? 'Macular Arcade & Central Fovea' : stage === 1 ? 'Inferior Temporal Arcade' : 'Uniformly Normal',
      activity_intensity: stage >= 3 ? 'High / Critical' : stage >= 2 ? 'Moderate / Elevated' : stage === 1 ? 'Low / Localized' : 'Minimal',
      region_scores: {
        macula: stage >= 2 ? 0.88 : stage === 1 ? 0.42 : 0.08,
        optic_disc: stage === 4 ? 0.94 : stage >= 2 ? 0.55 : 0.12,
        superior_temporal: stage >= 2 ? 0.76 : stage === 1 ? 0.38 : 0.06,
        inferior_temporal: stage >= 2 ? 0.82 : stage === 1 ? 0.49 : 0.07,
        nasal: stage >= 3 ? 0.71 : stage === 2 ? 0.35 : 0.05,
      },
    },
    vessel_stats: {
      vessel_density_percent: vesselDensity,
      vessel_health_text:
        stage === 0
          ? 'Normal capillary caliber and branching fractal dimension.'
          : stage === 1
          ? 'Early focal arteriolar narrowing observed in temporal branches.'
          : stage === 2
          ? 'Moderate vessel attenuation and venous dilation with lipid exudates.'
          : stage === 3
          ? 'Severe capillary drop-out, venous beading, and widespread ischemia.'
          : 'Extensive capillary non-perfusion with abnormal neovascular fronds.',
      quadrant_density: {
        superior_nasal: Number((vesselDensity * 1.02).toFixed(1)),
        superior_temporal: Number((vesselDensity * 0.96).toFixed(1)),
        inferior_nasal: Number((vesselDensity * 1.05).toFixed(1)),
        inferior_temporal: Number((vesselDensity * 0.92).toFixed(1)),
      },
    },
    report: {
      current_diagnosis: {
        stage,
        stage_name: stageMeta.name,
        confidence: `${confidence.toFixed(1)}%`,
        plain_language: plainDescriptions[stage],
      },
      visual_findings: {
        heatmap_summary:
          stage >= 2
            ? 'Deep Grad-CAM attention focuses heavily on the paramacular vascular arcade, detecting clustered microvascular lesions and elevated permeability.'
            : stage === 1
            ? 'Heatmap reveals localized activation points consistent with isolated microaneurysms along the temporal arcade.'
            : 'Homogeneous baseline heat distribution with no pathological activation peaks across all 4 retinal quadrants.',
        vessel_analysis: `Vessel segmentation demonstrates an effective blood vessel density of ${vesselDensity}% with ${
          stage <= 1 ? 'preserved microvascular integrity' : 'progressive capillary attenuation and leakage'
        }.`,
      },
      risk_prediction: {
        '6_month': {
          progression_risk_percent: stage === 0 ? '2-4%' : stage === 1 ? '12-18%' : stage === 2 ? '28-38%' : stage === 3 ? '55-65%' : '85-95%',
          scenario_if_untreated:
            stage === 0
              ? 'Low probability of developing lesions if glucose remains stable.'
              : stage <= 2
              ? 'Likely development of macular edema, increasing blurriness, and accelerated vascular leakage.'
              : 'Severe risk of sudden vision loss, vitreous hemorrhage, or tractional retinal detachment.',
          scenario_if_managed:
            stage <= 1
              ? 'Complete stabilization and up to 90% prevention of retinopathy advancement.'
              : 'Over 80% reduction in vision loss risk with timely medical and laser/injection therapy.',
        },
        '12_month': {
          progression_risk_percent: stage === 0 ? '5-8%' : stage === 1 ? '22-30%' : stage === 2 ? '45-55%' : stage === 3 ? '75-85%' : '>95%',
          scenario_if_untreated:
            stage <= 1
              ? 'Potential transition to moderate NPDR with hard exudates encroaching on central vision.'
              : 'Irreversible photoreceptor apoptosis and severe functional low-vision disability.',
          scenario_if_managed:
            'Long-term preservation of central visual acuity and stabilized retinal perfusion.',
        },
      },
      action_plan: actionPlans[stage],
      diet_recommendations: diets[stage],
      urgency,
      recommended_follow_up: followUp,
      disclaimer: 'This is an AI-assisted screening assessment, NOT a definitive diagnosis. Clinical review by an ophthalmologist is mandatory.',
    },
    images: {
      original: createFundusDataUrl(stage, 'original'),
      heatmap: createFundusDataUrl(stage, 'heatmap'),
      vessels: createFundusDataUrl(stage, 'vessels'),
    },
    eye: 'OD',
    safety_state: 'VERIFIED',
    automation_level: 'AUTOMATED_ASSISTANCE',
    reason_codes: [],
    longitudinal_state: 'LIMITED_LONGITUDINAL_HISTORY',
    progression_availability_message: 'Progression prediction unavailable: insufficient longitudinal data.',
  };
}

export const INITIAL_PATIENTS: Patient[] = [
  {
    id: 'P-1001',
    name: 'Rajesh Kumar',
    age: 56,
    gender: 'Male',
    diabetes_duration: 8,
    sugar_level: 154,
    hba1c: 7.4,
    phone: '+91 98251 44102',
    location: 'Ahmedabad, Gujarat',
    notes: 'Type 2 Diabetes since 2018. Complaining of occasional blurry vision when reading in bright daylight.',
    created_at: '2024-03-15',
    scans: [
      buildSyntheticScan('P-1001', 'Rajesh Kumar', 2, '2026-08-10', 89.4),
      buildSyntheticScan('P-1001', 'Rajesh Kumar', 1, '2025-09-12', 91.2),
      buildSyntheticScan('P-1001', 'Rajesh Kumar', 1, '2024-11-04', 93.0),
    ],
  },
  {
    id: 'P-1002',
    name: 'Ananya Sharma',
    age: 44,
    gender: 'Female',
    diabetes_duration: 4,
    sugar_level: 118,
    hba1c: 6.2,
    phone: '+91 94140 88219',
    location: 'Jaipur, Rajasthan',
    notes: 'Well-controlled early diabetes. Regular screening attendee.',
    created_at: '2024-06-20',
    scans: [
      buildSyntheticScan('P-1002', 'Ananya Sharma', 0, '2026-07-28', 98.2),
      buildSyntheticScan('P-1002', 'Ananya Sharma', 0, '2025-07-14', 97.6),
    ],
  },
  {
    id: 'P-1003',
    name: 'Meenakshi Patel',
    age: 62,
    gender: 'Female',
    diabetes_duration: 14,
    sugar_level: 195,
    hba1c: 8.9,
    phone: '+91 97243 19004',
    location: 'Surat, Gujarat',
    notes: 'Long-standing diabetes with mild hypertension. Reports dark floater in right eye.',
    created_at: '2023-11-10',
    scans: [
      buildSyntheticScan('P-1003', 'Meenakshi Patel', 3, '2026-08-18', 93.7),
      buildSyntheticScan('P-1003', 'Meenakshi Patel', 2, '2025-10-05', 88.0),
      buildSyntheticScan('P-1003', 'Meenakshi Patel', 2, '2024-08-22', 86.5),
    ],
  },
  {
    id: 'P-1004',
    name: 'Vikramjit Singh',
    age: 68,
    gender: 'Male',
    diabetes_duration: 21,
    sugar_level: 245,
    hba1c: 10.4,
    phone: '+91 98150 33412',
    location: 'Amritsar, Punjab',
    notes: 'Severe photophobia and reduced contrast sensitivity. Urgent retinal evaluation indicated.',
    created_at: '2023-04-18',
    scans: [
      buildSyntheticScan('P-1004', 'Vikramjit Singh', 4, '2026-08-21', 97.9),
      buildSyntheticScan('P-1004', 'Vikramjit Singh', 3, '2025-12-01', 94.1),
    ],
  },
  {
    id: 'P-1005',
    name: 'Kishore Dave',
    age: 51,
    gender: 'Male',
    diabetes_duration: 6,
    sugar_level: 138,
    hba1c: 6.9,
    phone: '+91 99099 22134',
    location: 'Vadodara, Gujarat',
    notes: 'Screened at rural outreach camp. Borderline HbA1c.',
    created_at: '2025-01-14',
    scans: [
      buildSyntheticScan('P-1005', 'Kishore Dave', 1, '2026-06-11', 90.5),
    ],
  },
  {
    id: 'P-1006',
    name: 'Sunita Roy',
    age: 59,
    gender: 'Female',
    diabetes_duration: 11,
    sugar_level: 172,
    hba1c: 8.1,
    phone: '+91 98311 77620',
    location: 'Kolkata, West Bengal',
    notes: 'Referred from community health center for macular thickness assessment.',
    created_at: '2025-04-09',
    scans: [
      buildSyntheticScan('P-1006', 'Sunita Roy', 2, '2026-08-04', 88.7),
    ],
  },
];
