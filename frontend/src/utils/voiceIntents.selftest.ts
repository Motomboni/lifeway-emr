/**
 * Unit-style checks for voice intent parsing.
 */
import {
  parseVoiceIntent,
  wordsToDigits,
  getVoiceCommandExamplesForRole,
} from './voiceIntents';

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

assert(wordsToDigits('visit twelve') === 'visit 12', 'words twelve');
assert(wordsToDigits('visit twenty one') === 'visit 21', 'words 21');

assert(parseVoiceIntent('go to dashboard').type === 'navigate', 'dashboard');
assert(parseVoiceIntent('go to dashboard').path === '/dashboard', 'dashboard path');
assert(parseVoiceIntent('register patient').path === '/patients/register', 'register');
assert(parseVoiceIntent('create visit').path === '/visits/new', 'create visit');
assert(parseVoiceIntent('show open visits').path === '/visits?status=OPEN', 'open visits');
assert(parseVoiceIntent('open visit 42').path === '/visits/42', 'visit detail');
assert(parseVoiceIntent('open visit twelve').path === '/visits/12', 'visit twelve');
assert(
  parseVoiceIntent('start consultation for visit 7').path === '/visits/7/consultation',
  'consult',
);
assert(
  parseVoiceIntent('take vitals for visit 7').path === '/visits/7/nursing',
  'vitals',
);
assert(
  parseVoiceIntent('start video consult for visit 7').path === '/visits/7/telemedicine',
  'video visit',
);
assert(
  parseVoiceIntent('open consultation', { visitId: '9' }).path ===
    '/visits/9/consultation',
  'context consult',
);
assert(
  parseVoiceIntent('invite nurse', { visitId: '9' }).type === 'clinic_invite',
  'invite nurse',
);
assert(parseVoiceIntent('invite nurse').inviteRole === 'NURSE', 'invite role');
assert(parseVoiceIntent('join my clinic').path === '/telemedicine', 'join clinic');
assert(parseVoiceIntent('order labs').path === '/lab-orders', 'labs');
assert(parseVoiceIntent('new prescription').path === '/prescriptions', 'rx');
assert(parseVoiceIntent('collect payment').path === '/payments', 'payment');
assert(parseVoiceIntent('open virtual clinic').path === '/telemedicine', 'clinic');
assert(parseVoiceIntent('book appointment').path === '/appointments', 'appt');
assert(parseVoiceIntent('new antenatal record').path === '/antenatal/records/new', 'anc');
assert(parseVoiceIntent('record immunization').path === '/clinical/immunizations', 'imm');
assert(
  parseVoiceIntent('open medical history for patient 9').path === '/patients/9/history',
  'history',
);
assert(
  parseVoiceIntent('join clinic room 3').path === '/telemedicine/room/3',
  'clinic room',
);
assert(parseVoiceIntent('start ambient scribe').type === 'scribe_start', 'scribe start');
assert(parseVoiceIntent('stop ambient scribe').type === 'scribe_stop', 'scribe stop');
assert(parseVoiceIntent('generate note').requiresConfirm === true, 'generate confirm');
assert(parseVoiceIntent('apply scribe').type === 'scribe_apply', 'apply');
assert(parseVoiceIntent('help').type === 'help', 'help');
assert(parseVoiceIntent('open lab orders').path === '/lab-orders', 'lab path');
assert(parseVoiceIntent('open billing').path === '/billing/pending-queue', 'billing path');
assert(parseVoiceIntent('bananas forever').type === 'unknown', 'unknown');

const nurseHelp = getVoiceCommandExamplesForRole('NURSE');
assert(nurseHelp.some((x) => x.includes('vitals')), 'nurse help vitals');
assert(!nurseHelp.includes('Invite nurse'), 'nurse help no invite');

console.log('voiceIntents.selftest: ok');
