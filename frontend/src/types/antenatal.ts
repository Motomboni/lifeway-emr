/**
 * TypeScript types for Antenatal Clinic Management Module
 * 
 * Comprehensive type definitions for antenatal records, visits, and outcomes.
 */

// ============================================================================
// Enums and Constants
// ============================================================================

export type PregnancyOutcome =
  | 'ONGOING'
  | 'DELIVERED'
  | 'MISCARRIAGE'
  | 'STILLBIRTH'
  | 'TERMINATION'
  | 'ECTOPIC'
  | 'MOLAR';

export type Parity =
  | 'PRIMIGRAVIDA'
  | 'MULTIGRAVIDA'
  | 'GRAND_MULTIGRAVIDA';

export type PregnancyType =
  | 'SINGLETON'
  | 'TWINS'
  | 'TRIPLETS'
  | 'MORE';

export type VisitType =
  | 'BOOKING'
  | 'ROUTINE'
  | 'EMERGENCY'
  | 'FOLLOW_UP'
  | 'DELIVERY';

export type FetalPresentation =
  | 'CEPHALIC'
  | 'BREECH'
  | 'TRANSVERSE'
  | 'UNKNOWN';

export type UrineTestResult =
  | 'NEGATIVE'
  | 'TRACE'
  | '1+'
  | '2+'
  | '3+'
  | '4+';

export type ScanType =
  | 'DATING'
  | 'NT'
  | 'ANATOMY'
  | 'GROWTH'
  | 'DOPPLER'
  | 'BIOPHYSICAL'
  | 'OTHER';

export type AmnioticFluid =
  | 'NORMAL'
  | 'OLIGOHYDRAMNIOS'
  | 'POLYHYDRAMNIOS';

export type BloodGroup =
  | 'A+'
  | 'A-'
  | 'B+'
  | 'B-'
  | 'AB+'
  | 'AB-'
  | 'O+'
  | 'O-';

export type Rhesus =
  | 'POSITIVE'
  | 'NEGATIVE';

export type TestResult =
  | 'NEGATIVE'
  | 'POSITIVE'
  | 'PENDING';

export type MedicationCategory =
  | 'FOLIC_ACID'
  | 'IRON'
  | 'CALCIUM'
  | 'MULTIVITAMIN'
  | 'ANTIMALARIAL'
  | 'ANTIBIOTIC'
  | 'ANALGESIC'
  | 'ANTIHYPERTENSIVE'
  | 'ANTIDIABETIC'
  | 'OTHER';

export type DeliveryType =
  | 'VAGINAL'
  | 'VAGINAL_INSTRUMENTAL'
  | 'CESAREAN_ELECTIVE'
  | 'CESAREAN_EMERGENCY';

export type BabyGender =
  | 'MALE'
  | 'FEMALE';

// ============================================================================
// Antenatal Record
// ============================================================================

export interface AntenatalRecord {
  id: number;
  patient: number;
  patient_name?: string;
  pregnancy_number: number;
  booking_date: string;
  lmp: string;
  edd: string;
  parity: Parity;
  gravida: number;
  para: number;
  abortions: number;
  living_children: number;
  past_medical_history: string;
  past_surgical_history: string;
  family_history: string;
  allergies: string;
  previous_cs: boolean;
  previous_cs_count: number;
  previous_complications: string;
  pregnancy_type: PregnancyType;
  high_risk: boolean;
  risk_factors: string[];
  outcome: PregnancyOutcome;
  delivery_date?: string;
  delivery_gestational_age_weeks?: number;
  delivery_gestational_age_days?: number;
  clinical_notes: string;
  created_by: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  current_gestational_age_weeks?: number;
  current_gestational_age_days?: number;
}

export interface AntenatalRecordListItem {
  id: number;
  patient: number;
  patient_name: string;
  pregnancy_number: number;
  booking_date: string;
  lmp: string;
  edd: string;
  outcome: PregnancyOutcome;
  high_risk: boolean;
  current_gestational_age_weeks?: number;
  current_gestational_age_days?: number;
  created_at: string;
}

export interface AntenatalRecordCreateData {
  patient: number;
  pregnancy_number?: number;
  booking_date: string;
  lmp: string;
  edd: string;
  parity?: Parity;
  gravida?: number;
  para?: number;
  abortions?: number;
  living_children?: number;
  past_medical_history?: string;
  past_surgical_history?: string;
  family_history?: string;
  allergies?: string;
  previous_cs?: boolean;
  previous_cs_count?: number;
  previous_complications?: string;
  pregnancy_type?: PregnancyType;
  high_risk?: boolean;
  risk_factors?: string[];
  clinical_notes?: string;
}

export interface AntenatalRecordUpdateData {
  outcome?: PregnancyOutcome;
  delivery_date?: string;
  delivery_gestational_age_weeks?: number;
  delivery_gestational_age_days?: number;
  high_risk?: boolean;
  risk_factors?: string[];
  clinical_notes?: string;
}

export interface AntenatalRecordSummary {
  record_id: number;
  patient_name: string;
  pregnancy_number: number;
  booking_date: string;
  lmp: string;
  edd: string;
  current_gestational_age_weeks?: number;
  current_gestational_age_days?: number;
  outcome: PregnancyOutcome;
  high_risk: boolean;
  visits_count: number;
  ultrasounds_count: number;
  labs_count: number;
}

// ============================================================================
// Antenatal Visit
// ============================================================================

export interface AntenatalVisit {
  id: number;
  antenatal_record: number;
  visit: number;
  visit_date: string;
  visit_type: VisitType;
  gestational_age_weeks: number;
  gestational_age_days: number;
  chief_complaint: string;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  weight?: number;
  fundal_height?: number;
  fetal_heart_rate?: number;
  fetal_presentation?: FetalPresentation;
  urine_protein?: UrineTestResult;
  urine_glucose?: UrineTestResult;
  clinical_notes: string;
  next_appointment_date?: string;
  recorded_by: number;
  recorded_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AntenatalVisitCreateData {
  antenatal_record: number;
  visit: number;
  visit_date: string;
  visit_type?: VisitType;
  gestational_age_weeks: number;
  gestational_age_days?: number;
  chief_complaint?: string;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  weight?: number;
  fundal_height?: number;
  fetal_heart_rate?: number;
  fetal_presentation?: FetalPresentation;
  urine_protein?: UrineTestResult;
  urine_glucose?: UrineTestResult;
  clinical_notes?: string;
  next_appointment_date?: string;
}

// ============================================================================
// Antenatal Ultrasound
// ============================================================================

export interface AntenatalUltrasound {
  id: number;
  antenatal_visit: number;
  scan_date: string;
  scan_type: ScanType;
  gestational_age_weeks: number;
  gestational_age_days: number;
  crl?: number;
  bpd?: number;
  hc?: number;
  ac?: number;
  fl?: number;
  estimated_fetal_weight?: number;
  number_of_fetuses: number;
  fetal_presentation?: FetalPresentation;
  placenta_location?: string;
  placenta_grade?: string;
  amniotic_fluid?: AmnioticFluid;
  findings: string;
  report: string;
  performed_by: number;
  performed_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AntenatalUltrasoundCreateData {
  antenatal_visit: number;
  scan_date: string;
  scan_type: ScanType;
  gestational_age_weeks: number;
  gestational_age_days?: number;
  crl?: number;
  bpd?: number;
  hc?: number;
  ac?: number;
  fl?: number;
  estimated_fetal_weight?: number;
  number_of_fetuses?: number;
  fetal_presentation?: FetalPresentation;
  placenta_location?: string;
  placenta_grade?: string;
  amniotic_fluid?: AmnioticFluid;
  findings?: string;
  report?: string;
}

// ============================================================================
// Antenatal Lab
// ============================================================================

export interface AntenatalLab {
  id: number;
  antenatal_visit: number;
  test_name: string;
  test_date: string;
  hb?: number;
  pcv?: number;
  blood_group?: BloodGroup;
  rhesus?: Rhesus;
  hiv?: TestResult;
  hbsag?: TestResult;
  vdrl?: TestResult;
  results: string;
  notes: string;
  ordered_by: number;
  ordered_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AntenatalLabCreateData {
  antenatal_visit: number;
  test_name: string;
  test_date: string;
  hb?: number;
  pcv?: number;
  blood_group?: BloodGroup;
  rhesus?: Rhesus;
  hiv?: TestResult;
  hbsag?: TestResult;
  vdrl?: TestResult;
  results?: string;
  notes?: string;
}

// ============================================================================
// Antenatal Medication
// ============================================================================

export interface AntenatalMedication {
  id: number;
  antenatal_visit: number;
  medication_name: string;
  category: MedicationCategory;
  dose: string;
  frequency: string;
  duration?: string;
  start_date: string;
  end_date?: string;
  notes: string;
  prescribed_by: number;
  prescribed_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AntenatalMedicationCreateData {
  antenatal_visit: number;
  medication_name: string;
  category: MedicationCategory;
  dose: string;
  frequency: string;
  duration?: string;
  start_date: string;
  end_date?: string;
  notes?: string;
}

// ============================================================================
// Antenatal Outcome
// ============================================================================

export interface AdditionalBaby {
  gender: BabyGender;
  weight: number;
  apgar_1min: number;
  apgar_5min: number;
}

export interface AntenatalOutcome {
  id: number;
  antenatal_record: number;
  delivery_date: string;
  delivery_time?: string;
  delivery_type: DeliveryType;
  delivery_gestational_age_weeks: number;
  delivery_gestational_age_days: number;
  number_of_babies: number;
  live_births: number;
  stillbirths: number;
  baby_1_gender?: BabyGender;
  baby_1_weight?: number;
  baby_1_apgar_1min?: number;
  baby_1_apgar_5min?: number;
  additional_babies: AdditionalBaby[];
  maternal_complications: string;
  neonatal_complications: string;
  notes: string;
  recorded_by: number;
  recorded_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AntenatalOutcomeCreateData {
  antenatal_record: number;
  delivery_date: string;
  delivery_time?: string;
  delivery_type: DeliveryType;
  delivery_gestational_age_weeks: number;
  delivery_gestational_age_days?: number;
  number_of_babies?: number;
  live_births?: number;
  stillbirths?: number;
  baby_1_gender?: BabyGender;
  baby_1_weight?: number;
  baby_1_apgar_1min?: number;
  baby_1_apgar_5min?: number;
  additional_babies?: AdditionalBaby[];
  maternal_complications?: string;
  neonatal_complications?: string;
  notes?: string;
}
