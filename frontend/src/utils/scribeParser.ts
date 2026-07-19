/**
 * Parse Clinical AI Scribe structured notes into consultation form fields.
 */

export interface ParsedScribeSections {
  history: string;
  examination: string;
  diagnosis: string;
  clinical_notes: string;
}

export interface ValidatedScribeCode {
  diagnosis: string;
  icd11: string;
  nhia: string;
  icd11_valid: boolean;
  nhia_valid: boolean;
  match_status: string;
  tariff_name?: string | null;
  amount_ngn?: string | null;
  category?: string | null;
}

export interface CodeValidation {
  extracted_codes: Array<{ diagnosis: string; icd11: string; nhia: string }>;
  validated_codes: ValidatedScribeCode[];
  unmatched_icd11: string[];
  unmatched_nhia: string[];
  suggested_tariffs: Array<{
    icd11: string;
    nhia_code: string;
    name: string;
    amount_ngn: string;
    category: string;
  }>;
  all_matched: boolean;
}

export interface GenerateScribeNoteResponse {
  structured_note: string;
  note_type: string;
  template_used?: string;
  raw_transcript?: string;
  request_id?: number | null;
  code_validation?: CodeValidation;
  parsed_sections?: ParsedScribeSections;
  icd11_apply_payload?: Array<{
    code: string;
    description: string;
    confidence?: number;
  }>;
}

function sectionContent(text: string, headers: string[]): string {
  for (const header of headers) {
    const pattern = new RegExp(`^\\s*#{1,3}\\s*${header}\\s*$`, 'im');
    const match = pattern.exec(text);
    if (!match) continue;
    const start = match.index + match[0].length;
    const rest = text.slice(start);
    const next = rest.search(/^\s*#{1,3}\s+.+/m);
    const end = next >= 0 ? start + next : text.length;
    return text.slice(start, end).trim();
  }
  return '';
}

export function parseScribeSections(
  structuredNote: string,
  template = 'soap'
): ParsedScribeSections {
  const note = (structuredNote || '').trim();
  if (!note) {
    return { history: '', examination: '', diagnosis: '', clinical_notes: '' };
  }

  const templateKey = (template || 'soap').toLowerCase();

  if (templateKey === 'antenatal') {
    const history = sectionContent(note, [
      'Maternal Complaints & History',
      'Maternal History',
      'History',
      'Subjective',
    ]);
    const examination = sectionContent(note, [
      'Vitals & Examination',
      'Examination',
      'Objective',
    ]);
    const diagnosis = sectionContent(note, [
      'Assessment',
      'Encounter Classification',
      'Diagnosis',
    ]);
    const plan = sectionContent(note, ['Plan', 'Management Plan']);
    const obstetric = sectionContent(note, [
      'Obstetric Summary',
      'Antenatal Summary',
      'Booking Details',
    ]);
    const clinical_notes = [obstetric, plan].filter(Boolean).join('\n\n').trim();
    return { history, examination, diagnosis, clinical_notes };
  }

  const subjective = sectionContent(note, ['Subjective', 'Chief Complaint', 'History']);
  const objective = sectionContent(note, ['Objective', 'Examination', 'Physical Examination']);
  const assessment = sectionContent(note, ['Assessment', 'Diagnosis']);
  const plan = sectionContent(note, ['Plan', 'Management', 'Treatment Plan']);
  const cc = sectionContent(note, ['Chief Complaint']);
  const hpi = sectionContent(note, ['History of Present Illness', 'HPI']);

  const historyParts: string[] = [];
  if (cc) historyParts.push(`Chief Complaint:\n${cc}`);
  if (hpi) historyParts.push(`History of Present Illness:\n${hpi}`);
  if (subjective && historyParts.length === 0) historyParts.push(subjective);
  else if (subjective && !historyParts.join('\n').includes(subjective)) {
    historyParts.push(subjective);
  }

  let clinical_notes = plan;
  if (!clinical_notes) {
    clinical_notes = sectionContent(note, ['Follow-up', 'Patient Education']);
  }

  return {
    history: historyParts.join('\n\n').trim(),
    examination: objective,
    diagnosis: assessment,
    clinical_notes,
  };
}

export function matchStatusLabel(status: string): string {
  switch (status) {
    case 'matched':
      return 'NHIA verified';
    case 'nhia_ok_icd11_mismatch':
      return 'NHIA ok — ICD-11 mismatch';
    case 'nhia_ok_icd11_unknown':
      return 'NHIA ok — ICD-11 not in tariff';
    case 'icd11_ok_nhia_unknown':
      return 'ICD-11 known — NHIA unknown';
    default:
      return 'Unverified';
  }
}
