/**
 * Voice command intent parser for staff VoiceCommandBar.
 *
 * Scope: navigation + opening clinical workflows + ambient scribe control.
 * No silent clinical writes — visit-scoped actions require confirmation.
 */

export type VoiceIntentType =
  | 'navigate'
  | 'scribe_start'
  | 'scribe_stop'
  | 'scribe_generate'
  | 'scribe_apply'
  | 'clinic_invite'
  | 'help'
  | 'unknown';

export interface VoiceIntent {
  type: VoiceIntentType;
  path?: string;
  label: string;
  /** Spoken phrase matched (normalized) */
  matched: string;
  requiresConfirm: boolean;
  /** For clinic_invite — staff role filter */
  inviteRole?: string;
}

export interface VoiceParseContext {
  /** Visit id from current route, e.g. /visits/12/... */
  visitId?: string | null;
  /** Telemedicine session id from /telemedicine/room/:id */
  sessionId?: string | null;
  /** Current user role for help filtering */
  role?: string | null;
}

const WORD_NUMBERS: Record<string, string> = {
  zero: '0',
  oh: '0',
  one: '1',
  two: '2',
  three: '3',
  four: '4',
  five: '5',
  six: '6',
  seven: '7',
  eight: '8',
  nine: '9',
  ten: '10',
  eleven: '11',
  twelve: '12',
  thirteen: '13',
  fourteen: '14',
  fifteen: '15',
  sixteen: '16',
  seventeen: '17',
  eighteen: '18',
  nineteen: '19',
  twenty: '20',
  thirty: '30',
  forty: '40',
  fifty: '50',
  sixty: '60',
  seventy: '70',
  eighty: '80',
  ninety: '90',
};

/** Convert spoken number phrases to digits (supports up to 99 and digit runs). */
export function wordsToDigits(text: string): string {
  const tokens = text.split(/\s+/);
  const out: string[] = [];
  let i = 0;
  while (i < tokens.length) {
    const a = tokens[i];
    const b = tokens[i + 1];
    if (WORD_NUMBERS[a] !== undefined) {
      const tens = WORD_NUMBERS[a];
      // twenty one → 21
      if (
        b &&
        WORD_NUMBERS[b] !== undefined &&
        Number(tens) >= 20 &&
        Number(tens) % 10 === 0 &&
        Number(WORD_NUMBERS[b]) < 10
      ) {
        out.push(String(Number(tens) + Number(WORD_NUMBERS[b])));
        i += 2;
        continue;
      }
      out.push(tens);
      i += 1;
      continue;
    }
    out.push(a);
    i += 1;
  }
  return out.join(' ');
}

function normalize(utterance: string): string {
  let text = utterance
    .toLowerCase()
    .replace(/[^\w\s/-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  // Common ASR slips
  text = text
    .replace(/\bvisit to\b/g, 'visit')
    .replace(/\bfor the visit\b/g, 'for visit')
    .replace(/\bnumber\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  text = wordsToDigits(text);
  return text;
}

/** Optional spoken lead-ins: go to / open / show / start / launch */
const LEAD = '(?:(?:go to|open|show|start|launch|take me to|bring up) )?';
const THE = '(?:the )?';

const NAV_RULES: Array<{ patterns: RegExp[]; path: string; label: string }> = [
  {
    patterns: [new RegExp(`^${LEAD}${THE}dashboard$`), /^(home|main menu)$/],
    path: '/dashboard',
    label: 'Open dashboard',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:patients|patient list|patient management)$`),
      /^find (a )?patient$/,
      /^search patients?$/,
    ],
    path: '/patients',
    label: 'Open patients',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:patient )?registration$`),
      /^(register|new|add) (a )?patient$/,
      /^enroll (a )?patient$/,
    ],
    path: '/patients/register',
    label: 'Patient registration',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}patient verification$`),
      /^(verify|verification) patients?$/,
    ],
    path: '/patients/verification',
    label: 'Patient verification',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}visits?(?: list)?$`),
      /^(?:open )?visit queue$/,
      /^clinic (?:floor|queue)$/,
    ],
    path: '/visits',
    label: 'Open visits',
  },
  {
    patterns: [
      /^(?:show |open |go to )?(?:all )?open visits$/,
      /^(?:show )?active visits$/,
      /^visits ready for care$/,
    ],
    path: '/visits?status=OPEN',
    label: 'Show open visits',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:new visit|create visit|register visit)$`),
      /^(start|create|open) (a )?(new )?visit$/,
      /^check[- ]?in (a )?patient$/,
    ],
    path: '/visits/new',
    label: 'Create visit',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}inpatients?$`),
      /^(?:show |open )?(?:admitted|ward) patients?$/,
      /^ward list$/,
    ],
    path: '/inpatients',
    label: 'Open inpatients',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}appointments?$`),
      /^(?:book|schedule) (an )?appointment$/,
      /^clinic schedule$/,
    ],
    path: '/appointments',
    label: 'Open appointments',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}immunizations?(?: schedule)?$`),
      /^(?:record|give|document) (a )?(?:vaccine|vaccination|immunization)$/,
      /^epi (?:schedule|clinic)$/,
      /^vaccination clinic$/,
    ],
    path: '/clinical/immunizations',
    label: 'Open immunizations',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}antenatal(?: clinic| dashboard)?$`),
      /^anc (?:clinic|dashboard)?$/,
      /^maternity clinic$/,
    ],
    path: '/antenatal',
    label: 'Open antenatal clinic',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}antenatal records?$`),
      /^anc records?$/,
    ],
    path: '/antenatal/records',
    label: 'Open antenatal records',
  },
  {
    patterns: [
      /^(?:new|create|start) (an )?antenatal record$/,
      /^new anc (?:record|booking)$/,
      /^book antenatal$/,
    ],
    path: '/antenatal/records/new',
    label: 'New antenatal record',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:virtual )?clinic$`),
      new RegExp(`^${LEAD}${THE}(?:telemedicine|tele consult|video clinic)$`),
      /^video (?:consults?|consultations?)$/,
      /^(?:join |open )?my (?:virtual )?clinic$/,
      /^join (?:the )?(?:virtual )?clinic$/,
    ],
    path: '/telemedicine',
    label: 'Open virtual clinic',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}ivf(?: clinic| dashboard)?$`),
      /^fertility clinic$/,
    ],
    path: '/ivf',
    label: 'Open IVF clinic',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}ivf (?:cycles|patients|visits)$`)],
    path: '/ivf/cycles',
    label: 'Open IVF cycles',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}lab(?:oratory)?(?: orders)?$`),
      /^(?:order|place|new) labs?$/,
      /^(?:check|view) lab (?:orders|results)$/,
      /^laboratory$/,
    ],
    path: '/lab-orders',
    label: 'Open lab orders',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}lab (?:test )?catalog$`),
      /^lab tests catalog$/,
    ],
    path: '/lab-test-catalog',
    label: 'Open lab test catalog',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}radiology(?: orders)?$`),
      /^(?:order|place|new) (?:x[- ]?ray|imaging|scan|radiology)$/,
      /^imaging orders?$/,
    ],
    path: '/radiology-orders',
    label: 'Open radiology orders',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:pharmacy|prescriptions?)$`),
      /^(?:new|write|create) (a )?prescription$/,
      /^(?:dispense|fill) (?:meds|medications|prescriptions?)?$/,
      /^medication orders?$/,
    ],
    path: '/prescriptions',
    label: 'Open pharmacy / prescriptions',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:drug|drugs)(?: catalog| inventory)?$`),
      /^(?:open |show )?inventory$/,
      /^stock (?:list|levels)$/,
    ],
    path: '/drugs',
    label: 'Open drug catalog',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}nafdac(?: formulary)?$`), /^formulary$/],
    path: '/pharmacy/nafdac-formulary',
    label: 'Open NAFDAC formulary',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}billing(?: queue)?$`),
      new RegExp(`^${LEAD}${THE}pending (?:bills|billing|payments)$`),
      /^cashier queue$/,
    ],
    path: '/billing/pending-queue',
    label: 'Open billing queue',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}payments?$`),
      /^(?:process|take|collect) (a )?payment$/,
      /^payment desk$/,
      /^cash desk$/,
    ],
    path: '/payments',
    label: 'Open payments',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}deferred payments?$`),
      /^payment plans?$/,
    ],
    path: '/billing/deferred-payments',
    label: 'Open deferred payments',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}(?:insurance )?claims?$`), /^hmo claims?$/],
    path: '/billing/claims',
    label: 'Open insurance claims',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}nhia(?: compliance)?$`), /^nhia dashboard$/],
    path: '/billing/nhia-compliance',
    label: 'Open NHIA compliance',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:end of day |eod )?reconciliation$`),
      /^end of day$/,
      /^close (?:the )?till$/,
    ],
    path: '/reconciliation',
    label: 'Open end-of-day reconciliation',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}(?:revenue )?leaks?$`), /^leak detection$/],
    path: '/billing/revenue-leaks',
    label: 'Open revenue leak dashboard',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}(?:bank )?payment reconciliation$`),
      /^bank transfers?$/,
    ],
    path: '/billing/payment-reconciliation',
    label: 'Open payment reconciliation',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}service catalog$`),
      /^price list$/,
      /^billable services$/,
    ],
    path: '/service-catalog',
    label: 'Open service catalog',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}wallet$`), /^patient wallet$/],
    path: '/wallet',
    label: 'Open wallet',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}offline(?: clinic)?(?: queue)?$`),
      /^offline sync$/,
    ],
    path: '/offline/queue',
    label: 'Open offline queue',
  },
  {
    patterns: [
      new RegExp(`^${LEAD}${THE}reports?$`),
      /^clinic reports?$/,
      /^analytics$/,
    ],
    path: '/reports',
    label: 'Open reports',
  },
  {
    patterns: [new RegExp(`^${LEAD}${THE}audit(?: logs?)?$`), /^security log$/],
    path: '/audit-logs',
    label: 'Open audit logs',
  },
];

/** Visit-scoped clinical activities (always confirm). */
const VISIT_ACTIVITY_RULES: Array<{
  patterns: RegExp[];
  buildPath: (id: string) => string;
  label: (id: string) => string;
}> = [
  {
    patterns: [
      /^(?:open |start |go to |begin )?(?:consultation|consult|see (?:the )?doctor|doctor consult)(?: for)?(?: visit)?\s+(\d+)$/,
      /^(?:start |open )?consult(?:ation)? visit\s+(\d+)$/,
      /^chart consult(?:ation)? (?:for )?visit\s+(\d+)$/,
    ],
    buildPath: (id) => `/visits/${id}/consultation`,
    label: (id) => `Open consultation for visit ${id}`,
  },
  {
    patterns: [
      /^(?:open |go to |start )?(?:nurse|nursing|vitals|triage|nursing chart)(?: visit)?(?: for)?(?: visit)?\s+(\d+)$/,
      /^(?:take |record )vitals(?: for)?(?: visit)?\s+(\d+)$/,
      /^nurse visit\s+(\d+)$/,
    ],
    buildPath: (id) => `/visits/${id}/nursing`,
    label: (id) => `Open nursing / vitals for visit ${id}`,
  },
  {
    patterns: [
      /^(?:open |start |go to |join )?(?:telemedicine|video consult|video call|virtual clinic)(?: for)?(?: visit)?\s+(\d+)$/,
      /^(?:start |open )?video (?:visit|consult)(?: for)?(?: visit)?\s+(\d+)$/,
    ],
    buildPath: (id) => `/visits/${id}/telemedicine`,
    label: (id) => `Open virtual clinic for visit ${id}`,
  },
  {
    patterns: [
      /^(?:open |go to |show )?visit\s+(\d+)$/,
      /^(?:open |show )?visit details?(?: for)?\s+(\d+)$/,
      /^patient visit\s+(\d+)$/,
    ],
    buildPath: (id) => `/visits/${id}`,
    label: (id) => `Open visit ${id}`,
  },
];

const PATIENT_HISTORY_RE =
  /^(?:open |show |go to )?(?:medical )?history(?: for)?(?: patient)?\s+(\d+)$/;

const JOIN_CLINIC_ROOM_RE =
  /^(?:join |open )?(?:virtual )?clinic(?: room)?(?: for)?(?: session)?\s+(\d+)$/;

/** Context-aware (no visit id) — resolved with current route visit. */
const CONTEXT_VISIT_RULES: Array<{
  patterns: RegExp[];
  suffix: string;
  label: string;
}> = [
  {
    patterns: [
      /^(?:open |start |go to |begin )?(?:consultation|consult|see (?:the )?doctor)$/,
      /^start consult$/,
    ],
    suffix: '/consultation',
    label: 'Open consultation for this visit',
  },
  {
    patterns: [
      /^(?:open |go to |start )?(?:nursing|vitals|triage)$/,
      /^(?:take |record )vitals$/,
    ],
    suffix: '/nursing',
    label: 'Open nursing / vitals for this visit',
  },
  {
    patterns: [
      /^(?:open |start |join )?(?:video consult|telemedicine|virtual clinic)$/,
      /^start video$/,
    ],
    suffix: '/telemedicine',
    label: 'Open virtual clinic for this visit',
  },
];

const INVITE_STAFF_RE =
  /^(?:invite|call|add|bring in) (?:a |the )?(nurse|specialist|doctor|lab tech|pharmacist|radiology|observer|staff)(?: (?:in|to|into)(?: (?:the )?(?:room|call|clinic))?)?$/;

export const VOICE_COMMAND_EXAMPLES = [
  'Go to dashboard',
  'Register patient',
  'Create visit',
  'Show open visits',
  'Open visit 12',
  'Open visit twelve',
  'Start consultation for visit 12',
  'Take vitals for visit 12',
  'Start video consult for visit 12',
  'Open consultation',
  'Invite nurse',
  'Join my clinic',
  'Open immunizations',
  'Order labs',
  'New prescription',
  'Collect payment',
  'Open virtual clinic',
  'Book appointment',
  'New antenatal record',
  'Start ambient scribe',
  'Generate note',
  'Help',
];

const DOCTOR_ONLY_EXAMPLES = new Set([
  'Register patient',
  'Create visit',
  'Start consultation for visit 12',
  'Start video consult for visit 12',
  'Open consultation',
  'Invite nurse',
  'Start ambient scribe',
  'Generate note',
  'New antenatal record',
]);

const NURSE_FOCUS_EXAMPLES = [
  'Show open visits',
  'Open visit 12',
  'Take vitals for visit 12',
  'Join my clinic',
  'Open immunizations',
  'Open antenatal clinic',
  'Record immunization',
  'Help',
];

export function getVoiceCommandExamplesForRole(role?: string | null): string[] {
  if (!role) return VOICE_COMMAND_EXAMPLES;
  if (role === 'NURSE') {
    return NURSE_FOCUS_EXAMPLES;
  }
  if (role === 'DOCTOR' || role === 'ADMIN' || role === 'IVF_SPECIALIST') {
    return VOICE_COMMAND_EXAMPLES;
  }
  // Other clinical staff: drop doctor-only charting phrases
  return VOICE_COMMAND_EXAMPLES.filter((ex) => !DOCTOR_ONLY_EXAMPLES.has(ex)).concat([
    'Join my clinic',
    'Open lab orders',
    'Help',
  ]);
}

function inviteRoleFromPhrase(roleWord: string): string {
  const r = roleWord.toLowerCase();
  if (r.includes('nurse')) return 'NURSE';
  if (r.includes('doctor') || r.includes('specialist')) return 'DOCTOR';
  if (r.includes('lab')) return 'LAB_TECH';
  if (r.includes('pharm')) return 'PHARMACIST';
  if (r.includes('radio')) return 'RADIOLOGY_TECH';
  if (r.includes('observer')) return 'OBSERVER';
  return 'NURSE';
}

export function parseVoiceIntent(
  utterance: string,
  context: VoiceParseContext = {},
): VoiceIntent {
  const text = normalize(utterance);
  if (!text) {
    return { type: 'unknown', label: 'Empty command', matched: text, requiresConfirm: false };
  }

  if (
    /^(help|what can (i|you) say|show commands|voice help|list commands)$/.test(text)
  ) {
    return { type: 'help', label: 'Show voice commands', matched: text, requiresConfirm: false };
  }

  // —— Ambient scribe ——
  if (
    /^(start |begin )?(ambient )?scribe$/.test(text) ||
    /^(start |begin )ambient( recording| listening)?$/.test(text) ||
    /^start listening$/.test(text) ||
    /^(start |begin )(?:clinical )?dictation$/.test(text)
  ) {
    return {
      type: 'scribe_start',
      label: 'Start ambient scribe',
      matched: text,
      requiresConfirm: false,
    };
  }

  if (
    /^(stop |end |pause )(ambient )?scribe$/.test(text) ||
    /^(stop |end )ambient( recording| listening)?$/.test(text) ||
    /^stop listening$/.test(text) ||
    /^(stop |end )(?:clinical )?dictation$/.test(text)
  ) {
    return {
      type: 'scribe_stop',
      label: 'Stop ambient scribe',
      matched: text,
      requiresConfirm: false,
    };
  }

  if (
    /^(generate|create|make)( a| the)? (clinical )?note$/.test(text) ||
    /^generate scribe$/.test(text) ||
    /^run scribe$/.test(text) ||
    /^scribe (?:the )?note$/.test(text)
  ) {
    return {
      type: 'scribe_generate',
      label: 'Generate clinical note from transcript',
      matched: text,
      requiresConfirm: true,
    };
  }

  if (
    /^(apply|use)( the)? (scribe|note|generated note)$/.test(text) ||
    /^apply to consultation$/.test(text) ||
    /^save (?:the )?scribe$/.test(text)
  ) {
    return {
      type: 'scribe_apply',
      label: 'Apply scribe to consultation',
      matched: text,
      requiresConfirm: true,
    };
  }

  // —— Invite staff into virtual clinic ——
  const inviteMatch = text.match(INVITE_STAFF_RE);
  if (inviteMatch) {
    const inviteRole = inviteRoleFromPhrase(inviteMatch[1]);
    return {
      type: 'clinic_invite',
      inviteRole,
      label: `Invite ${inviteMatch[1]} to virtual clinic`,
      matched: text,
      requiresConfirm: true,
      path: context.visitId
        ? `/visits/${context.visitId}/telemedicine`
        : context.sessionId
          ? `/telemedicine/room/${context.sessionId}`
          : '/telemedicine',
    };
  }

  // —— Context-aware visit actions (current page) ——
  if (context.visitId) {
    for (const rule of CONTEXT_VISIT_RULES) {
      if (rule.patterns.some((re) => re.test(text))) {
        return {
          type: 'navigate',
          path: `/visits/${context.visitId}${rule.suffix}`,
          label: `${rule.label} (#${context.visitId})`,
          matched: text,
          requiresConfirm: true,
        };
      }
    }
    if (/^(?:open |show )?this visit$/.test(text)) {
      return {
        type: 'navigate',
        path: `/visits/${context.visitId}`,
        label: `Open visit ${context.visitId}`,
        matched: text,
        requiresConfirm: false,
      };
    }
  }

  if (context.sessionId && /^(?:join |rejoin |return to )?(?:the )?(?:call|room|clinic)$/.test(text)) {
    return {
      type: 'navigate',
      path: `/telemedicine/room/${context.sessionId}`,
      label: `Return to virtual clinic session ${context.sessionId}`,
      matched: text,
      requiresConfirm: false,
    };
  }

  // —— Visit-scoped clinical activities ——
  for (const rule of VISIT_ACTIVITY_RULES) {
    for (const re of rule.patterns) {
      const m = text.match(re);
      if (m) {
        const id = m[1];
        return {
          type: 'navigate',
          path: rule.buildPath(id),
          label: rule.label(id),
          matched: text,
          requiresConfirm: true,
        };
      }
    }
  }

  const historyMatch = text.match(PATIENT_HISTORY_RE);
  if (historyMatch) {
    const id = historyMatch[1];
    return {
      type: 'navigate',
      path: `/patients/${id}/history`,
      label: `Open medical history for patient ${id}`,
      matched: text,
      requiresConfirm: true,
    };
  }

  const roomMatch = text.match(JOIN_CLINIC_ROOM_RE);
  if (roomMatch) {
    const id = roomMatch[1];
    return {
      type: 'navigate',
      path: `/telemedicine/room/${id}`,
      label: `Join virtual clinic session ${id}`,
      matched: text,
      requiresConfirm: true,
    };
  }

  // —— Global clinic navigation ——
  for (const rule of NAV_RULES) {
    if (rule.patterns.some((re) => re.test(text))) {
      return {
        type: 'navigate',
        path: rule.path,
        label: rule.label,
        matched: text,
        requiresConfirm: false,
      };
    }
  }

  return {
    type: 'unknown',
    label: `Unrecognized: “${utterance.trim()}”`,
    matched: text,
    requiresConfirm: false,
  };
}

export const VOICE_SCRIBE_EVENTS = {
  start: 'emr:voice-scribe-start',
  stop: 'emr:voice-scribe-stop',
  generate: 'emr:voice-scribe-generate',
  apply: 'emr:voice-scribe-apply',
} as const;

export const VOICE_OPEN_INVITE_EVENT = 'emr:voice-open-invite';
export const PENDING_INVITE_STORAGE_KEY = 'emr:pending-clinic-invite-role';

/** Queued when voice scribe is requested off the consultation page. */
export const PENDING_SCRIBE_STORAGE_KEY = 'emr:pending-scribe-action';

export type PendingScribeAction = keyof typeof VOICE_SCRIBE_EVENTS;

export function queuePendingScribeAction(action: PendingScribeAction): void {
  try {
    sessionStorage.setItem(PENDING_SCRIBE_STORAGE_KEY, action);
  } catch {
    // ignore
  }
}

export function consumePendingScribeAction(): PendingScribeAction | null {
  try {
    const raw = sessionStorage.getItem(PENDING_SCRIBE_STORAGE_KEY);
    sessionStorage.removeItem(PENDING_SCRIBE_STORAGE_KEY);
    if (raw && raw in VOICE_SCRIBE_EVENTS) {
      return raw as PendingScribeAction;
    }
  } catch {
    // ignore
  }
  return null;
}

export function queuePendingClinicInvite(role: string): void {
  try {
    sessionStorage.setItem(PENDING_INVITE_STORAGE_KEY, role);
  } catch {
    // ignore
  }
  window.dispatchEvent(
    new CustomEvent(VOICE_OPEN_INVITE_EVENT, { detail: { role } }),
  );
}

export function consumePendingClinicInvite(): string | null {
  try {
    const raw = sessionStorage.getItem(PENDING_INVITE_STORAGE_KEY);
    sessionStorage.removeItem(PENDING_INVITE_STORAGE_KEY);
    return raw;
  } catch {
    return null;
  }
}

export function dispatchScribeVoiceEvent(
  type: keyof typeof VOICE_SCRIBE_EVENTS,
): void {
  window.dispatchEvent(new CustomEvent(VOICE_SCRIBE_EVENTS[type]));
}
