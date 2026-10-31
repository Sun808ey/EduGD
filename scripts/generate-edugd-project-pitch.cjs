const fs = require('fs');
const path = require('path');
const pptxgen = require(path.join(rootForTools(), 'tmp', 'pptx-build', 'node_modules', 'pptxgenjs'));

function rootForTools() { return path.resolve(__dirname, '..'); }

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'output');
const out = path.join(outDir, 'EduGD_Project_Pitch_2026.pptx');
const assets = {
  dashboard: path.join(outDir, 'edugd-pitch-assets', 'dashboard.png'),
  devices: path.join(outDir, 'edugd-pitch-assets', 'devices.png'),
  policies: path.join(outDir, 'edugd-pitch-assets', 'policies.png'),
  reports: path.join(outDir, 'edugd-pitch-assets', 'reports.png'),
  operations: path.join(outDir, 'edugd-pitch-assets', 'operations.png'),
  architecture: path.join(root, 'docs', 'diagrams', 'png', '06-high-level-system-architecture.png'),
  sequence: path.join(root, 'docs', 'diagrams', 'png', '10-sequence-enrollment-offline-policy-sync.png'),
};
for (const file of Object.values(assets)) if (!fs.existsSync(file)) throw new Error(`Missing visual: ${file}`);

const pptx = new pptxgen();
pptx.defineLayout({ name: 'EDUGD_WIDE', width: 13.333, height: 7.5 });
pptx.layout = 'EDUGD_WIDE';
pptx.author = 'EduGD project team';
pptx.company = 'EduGD';
pptx.subject = 'EduGD project-wide pitch';
pptx.title = 'EduGD - From policy to proof';
pptx.lang = 'en-US';
pptx.theme = { headFontFace: 'Aptos Display', bodyFontFace: 'Aptos', lang: 'en-US' };

const C = {
  night: '090D14', panel: '111827', line: '293241', ice: 'EAF2FF', blue: '3B82F6', teal: '12A594', mint: 'B8F2E6',
  white: 'FFFFFF', ink: '112033', muted: '60748A', pale: 'F5F8FC', sky: 'EAF3FF', green: 'E6F7F2', amber: 'FFF4D6', red: 'FCECEF', redInk: 'B83D52', gold: 'C58B1A',
};
const W = 13.333;
const H = 7.5;

function tx(s, value, x, y, w, h, o = {}) {
  s.addText(value, { x, y, w, h, margin: o.margin ?? 0, fontFace: o.fontFace || 'Aptos', fontSize: o.fontSize || 14, bold: o.bold || false, italic: o.italic || false, color: o.color || C.ink, align: o.align || 'left', valign: o.valign || 'mid', fit: 'shrink', breakLine: false, paraSpaceAfterPt: 0, charSpacing: o.charSpacing || 0, isTextBox: true });
}
function box(s, x, y, w, h, fill, border = fill, radius = 0.15) {
  s.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: radius, fill: { color: fill }, line: { color: border, width: 1, transparency: border === fill ? 100 : 0 } });
}
function rule(s, x1, y1, x2, y2, color = C.line, width = 1.2, arrow = 'none') {
  s.addShape(pptx.ShapeType.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width, endArrowType: arrow } });
}
function pill(s, value, x, y, w, fill, color = C.ink) {
  box(s, x, y, w, 0.3, fill, fill, 0.15);
  tx(s, value, x + 0.06, y + 0.04, w - 0.12, 0.2, { fontSize: 8, bold: true, color, align: 'center', charSpacing: 0.5 });
}
function dot(s, x, y, d, fill, label, color = C.white) {
  s.addShape(pptx.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, transparency: 100 } });
  if (label) tx(s, label, x, y + 0.01, d, d - 0.02, { fontSize: 9, bold: true, color, align: 'center' });
}
function image(s, file, x, y, w, h, label) {
  box(s, x + 0.07, y + 0.08, w, h, 'D7E0EA', 'D7E0EA', 0.12);
  s.addImage({ path: file, x, y, w, h });
  s.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: C.white, transparency: 100 }, line: { color: 'B8C8D6', width: 0.7 } });
  if (label) { box(s, x + 0.14, y + 0.14, 1.36, 0.28, C.night, C.night, 0.1); tx(s, label.toUpperCase(), x + 0.22, y + 0.18, 1.2, 0.14, { fontSize: 7, bold: true, color: C.white, align: 'center', charSpacing: 0.7 }); }
}
function header(s, kicker, title, subtitle, page) {
  tx(s, kicker.toUpperCase(), 0.62, 0.34, 4.4, 0.2, { fontSize: 9, bold: true, color: C.teal, charSpacing: 1.6 });
  tx(s, title, 0.62, 0.68, 11.6, 0.58, { fontFace: 'Aptos Display', fontSize: 27, bold: true, color: C.ink });
  tx(s, subtitle, 0.64, 1.35, 11.5, 0.28, { fontSize: 12.2, color: C.muted });
  rule(s, 0.62, 1.78, 12.72, 1.78, C.line, 1);
  tx(s, String(page).padStart(2, '0'), 12.14, 7.14, 0.55, 0.15, { fontSize: 8.5, bold: true, color: C.muted, align: 'right' });
}
function foot(s, textValue = 'EDUGD  /  SCHOOL DEVICE POLICY CONTROL') {
  rule(s, 0.62, 7.04, 12.72, 7.04, C.line, 0.8);
  tx(s, textValue, 0.62, 7.12, 5.8, 0.14, { fontSize: 7.2, bold: true, color: C.muted, charSpacing: 0.9 });
}
function note(s, value) { s.addNotes(value); }

// 1 - opening promise
{
  const s = pptx.addSlide();
  s.background = { color: C.night };
  s.addShape(pptx.ShapeType.arc, { x: 8.7, y: -1.2, w: 6.2, h: 6.2, line: { color: C.blue, transparency: 38, width: 2 }, fill: { color: C.night, transparency: 100 } });
  s.addShape(pptx.ShapeType.arc, { x: 9.8, y: 4.5, w: 3.9, h: 3.9, line: { color: C.teal, transparency: 15, width: 9 }, fill: { color: C.night, transparency: 100 } });
  tx(s, 'EDUGD', 0.72, 0.62, 2.4, 0.24, { fontSize: 11, bold: true, color: C.mint, charSpacing: 2.4 });
  tx(s, 'From policy\nto proof', 0.72, 1.35, 5.3, 1.25, { fontFace: 'Aptos Display', fontSize: 35, bold: true, color: C.white, valign: 'top' });
  tx(s, 'A connected, offline-first control system for school-owned Android devices in Ugandan secondary schools.', 0.75, 2.88, 5.25, 0.75, { fontSize: 16, color: 'C7D6E5', valign: 'top' });
  pill(s, 'ADMIN  /  API  /  DPC  /  EVIDENCE', 0.75, 4.1, 2.55, '17374B', C.mint);
  tx(s, 'Set the rule. Keep it active.\nKnow what happened.', 0.75, 4.82, 4.8, 0.65, { fontSize: 15, bold: true, color: C.white, valign: 'top' });
  box(s, 6.78, 0.88, 5.85, 5.75, '172738', '31526A', 0.22);
  image(s, assets.dashboard, 7.03, 1.12, 5.35, 3.42, 'Authenticated dashboard');
  const metrics = [['2', 'ENROLLED DEVICES', C.mint], ['22', 'DPC VIOLATIONS', 'FFB7C3'], ['0', 'NON-COMPLIANT', C.mint]];
  metrics.forEach(([v, l, col], i) => { const x = 7.03 + i * (5.35 / 3); const w = i === 1 ? 1.96 : 1.53; box(s, x, 4.82, w, 0.98, i === 1 ? '3A2D39' : '203C4C', '203C4C', 0.12); tx(s, v, x + 0.14, 4.96, w - 0.28, 0.3, { fontSize: 23, bold: true, color: col }); tx(s, l, x + 0.14, 5.4, w - 0.28, 0.16, { fontSize: 7.7, bold: true, color: 'C7D6E5' }); });
  tx(s, 'A project-wide view of the operating model', 0.75, 6.72, 5.2, 0.18, { fontSize: 8.5, color: '91A8BC' });
  tx(s, '01', 12.18, 7.14, 0.55, 0.15, { fontSize: 8.5, bold: true, color: C.mint, align: 'right' });
  note(s, 'Open with the product promise. EduGD connects the decision a school administrator makes to the rule a managed Android device applies, then returns privacy-limited evidence that can be reviewed. The dashboard capture is an authenticated view of the current system. It shows two enrolled devices, twenty-two DPC-reported violations, and no non-compliant devices in this captured state. The numbers are not the whole product; they are the visible signal of a larger lifecycle: school setup, enrollment, policy, synchronization, enforcement, and evidence. The narrative is simple: set the right learning conditions, keep them active, and know what happened.');
}

// 2 - problem and solution
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The problem', 'Schools need digital access without losing control.', 'The gap is not only technical. It is operational: clear rules must survive connectivity changes and remain reviewable.', 2);
  box(s, 0.62, 2.08, 5.05, 4.55, C.night, C.night, 0.2);
  tx(s, 'Three sources of uncertainty', 0.96, 2.42, 3.8, 0.3, { fontFace: 'Aptos Display', fontSize: 19, bold: true, color: C.white });
  const risks = [
    ['01', 'Status', 'Which devices are enrolled, synced, compliant, or waiting?'],
    ['02', 'Policy', 'How can staff choose outcomes without package names or manual rules?'],
    ['03', 'Evidence', 'What actually happened when a restricted action was attempted?'],
  ];
  risks.forEach(([n, t, b], i) => { const y = 3.08 + i * 0.88; tx(s, n, 0.98, y, 0.35, 0.18, { fontSize: 9, bold: true, color: C.mint }); tx(s, t, 1.5, y - 0.02, 3.6, 0.22, { fontSize: 13, bold: true, color: C.white }); tx(s, b, 1.5, y + 0.28, 3.76, 0.35, { fontSize: 9.4, color: 'B8CADB', valign: 'top' }); });
  tx(s, 'Manual follow-up turns every exception into a conversation.', 0.96, 6.1, 4.1, 0.25, { fontSize: 10.5, bold: true, color: 'FFB7C3' });
  box(s, 6.05, 2.08, 6.68, 4.55, C.white, C.line, 0.2);
  tx(s, 'EduGD solves the control gap with one connected path', 6.4, 2.42, 5.75, 0.3, { fontFace: 'Aptos Display', fontSize: 19, bold: true, color: C.ink });
  const solve = [
    ['Central view', 'School profile, devices, policies, assignments, provisioning, violations, and audit in one admin shell.', C.sky, C.blue],
    ['Local continuity', 'The DPC keeps the last approved policy active while offline and stores evidence for later sync.', C.green, C.teal],
    ['Accountable record', 'Versioned revisions, acknowledgements, violations, hashes, and redacted audit events.', C.amber, C.gold],
  ];
  solve.forEach(([t, b, fill, accent], i) => { const y = 3.08 + i * 0.94; box(s, 6.38, y, 5.98, 0.7, fill, fill, 0.12); dot(s, 6.62, y + 0.18, 0.3, accent, ''); tx(s, t, 7.08, y + 0.13, 1.55, 0.2, { fontSize: 11, bold: true, color: C.ink }); tx(s, b, 8.68, y + 0.11, 3.35, 0.35, { fontSize: 8.6, color: C.muted, valign: 'top' }); });
  pill(s, 'SCHOOL-OWNED  /  FULLY MANAGED', 6.42, 6.02, 2.5, C.night, C.white);
  tx(s, 'Designed for a non-technical school administrator.', 9.12, 6.08, 3.1, 0.18, { fontSize: 9.3, bold: true, color: C.teal });
  foot(s);
  note(s, 'Frame the problem in the language of the people who operate a school. Staff need a reliable view of device status, a clear way to define rules, and evidence when something is blocked or fails. The solution is not a larger manual checklist. EduGD reduces uncertainty through a central administrator view, local continuity on the device, and an accountable record. The scope is intentionally focused on school-owned and fully managed Android devices; the system is not a BYOD or consumer parental-control product.');
}

// 3 - complete lifecycle
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The lifecycle', 'One rule travels from school intent to device evidence.', 'The complete process is visible from setup through enforcement, recovery, and review.', 3);
  const steps = [
    ['1', 'Set up school', 'Edit the school profile and select the timetable timezone.', C.blue],
    ['2', 'Enroll device', 'DPC identity and Android details are fetched during provisioning.', C.teal],
    ['3', 'Build policy', 'Choose apps, domains, restrictions, and time-based modes.', C.gold],
    ['4', 'Deliver revision', 'Assign an immutable revision and track device acknowledgement.', C.blue],
    ['5', 'Enforce offline', 'Keep the last valid policy active and queue local events.', C.teal],
    ['6', 'Review evidence', 'Sync violations, compliance, audit, and recovery outcomes.', C.redInk],
  ];
  steps.forEach(([n, t, b, accent], i) => { const x = 0.63 + i * 2.08; box(s, x, 2.1, 1.78, 1.62, C.white, C.line, 0.14); dot(s, x + 0.16, 2.28, 0.34, accent, n); tx(s, t, x + 0.16, 2.78, 1.45, 0.22, { fontSize: 11, bold: true, color: C.ink }); tx(s, b, x + 0.16, 3.1, 1.45, 0.42, { fontSize: 8.2, color: C.muted, valign: 'top' }); if (i < steps.length - 1) rule(s, x + 1.78, 2.9, x + 2.02, 2.9, C.teal, 1.5, 'triangle'); });
  box(s, 0.63, 4.17, 7.35, 2.15, C.night, C.night, 0.18);
  tx(s, 'When connectivity drops', 0.96, 4.5, 2.55, 0.25, { fontFace: 'Aptos Display', fontSize: 18, bold: true, color: C.white });
  const offline = [['KEEP', 'last valid policy'], ['APPLY', 'rules on device'], ['QUEUE', 'privacy-limited events'], ['RECONNECT', 'sync and acknowledge']];
  offline.forEach(([a, b], i) => { const x = 0.98 + i * 1.72; dot(s, x, 5.18, 0.3, i === 3 ? C.teal : C.blue, String(i + 1)); tx(s, a, x + 0.42, 5.19, 1.08, 0.16, { fontSize: 8.5, bold: true, color: C.mint }); tx(s, b, x + 0.42, 5.47, 1.2, 0.28, { fontSize: 8.8, color: 'C7D6E5', valign: 'top' }); });
  image(s, assets.sequence, 8.22, 4.17, 4.42, 2.15, 'Lifecycle sequence');
  foot(s, 'EDUGD  /  COMPLETE PROCESS LIFECYCLE');
  note(s, 'This is the core process lifecycle. The school profile establishes the human and timetable context. Provisioning creates the device record from the Android DPC rather than asking an administrator to type device identity. Policy management uses plain-language catalogue choices, schedules, and restrictions. A stable policy identity can have immutable revisions, and assignments point to an exact revision. The DPC applies the signed state locally, continues with the last valid policy when offline, queues relevant evidence, and synchronises when connectivity returns. The final step is review: the school sees acknowledgement, compliance, violations, and audit evidence. The sequence diagram is a repository visual; the six-step path is the project-wide operating model.');
}

// 4 - project-wide architecture
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The system', 'Five connected layers make the workflow dependable.', 'The product is an integrated frontend, backend, data, Android, and governance system rather than a standalone screen.', 4);
  image(s, assets.architecture, 0.62, 2.06, 7.28, 3.2, 'Repository architecture');
  const layers = [
    ['Admin experience', 'React + TypeScript shell, route-level workflows, dark/light mode, responsive forms, and documentation assistant.', C.sky, C.blue],
    ['Application services', 'Flask API, authentication, permission checks, policy validation, enrollment, assignments, and reporting.', C.green, C.teal],
    ['Trusted state', 'PostgreSQL system of record, immutable revisions, audit chain heads, and privacy-minimised evidence.', C.amber, C.gold],
    ['Operational resilience', 'Redis-backed controls, offline queue, retryable synchronization, health/readiness, and staging gates.', C.red, C.redInk],
    ['Managed device', 'Android DPC identity, signed policy verification, local enforcement, check-in, and device evidence.', C.night, C.white],
  ];
  layers.forEach(([t, b, fill, accent], i) => { const y = 2.06 + i * 0.9; box(s, 8.2, y, 4.48, 0.72, fill, fill, 0.11); tx(s, t, 8.45, y + 0.12, 1.42, 0.18, { fontSize: 10.5, bold: true, color: fill === C.night ? C.white : C.ink }); tx(s, b, 9.94, y + 0.1, 2.45, 0.36, { fontSize: 8.1, color: fill === C.night ? 'C7D6E5' : C.muted, valign: 'top' }); });
  pill(s, 'FRONTEND', 0.74, 5.65, 0.92, C.sky, C.blue); pill(s, 'FLASK API', 1.78, 5.65, 0.9, C.green, C.teal); pill(s, 'POSTGRES', 2.8, 5.65, 0.98, C.amber, C.gold); pill(s, 'REDIS', 3.9, 5.65, 0.62, C.red, C.redInk); pill(s, 'ANDROID DPC', 4.68, 5.65, 1.2, C.night, C.white);
  tx(s, 'The dashboard is the control surface. Enforcement remains on the managed device.', 0.74, 6.15, 6.35, 0.3, { fontSize: 11, bold: true, color: C.teal });
  foot(s, 'EDUGD  /  FRONTEND  -  API  -  DATA  -  DPC  -  GOVERNANCE');
  note(s, 'Explain the project as a system of connected layers. The administrator frontend is responsible for clarity, navigation, forms, status, and documentation guidance. The Flask API is the policy and authorization boundary. PostgreSQL is the authoritative system of record for device, policy, assignment, enrollment, and evidence state. Redis supports operational controls such as rate limiting. The Android DPC is the enforcement boundary: it verifies and applies device policy locally and reports state back. The design also includes health and readiness checks, offline queues, retries, staging gates, and redacted audit records. This is why the project is more than a dashboard: the dashboard is the control surface for a lifecycle spanning school, service, and device.');
}

// 5 - admin experience
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The experience', 'A non-technical administrator can operate the whole day.', 'Live captures show the navigation, device register, and policy management surface built around plain-language choices.', 5);
  image(s, assets.devices, 0.62, 2.03, 4.05, 2.55, 'Devices');
  image(s, assets.policies, 4.77, 2.03, 4.05, 2.55, 'Policies');
  image(s, assets.reports, 8.92, 2.03, 3.8, 2.55, 'Violations');
  const items = [
    ['School profile', 'Editable school details with an admin-selected timetable timezone.', C.sky, C.blue],
    ['Policy management', 'Dropdown catalogue for blocked/approved apps and domains, schedules, preview, revisions, and assignments.', C.green, C.teal],
    ['Device and evidence', 'DPC-fetched identity, enrollment state, sync acknowledgement, compliance, violations, and audit filters.', C.amber, C.gold],
  ];
  items.forEach(([t, b, fill, accent], i) => { const x = 0.62 + i * 4.05; box(s, x, 4.92, 3.78, 1.28, fill, fill, 0.13); dot(s, x + 0.22, 5.16, 0.27, accent, ''); tx(s, t, x + 0.63, 5.08, 2.72, 0.2, { fontSize: 11.5, bold: true, color: C.ink }); tx(s, b, x + 0.22, 5.47, 3.25, 0.45, { fontSize: 9.1, color: C.muted, valign: 'top' }); });
  pill(s, 'CHOOSE INTENT', 0.68, 6.48, 1.25, C.night, C.white); tx(s, 'The platform turns simple choices into signed, versioned, device-enforceable state.', 2.12, 6.54, 8.8, 0.18, { fontSize: 10.2, bold: true, color: C.teal });
  foot(s, 'EDUGD  /  LIVE AUTHENTICATED DASHBOARD CAPTURES');
  note(s, 'This slide makes the product tangible. The live dashboard shows a consistent side menu and control-room language. The devices view keeps identity and Android details tied to DPC records. The policy view shows class-time and exam-mode policies with immutable revisions. The operations view connects the lifecycle for an administrator who should not need to understand the internal service boundaries. The key UX decision is to let administrators choose intent: select an application or domain from a catalogue, choose a time-based mode, preview the plain-language effect, and let the backend produce the signed revision. The platform handles technical identifiers, permissions, synchronization states, and evidence.');
}

// 6 - trust and proof
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The proof', 'Trust is designed into the operating record.', 'EduGD separates what the device observed, what the service accepted, and what the administrator is allowed to see.', 6);
  image(s, assets.reports, 0.62, 2.05, 6.62, 3.85, 'DPC-recorded violations');
  box(s, 7.56, 2.05, 5.16, 3.85, C.white, C.line, 0.18);
  tx(s, 'Evidence and quality gates', 7.92, 2.38, 4.2, 0.28, { fontFace: 'Aptos Display', fontSize: 18, bold: true, color: C.ink });
  const proof = [
    ['SIGNED STATE', 'Policies are versioned and verified before device application.', C.sky, C.blue],
    ['PRIVACY LIMIT', 'Evidence excludes private messages, photos, contacts, location, microphone, and learner content.', C.green, C.teal],
    ['FORENSIC TRACE', 'Hash-linked sequences connect violations, synchronisation, assignments, and audit events.', C.amber, C.gold],
    ['ASSISTED CLARITY', 'The assistant answers the attached 180-question knowledge base and cannot change records.', C.red, C.redInk],
  ];
  proof.forEach(([t, b, fill, accent], i) => { const y = 2.9 + i * 0.67; box(s, 7.9, y, 4.48, 0.49, fill, fill, 0.1); tx(s, t, 8.08, y + 0.08, 1.12, 0.15, { fontSize: 7.7, bold: true, color: accent }); tx(s, b, 9.34, y + 0.06, 2.82, 0.28, { fontSize: 8.1, color: C.muted, valign: 'top' }); });
  box(s, 0.62, 6.15, 12.1, 0.56, C.night, C.night, 0.12);
  tx(s, 'Validated in layers: Android logic  |  Flask contracts  |  database migrations  |  frontend tests  |  browser workflow  |  staging-first release gates', 0.9, 6.34, 11.5, 0.18, { fontSize: 9.4, bold: true, color: C.white, align: 'center' });
  foot(s, 'EDUGD  /  EVIDENCE, PRIVACY, ASSISTANCE, QUALITY');
  note(s, 'The violation report shows why evidence matters. A school needs to understand the device, policy context, outcome, time, and evidence identifier without collecting private learner content. The platform uses signed policy state, immutable revisions, device acknowledgements, hash-linked event sequences, permission checks, rate limiting, and redacted logs. The in-dashboard assistant is deliberately bounded: it answers the attached 180-question reference and explains documented workflows, but it cannot approve, publish, assign, revoke, delete, create, edit, apply, or change records. Quality is layered across Android, backend, database, frontend, browser workflows, and staging release gates.');
}

// 7 - rollout and ask
{
  const s = pptx.addSlide();
  s.background = { color: C.night };
  s.addShape(pptx.ShapeType.arc, { x: -0.8, y: 4.75, w: 4.4, h: 4.4, rotate: 188, line: { color: C.teal, transparency: 14, width: 10 }, fill: { color: C.night, transparency: 100 } });
  s.addShape(pptx.ShapeType.arc, { x: 10.4, y: -0.7, w: 4.2, h: 4.2, rotate: 12, line: { color: C.blue, transparency: 18, width: 9 }, fill: { color: C.night, transparency: 100 } });
  tx(s, 'THE PATH FORWARD', 0.72, 0.62, 3.6, 0.22, { fontSize: 10, bold: true, color: C.mint, charSpacing: 2 });
  tx(s, 'Start with one class.\nScale with evidence.', 0.72, 1.32, 6.1, 1.0, { fontFace: 'Aptos Display', fontSize: 31, bold: true, color: C.white, valign: 'top' });
  tx(s, 'The responsible next step is a supervised staging pilot with physical Android verification before wider rollout.', 0.75, 2.72, 5.6, 0.58, { fontSize: 15, color: 'C7D6E5', valign: 'top' });
  const plan = [
    ['01', 'Validate', 'Complete physical DPC, offline, recovery, and device-owner checks.'],
    ['02', 'Pilot', 'Enroll one approved class and measure administration, sync, and evidence.'],
    ['03', 'Review', 'Use violations, compliance, audit, and school feedback to improve.'],
    ['04', 'Expand', 'Scale only when reliability, privacy, and governance evidence is strong.'],
  ];
  plan.forEach(([n, t, b], i) => { const y = 4.0 + i * 0.56; tx(s, n, 0.76, y, 0.35, 0.17, { fontSize: 9, bold: true, color: C.mint }); tx(s, t, 1.34, y - 0.02, 1.05, 0.2, { fontSize: 11.5, bold: true, color: C.white }); tx(s, b, 2.35, y, 4.05, 0.2, { fontSize: 9.2, color: 'AFC3D5' }); });
  box(s, 7.08, 1.05, 5.52, 4.98, '172738', '31526A', 0.22);
  image(s, assets.dashboard, 7.3, 1.28, 5.08, 2.9, 'Control room');
  tx(s, 'Safer learning.\nSimpler administration.\nEvidence when it matters.', 7.34, 4.6, 4.9, 0.82, { fontFace: 'Aptos Display', fontSize: 19, bold: true, color: C.white, valign: 'top' });
  pill(s, 'STAGING FIRST', 7.34, 5.72, 1.15, '204B59', C.mint);
  tx(s, 'Production is outside this pitch scope.', 8.68, 5.79, 3.2, 0.16, { fontSize: 8.8, color: 'AFC3D5' });
  tx(s, '07', 12.18, 7.14, 0.55, 0.15, { fontSize: 8.5, bold: true, color: C.mint, align: 'right' });
  note(s, 'Close with a measured adoption path. The software now expresses the full operating lifecycle, but physical DPC behavior and field conditions still deserve direct evidence. The next step is a supervised staging pilot with one approved class and real school-owned Android devices. Measure enrollment, policy application, offline continuity, synchronization recovery, violation evidence, administrator effort, and privacy experience. Expand only when the evidence is strong enough. The central takeaway is that EduGD turns a school policy into a repeatable operating habit: safer learning conditions, simpler administration, and evidence when it matters.');
}

(async () => {
  await pptx.writeFile({ fileName: out });
  console.log(`DECK: ${out}`);
  console.log(`SLIDES: ${pptx._slides.length}`);
  console.log(`BYTES: ${fs.statSync(out).size}`);
})();
