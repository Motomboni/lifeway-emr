/**
 * TypeScript types for IVF Treatment Module
 * 
 * Comprehensive type definitions for IVF cycles, procedures, and outcomes.
 */

// ============================================================================
// Enums and Constants
// ============================================================================

export type CycleType = 
  | 'FRESH_IVF'
  | 'FET'
  | 'IUI'
  | 'ICSI'
  | 'EGG_DONATION'
  | 'SPERM_DONATION'
  | 'SURROGACY'
  | 'EGG_FREEZING'
  | 'SPERM_FREEZING';

export type CycleStatus =
  | 'PLANNED'
  | 'STIMULATION'
  | 'RETRIEVAL'
  | 'FERTILIZATION'
  | 'CULTURE'
  | 'TRANSFER'
  | 'LUTEAL'
  | 'PREGNANCY_TEST'
  | 'PREGNANT'
  | 'NOT_PREGNANT'
  | 'CANCELLED'
  | 'COMPLETED';

export type CancellationReason =
  | 'POOR_RESPONSE'
  | 'OHSS_RISK'
  | 'NO_FERTILIZATION'
  | 'NO_VIABLE_EMBRYOS'
  | 'PATIENT_REQUEST'
  | 'MEDICAL_CONTRAINDICATION'
  | 'FINANCIAL'
  | 'OTHER';

export type PregnancyOutcome =
  | 'POSITIVE'
  | 'NEGATIVE'
  | 'CHEMICAL'
  | 'ECTOPIC'
  | 'MISCARRIAGE'
  | 'ONGOING'
  | 'LIVE_BIRTH'
  | 'STILLBIRTH';

export type EmbryoStatus =
  | 'FERTILIZED'
  | 'CLEAVING'
  | 'MORULA'
  | 'BLASTOCYST'
  | 'TRANSFERRED'
  | 'FROZEN'
  | 'THAWED'
  | 'DISCARDED'
  | 'DONATED'
  | 'ARRESTED';

export type FertilizationMethod =
  | 'IVF'
  | 'ICSI'
  | 'SPLIT'
  | 'IMSI';

export type SpermSampleSource =
  | 'FRESH'
  | 'FROZEN'
  | 'TESE'
  | 'MESA'
  | 'PESA'
  | 'DONOR';

export type SpermAssessment =
  | 'NORMOZOOSPERMIA'
  | 'OLIGOZOOSPERMIA'
  | 'ASTHENOZOOSPERMIA'
  | 'TERATOZOOSPERMIA'
  | 'OLIGOASTHENOZOOSPERMIA'
  | 'OLIGOASTHENOTERATOZOOSPERMIA'
  | 'AZOOSPERMIA'
  | 'CRYPTOZOOSPERMIA'
  | 'NECROZOOSPERMIA';

export type ConsentType =
  | 'TREATMENT'
  | 'EGG_RETRIEVAL'
  | 'SPERM_COLLECTION'
  | 'EMBRYO_TRANSFER'
  | 'EMBRYO_FREEZING'
  | 'EMBRYO_DISPOSITION'
  | 'EGG_FREEZING'
  | 'SPERM_FREEZING'
  | 'PGT'
  | 'DONOR_EGG'
  | 'DONOR_SPERM'
  | 'SURROGACY';

export type PGTResult =
  | 'EUPLOID'
  | 'ANEUPLOID'
  | 'MOSAIC'
  | 'NO_RESULT'
  | 'PENDING';

// ============================================================================
// IVF Cycle
// ============================================================================

export interface IVFCycle {
  id: number;
  patient: number;
  patient_name: string;
  partner?: number;
  partner_name?: string;
  cycle_number: number;
  cycle_type: CycleType;
  status: CycleStatus;
  planned_start_date?: string;
  actual_start_date?: string;
  lmp_date?: string;
  protocol: string;
  diagnosis: string;
  consent_signed: boolean;
  consent_date?: string;
  partner_consent_signed: boolean;
  partner_consent_date?: string;
  cancellation_reason?: CancellationReason;
  cancellation_notes?: string;
  cancelled_at?: string;
  pregnancy_test_date?: string;
  beta_hcg_result?: number;
  pregnancy_outcome?: PregnancyOutcome;
  estimated_cost?: number;
  insurance_pre_auth: boolean;
  insurance_pre_auth_number?: string;
  clinical_notes: string;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface IVFCycleListItem {
  id: number;
  patient: number;
  patient_name: string;
  partner?: number;
  partner_name?: string;
  cycle_number: number;
  cycle_type: CycleType;
  status: CycleStatus;
  planned_start_date?: string;
  actual_start_date?: string;
  consent_signed: boolean;
  pregnancy_outcome?: PregnancyOutcome;
  created_at: string;
}

export interface IVFCycleCreateData {
  patient: number;
  partner?: number;
  cycle_type: CycleType;
  planned_start_date?: string;
  lmp_date?: string;
  protocol?: string;
  diagnosis?: string;
  estimated_cost?: number;
  insurance_pre_auth?: boolean;
  insurance_pre_auth_number?: string;
  clinical_notes?: string;
}

export interface IVFCycleUpdateData {
  status?: CycleStatus;
  actual_start_date?: string;
  protocol?: string;
  diagnosis?: string;
  consent_signed?: boolean;
  consent_date?: string;
  partner_consent_signed?: boolean;
  partner_consent_date?: string;
  pregnancy_test_date?: string;
  beta_hcg_result?: number;
  pregnancy_outcome?: PregnancyOutcome;
  estimated_cost?: number;
  clinical_notes?: string;
}

export interface IVFCycleFull extends IVFCycle {
  stimulation_records: OvarianStimulation[];
  oocyte_retrieval?: OocyteRetrieval;
  sperm_analyses: SpermAnalysisListItem[];
  embryos: EmbryoListItem[];
  embryo_transfers: EmbryoTransfer[];
  medications: IVFMedication[];
  outcome?: IVFOutcome;
  consents: IVFConsent[];
  total_embryos: number;
  frozen_embryos: number;
  transferred_embryos: number;
}

// ============================================================================
// Ovarian Stimulation
// ============================================================================

export interface Medication {
  name: string;
  dose: number;
  unit: string;
}

export interface OvarianStimulation {
  id: number;
  cycle: number;
  day: number;
  date: string;
  estradiol?: number;
  lh?: number;
  progesterone?: number;
  endometrial_thickness?: number;
  endometrial_pattern?: 'TRILAMINAR' | 'HYPERECHOIC' | 'HYPOECHOIC' | 'HOMOGENEOUS';
  right_ovary_follicles: number[];
  left_ovary_follicles: number[];
  medications: Medication[];
  notes: string;
  next_appointment?: string;
  total_follicle_count: number;
  leading_follicles: number;
  recorded_by: number;
  recorded_by_name: string;
  created_at: string;
}

export interface OvarianStimulationCreateData {
  day: number;
  date: string;
  estradiol?: number;
  lh?: number;
  progesterone?: number;
  endometrial_thickness?: number;
  endometrial_pattern?: string;
  right_ovary_follicles?: number[];
  left_ovary_follicles?: number[];
  medications?: Medication[];
  notes?: string;
  next_appointment?: string;
}

// ============================================================================
// Oocyte Retrieval
// ============================================================================

export interface OocyteRetrieval {
  id: number;
  cycle: number;
  procedure_date: string;
  procedure_time?: string;
  trigger_medication: string;
  trigger_time?: string;
  anesthesia_type: 'NONE' | 'LOCAL' | 'CONSCIOUS_SEDATION' | 'GENERAL';
  anesthesiologist?: string;
  right_ovary_oocytes: number;
  left_ovary_oocytes: number;
  total_oocytes_retrieved: number;
  mature_oocytes: number;
  immature_oocytes: number;
  degenerated_oocytes: number;
  complications: string;
  blood_loss?: 'MINIMAL' | 'MODERATE' | 'SIGNIFICANT';
  recovery_notes: string;
  discharge_time?: string;
  performed_by: number;
  performed_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface OocyteRetrievalCreateData {
  procedure_date: string;
  procedure_time?: string;
  trigger_medication?: string;
  trigger_time?: string;
  anesthesia_type?: string;
  anesthesiologist?: string;
  right_ovary_oocytes: number;
  left_ovary_oocytes: number;
  mature_oocytes?: number;
  immature_oocytes?: number;
  degenerated_oocytes?: number;
  complications?: string;
  blood_loss?: string;
  recovery_notes?: string;
  discharge_time?: string;
}

// ============================================================================
// Sperm Analysis
// ============================================================================

export interface SpermAnalysisListItem {
  id: number;
  patient: number;
  patient_name: string;
  collection_date: string;
  concentration?: number;
  total_motility?: number;
  normal_forms?: number;
  assessment?: SpermAssessment;
  created_at: string;
}

export interface SpermAnalysis {
  id: number;
  patient: number;
  patient_name: string;
  cycle?: number;
  collection_date: string;
  collection_time?: string;
  abstinence_days?: number;
  sample_source: SpermSampleSource;
  // Macroscopic
  volume?: number;
  appearance?: 'NORMAL' | 'YELLOW' | 'RED_BROWN' | 'CLEAR';
  liquefaction_time?: number;
  ph?: number;
  viscosity?: 'NORMAL' | 'INCREASED';
  // Concentration
  concentration?: number;
  total_sperm_count?: number;
  // Motility
  progressive_motility?: number;
  non_progressive_motility?: number;
  immotile?: number;
  total_motility?: number;
  // Morphology
  normal_forms?: number;
  head_defects?: number;
  midpiece_defects?: number;
  tail_defects?: number;
  // Other
  vitality?: number;
  round_cells?: number;
  wbc_count?: number;
  dna_fragmentation_index?: number;
  // Assessment
  assessment?: SpermAssessment;
  recommendation: string;
  notes: string;
  analyzed_by: number;
  analyzed_by_name: string;
  created_at: string;
}

export interface SpermAnalysisCreateData {
  patient: number;
  cycle?: number;
  collection_date: string;
  collection_time?: string;
  abstinence_days?: number;
  sample_source?: SpermSampleSource;
  volume?: number;
  appearance?: string;
  liquefaction_time?: number;
  ph?: number;
  viscosity?: string;
  concentration?: number;
  total_sperm_count?: number;
  progressive_motility?: number;
  non_progressive_motility?: number;
  immotile?: number;
  total_motility?: number;
  normal_forms?: number;
  head_defects?: number;
  midpiece_defects?: number;
  tail_defects?: number;
  vitality?: number;
  round_cells?: number;
  wbc_count?: number;
  dna_fragmentation_index?: number;
  assessment?: SpermAssessment;
  recommendation?: string;
  notes?: string;
}

// ============================================================================
// Embryo
// ============================================================================

export interface EmbryoListItem {
  id: number;
  lab_id: string;
  embryo_number: number;
  status: EmbryoStatus;
  fertilization_method: FertilizationMethod;
  day3_grade?: string;
  blastocyst_grade?: string;
  pgt_performed: boolean;
  pgt_result?: PGTResult;
  disposition?: string;
}

export interface Embryo {
  id: number;
  cycle: number;
  embryo_number: number;
  lab_id: string;
  status: EmbryoStatus;
  fertilization_method: FertilizationMethod;
  fertilization_date: string;
  fertilization_time?: string;
  // Day 1
  day1_pn_status?: '2PN' | '1PN' | '3PN' | '0PN' | 'DEGENERATED';
  // Day 2-3
  day2_cell_count?: number;
  day3_cell_count?: number;
  day3_grade?: string;
  fragmentation?: number;
  // Blastocyst
  blastocyst_day?: 5 | 6 | 7;
  blastocyst_grade?: string;
  expansion_grade?: '1' | '2' | '3' | '4' | '5' | '6';
  icm_grade?: 'A' | 'B' | 'C';
  trophectoderm_grade?: 'A' | 'B' | 'C';
  // PGT
  pgt_performed: boolean;
  pgt_result?: PGTResult;
  pgt_details?: string;
  // Cryo
  frozen_date?: string;
  storage_location?: string;
  straw_id?: string;
  thaw_date?: string;
  survived_thaw?: boolean;
  // Disposition
  disposition?: string;
  disposition_date?: string;
  disposition_notes?: string;
  notes: string;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface EmbryoCreateData {
  embryo_number: number;
  fertilization_method: FertilizationMethod;
  fertilization_date: string;
  fertilization_time?: string;
  day1_pn_status?: string;
  notes?: string;
}

// ============================================================================
// Embryo Transfer
// ============================================================================

export interface EmbryoTransfer {
  id: number;
  cycle: number;
  transfer_date: string;
  transfer_time?: string;
  transfer_type: 'FRESH' | 'FROZEN';
  embryos: number[];
  embryo_details?: EmbryoListItem[];
  embryos_transferred_count: number;
  embryo_stage?: 'CLEAVAGE' | 'BLASTOCYST';
  catheter_type?: string;
  ultrasound_guided: boolean;
  difficulty: 'EASY' | 'MODERATE' | 'DIFFICULT';
  endometrial_thickness?: number;
  uterine_position?: 'ANTEVERTED' | 'RETROVERTED' | 'MIDPOSITION';
  distance_from_fundus?: number;
  blood_on_catheter: boolean;
  mucus_on_catheter: boolean;
  embryos_retained: boolean;
  bed_rest_duration: number;
  medications_prescribed: any[];
  notes: string;
  performed_by: number;
  performed_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface EmbryoTransferCreateData {
  transfer_date: string;
  transfer_time?: string;
  transfer_type: 'FRESH' | 'FROZEN';
  embryos: number[];
  embryos_transferred_count: number;
  embryo_stage?: string;
  catheter_type?: string;
  ultrasound_guided?: boolean;
  difficulty?: string;
  endometrial_thickness?: number;
  uterine_position?: string;
  distance_from_fundus?: number;
  blood_on_catheter?: boolean;
  mucus_on_catheter?: boolean;
  embryos_retained?: boolean;
  bed_rest_duration?: number;
  medications_prescribed?: any[];
  notes?: string;
}

// ============================================================================
// IVF Medication
// ============================================================================

export type MedicationCategory =
  | 'GNRH_AGONIST'
  | 'GNRH_ANTAGONIST'
  | 'GONADOTROPIN'
  | 'HCG'
  | 'PROGESTERONE'
  | 'ESTROGEN'
  | 'ANTIBIOTIC'
  | 'OTHER';

export interface IVFMedication {
  id: number;
  cycle: number;
  medication_name: string;
  category: MedicationCategory;
  dose: number;
  unit: string;
  route: 'SUBCUTANEOUS' | 'INTRAMUSCULAR' | 'ORAL' | 'VAGINAL' | 'TRANSDERMAL';
  frequency: string;
  start_date: string;
  end_date?: string;
  instructions: string;
  prescribed_by: number;
  prescribed_by_name: string;
  created_at: string;
}

export interface IVFMedicationCreateData {
  medication_name: string;
  category: MedicationCategory;
  dose: number;
  unit: string;
  route: string;
  frequency: string;
  start_date: string;
  end_date?: string;
  instructions?: string;
}

// ============================================================================
// IVF Outcome
// ============================================================================

export interface IVFOutcome {
  id: number;
  cycle: number;
  clinical_pregnancy: boolean;
  clinical_pregnancy_date?: string;
  fetal_heartbeat: boolean;
  fetal_heartbeat_date?: string;
  gestational_sacs: number;
  fetal_poles: number;
  miscarriage: boolean;
  miscarriage_date?: string;
  miscarriage_gestational_age?: number;
  ectopic: boolean;
  delivery_date?: string;
  gestational_age_at_delivery?: number;
  delivery_type?: 'VAGINAL' | 'CESAREAN_ELECTIVE' | 'CESAREAN_EMERGENCY';
  live_births: number;
  stillbirths: number;
  neonatal_deaths: number;
  birth_weights: number[];
  maternal_complications: string;
  neonatal_complications: string;
  notes: string;
  recorded_by: number;
  recorded_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface IVFOutcomeCreateData {
  clinical_pregnancy?: boolean;
  clinical_pregnancy_date?: string;
  fetal_heartbeat?: boolean;
  fetal_heartbeat_date?: string;
  gestational_sacs?: number;
  fetal_poles?: number;
  notes?: string;
}

// ============================================================================
// IVF Consent
// ============================================================================

export interface IVFConsent {
  id: number;
  cycle: number;
  consent_type: ConsentType;
  patient: number;
  patient_name: string;
  signed: boolean;
  signed_date?: string;
  signed_time?: string;
  witness_name?: string;
  witness_signature: boolean;
  document_path?: string;
  revoked: boolean;
  revoked_date?: string;
  revocation_reason?: string;
  notes: string;
  recorded_by: number;
  recorded_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface IVFConsentCreateData {
  consent_type: ConsentType;
  patient: number;
  notes?: string;
}

// ============================================================================
// Statistics
// ============================================================================

export interface IVFStatistics {
  total_cycles: number;
  cycles_by_status: { status: CycleStatus; count: number }[];
  cycles_by_type: { cycle_type: CycleType; count: number }[];
  pregnancy_rate: number;
  clinical_pregnancy_rate: number;
  live_birth_rate: number;
  completed_cycles: number;
}

// ============================================================================
// Display Helpers
// ============================================================================

export const CYCLE_TYPE_LABELS: Record<CycleType, string> = {
  FRESH_IVF: 'Fresh IVF Cycle',
  FET: 'Frozen Embryo Transfer',
  IUI: 'Intrauterine Insemination',
  ICSI: 'ICSI',
  EGG_DONATION: 'Egg Donation Cycle',
  SPERM_DONATION: 'Sperm Donation Cycle',
  SURROGACY: 'Surrogacy Cycle',
  EGG_FREEZING: 'Egg Freezing',
  SPERM_FREEZING: 'Sperm Freezing',
};

export const CYCLE_STATUS_LABELS: Record<CycleStatus, string> = {
  PLANNED: 'Planned',
  STIMULATION: 'Ovarian Stimulation',
  RETRIEVAL: 'Egg Retrieval',
  FERTILIZATION: 'Fertilization',
  CULTURE: 'Embryo Culture',
  TRANSFER: 'Embryo Transfer',
  LUTEAL: 'Luteal Phase Support',
  PREGNANCY_TEST: 'Pregnancy Test',
  PREGNANT: 'Pregnant',
  NOT_PREGNANT: 'Not Pregnant',
  CANCELLED: 'Cancelled',
  COMPLETED: 'Completed',
};

export const EMBRYO_STATUS_LABELS: Record<EmbryoStatus, string> = {
  FERTILIZED: 'Fertilized (2PN)',
  CLEAVING: 'Cleaving',
  MORULA: 'Morula',
  BLASTOCYST: 'Blastocyst',
  TRANSFERRED: 'Transferred',
  FROZEN: 'Frozen',
  THAWED: 'Thawed',
  DISCARDED: 'Discarded',
  DONATED: 'Donated',
  ARRESTED: 'Arrested Development',
};
