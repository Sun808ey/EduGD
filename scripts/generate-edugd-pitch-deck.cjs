const fs = require('fs');
const path = require('path');
const pptxgen = require(path.join(process.env.TEMP, 'edugd-pptx-tools', 'node_modules', 'pptxgenjs'));

const root = path.resolve(__dirname, '..');
const assetDir = path.join(root, 'output', 'edugd-pitch-assets');
const output = path.join(root, 'output', 'edugd-pitch-deck.pptx');
const assets = {
  dashboard: path.join(assetDir, 'dashboard.png'),
  devices: path.join(assetDir, 'devices.png'),
  policies: path.join(assetDir, 'policies.png'),
  reports: path.join(assetDir, 'reports.png'),
};
for (const [name, file] of Object.entries(assets)) {
  if (!fs.existsSync(file)) throw new Error(`Missing live dashboard snapshot: ${name}`);
}

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'EduGD';
pptx.company = 'EduGD';
pptx.subject = 'School device policy management';
pptx.title = 'EduGD — From device uncertainty to accountable learning';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Aptos Display',
  bodyFontFace: 'Aptos',
  lang: 'en-US',
};
pptx.defineLayout({ name: 'EDUGD_WIDE', width: 13.333, height: 7.5 });
pptx.layout = 'EDUGD_WIDE';
pptx.margin = 0;

const C = {
  ink: '0B1320', navy: '102236', teal: '0E8179', tealDark: '08655F', blue: '2F8DFF', ice: 'F5F8FC', panel: 'FFFFFF', line: 'D8E2EA', muted: '5C7186', red: 'D94D61', amber: 'E0A52D', green: '28A878', white: 'FFFFFF', paleTeal: 'E6F5F2', paleBlue: 'EAF3FF', paleRed: 'FCECEF', paleAmber: 'FFF5DD',
};
const W = 13.333;
const H = 7.5;

function rect(slide, x, y, w, h, fill, radius = 0.16, line = fill) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: radius, fill: { color: fill }, line: { color: line, transparency: 100 } });
}
function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, { x, y, w, h, margin: 0, fontFace: opts.fontFace || 'Aptos', fontSize: opts.fontSize || 16, bold: opts.bold || false, color: opts.color || C.ink, breakLine: false, fit: 'shrink', valign: opts.valign || 'mid', align: opts.align || 'left', paraSpaceAfterPt: 0, charSpacing: opts.charSpacing || 0, italic: opts.italic || false, bullet: opts.bullet, transparency: opts.transparency, isTextBox: true });
}
function line(slide, x1, y1, x2, y2, color = C.line, width = 1.2, dash = 'solid') {
  slide.addShape(pptx.ShapeType.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width, dashType: dash, beginArrowType: 'none', endArrowType: 'none' } });
}
function header(slide, kicker, title, subtitle) {
  text(slide, kicker.toUpperCase(), 0.62, 0.38, 4.6, 0.23, { fontSize: 9, bold: true, color: C.teal, charSpacing: 2.1 });
  text(slide, title, 0.62, 0.72, 8.5, 0.58, { fontSize: 27, bold: true, color: C.ink });
  if (subtitle) text(slide, subtitle, 0.64, 1.38, 8.7, 0.34, { fontSize: 11.5, color: C.muted });
}
function footer(slide, n) {
  line(slide, 0.62, 7.12, 12.72, 7.12, C.line, 0.8);
  text(slide, 'EDUGD  /  SCHOOL DEVICE POLICY CONTROL', 0.62, 7.19, 4.8, 0.16, { fontSize: 7.5, bold: true, color: C.muted, charSpacing: 1.1 });
  text(slide, String(n).padStart(2, '0'), 12.18, 7.16, 0.54, 0.2, { fontSize: 8.5, bold: true, color: C.teal, align: 'right' });
}
function notes(slide, value) { slide.addNotes(value); }
function screenshot(slide, file, x, y, w, h, label) {
  rect(slide, x + 0.08, y + 0.1, w, h, 'D5DEE8', 0.13);
  slide.addImage({ path: file, x, y, w, h });
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: 'FFFFFF', transparency: 100 }, line: { color: 'BFCEDB', width: 0.7 } });
  if (label) {
    rect(slide, x + 0.16, y + 0.16, 1.35, 0.29, C.ink, 0.12);
    text(slide, label.toUpperCase(), x + 0.27, y + 0.2, 1.12, 0.15, { fontSize: 7, bold: true, color: C.white, charSpacing: 1 });
  }
}
function pill(slide, value, x, y, w, fill, color = C.ink) {
  rect(slide, x, y, w, 0.31, fill, 0.15);
  text(slide, value, x + 0.12, y + 0.055, w - 0.24, 0.16, { fontSize: 8.2, bold: true, color, align: 'center' });
}
function bullet(slide, title, body, x, y, accent = C.teal, width = 3.8) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y: y + 0.03, w: 0.18, h: 0.18, fill: { color: accent }, line: { color: accent, transparency: 100 } });
  text(slide, title, x + 0.31, y, width - 0.31, 0.23, { fontSize: 13, bold: true, color: C.ink });
  text(slide, body, x + 0.31, y + 0.28, width - 0.31, 0.45, { fontSize: 10.2, color: C.muted, valign: 'top' });
}
function metric(slide, value, label, x, y, w, fill, accent) {
  rect(slide, x, y, w, 0.98, fill, 0.15);
  text(slide, value, x + 0.2, y + 0.14, w - 0.4, 0.33, { fontSize: 24, bold: true, color: accent });
  text(slide, label, x + 0.2, y + 0.58, w - 0.4, 0.2, { fontSize: 8.7, bold: true, color: C.muted });
}
function flow(slide, num, title, body, x, y, accent) {
  rect(slide, x, y, 1.76, 1.22, C.panel, 0.16, C.line);
  slide.addShape(pptx.ShapeType.ellipse, { x: x + 0.14, y: y + 0.14, w: 0.31, h: 0.31, fill: { color: accent }, line: { color: accent, transparency: 100 } });
  text(slide, String(num), x + 0.14, y + 0.19, 0.31, 0.15, { fontSize: 8.5, bold: true, color: C.white, align: 'center' });
  text(slide, title, x + 0.14, y + 0.55, 1.48, 0.22, { fontSize: 11, bold: true, color: C.ink });
  text(slide, body, x + 0.14, y + 0.83, 1.46, 0.26, { fontSize: 8.2, color: C.muted, valign: 'top' });
}

// 1 — Opening promise
{
  const s = pptx.addSlide();
  s.background = { color: C.ink };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.ink }, line: { color: C.ink, transparency: 100 } });
  s.addShape(pptx.ShapeType.arc, { x: 8.3, y: -1.5, w: 6.6, h: 6.6, adjustPoint: 0.25, line: { color: C.teal, transparency: 62, width: 1.2 }, fill: { color: C.ink, transparency: 100 } });
  text(s, 'EDUGD', 0.72, 0.64, 2.2, 0.28, { fontSize: 12, bold: true, color: C.teal, charSpacing: 2.8 });
  text(s, 'From device uncertainty\nto accountable learning', 0.72, 1.52, 6.2, 1.35, { fontSize: 31, bold: true, color: C.white, valign: 'top' });
  text(s, 'Offline-first policy enforcement for school-owned Android devices in Ugandan secondary schools.', 0.75, 3.14, 5.5, 0.62, { fontSize: 16, color: 'C7D6E5', valign: 'top' });
  pill(s, 'SCHOOL DEVICE POLICY CONTROL', 0.75, 4.2, 2.66, '17374B', 'A9E9DE');
  text(s, 'The administrator sees the signal.\nThe device policy controller does the work.', 0.75, 5.1, 5.3, 0.62, { fontSize: 14, color: C.white, bold: true, valign: 'top' });
  rect(s, 7.06, 1.0, 5.62, 4.82, '172738', 0.22);
  screenshot(s, assets.dashboard, 7.28, 1.22, 5.18, 3.24, 'Live dashboard');
  metric(s, '2', 'ENROLLED DEVICES', 7.28, 4.72, 1.52, '203C4C', '9EE9D6');
  metric(s, '22', 'DPC-REPORTED VIOLATIONS', 8.94, 4.72, 1.98, '3A2D39', 'FFB7C3');
  metric(s, '0', 'NON-COMPLIANT DEVICES', 11.04, 4.72, 1.42, '203C4C', '9EE9D6');
  text(s, 'A pitch for a calmer, more accountable school day', 0.75, 6.74, 5.8, 0.2, { fontSize: 9, color: '91A8BC' });
  text(s, '01', 12.18, 7.12, 0.54, 0.2, { fontSize: 8.5, bold: true, color: '7CE3D3', align: 'right' });
  notes(s, 'Open with the promise and the scope. EduGD is an academic proof-of-concept for offline-first policy enforcement on school-owned Android devices in Ugandan secondary schools. It is not another complicated technology layer for teachers. It is a control surface that turns devices into a visible, policy-driven learning environment. Point to the live dashboard snapshot. In this captured state, administrators can see two enrolled devices, twenty-two DPC-reported violations, and no devices currently marked non-compliant. The story is simple: schools need a way to set the right learning conditions and know what actually happened. EduGD connects that decision to the device and returns accountable evidence.');
}

// 2 — Problem
{
  const s = pptx.addSlide();
  s.background = { color: C.ice };
  header(s, 'The problem', 'Rules exist. Visibility does not.', 'Schools are asked to protect learning time with fragmented tools, manual follow-up, and incomplete device context.');
  rect(s, 0.62, 2.05, 5.05, 4.62, C.navy, 0.2);
  text(s, 'The cost of uncertainty', 0.95, 2.44, 3.7, 0.3, { fontSize: 19, bold: true, color: C.white });
  text(s, 'When a device drifts away from the intended learning environment, the school should not have to guess.', 0.95, 2.92, 4.02, 0.75, { fontSize: 14, color: 'C8D8E8', valign: 'top' });
  const issues = [
    ['01', 'Unknown device status', 'Who is enrolled, synced, or waiting for action?'],
    ['02', 'Manual policy translation', 'Teachers should choose outcomes—not package names.'],
    ['03', 'Opaque incidents', 'A block without evidence creates follow-up work and doubt.'],
  ];
  issues.forEach(([num, title, body], i) => {
    const y = 4.12 + i * 0.76;
    text(s, num, 0.96, y, 0.36, 0.18, { fontSize: 9, bold: true, color: '79D6C9' });
    text(s, title, 1.46, y - 0.03, 3.7, 0.22, { fontSize: 12, bold: true, color: C.white });
    text(s, body, 1.46, y + 0.24, 3.8, 0.26, { fontSize: 9.2, color: 'AFC3D5', valign: 'top' });
  });
  screenshot(s, assets.reports, 6.08, 2.05, 6.62, 4.14, 'Current state');
  rect(s, 6.35, 6.34, 6.08, 0.34, C.paleRed, 0.14);
  text(s, 'Without a trusted evidence trail, every exception becomes a conversation instead of a signal.', 6.54, 6.43, 5.68, 0.15, { fontSize: 8.6, bold: true, color: C.red });
  footer(s, 2);
  notes(s, 'Make the problem human. Teachers and school administrators are not trying to become device engineers. They need to know which devices are ready, which policies are active, and what happened when a restricted action was attempted. Today, that information is often scattered across settings, spreadsheets, and manual reports. This creates three kinds of uncertainty: status uncertainty, policy complexity, and evidence gaps. The live violation report shows the kind of evidence a school needs: the device, class, policy, rule, outcome, and chain evidence—without exposing private device content.');
}

// 3 — Project-wide architecture
{
  const s = pptx.addSlide();
  s.background = { color: C.ice };
  header(s, 'The solution', 'One product. Five connected layers.', 'EduGD joins the administrator experience, policy service, trusted data, Android control, and secure operations.');
  rect(s, 0.7, 2.0, 11.94, 0.63, C.navy, 0.15);
  text(s, 'ADMINISTRATOR', 0.98, 2.19, 1.52, 0.18, { fontSize: 9, bold: true, color: '9EE9D6', charSpacing: 1.2 });
  text(s, 'sets intent', 2.7, 2.19, 1.0, 0.18, { fontSize: 9, color: 'C7D6E5' });
  text(s, 'REACT + TYPESCRIPT DASHBOARD', 4.0, 2.19, 2.45, 0.18, { fontSize: 9, bold: true, color: 'A9CFFF', charSpacing: .8 });
  text(s, 'REST / HTTPS', 7.02, 2.19, 1.0, 0.18, { fontSize: 9, color: 'C7D6E5' });
  text(s, 'FLASK API', 8.4, 2.19, 1.0, 0.18, { fontSize: 9, bold: true, color: 'A9CFFF', charSpacing: 1 });
  text(s, 'authorises', 9.65, 2.19, 1.0, 0.18, { fontSize: 9, color: 'C7D6E5' });
  text(s, 'ANDROID DPC', 11.02, 2.19, 1.2, 0.18, { fontSize: 9, bold: true, color: 'FFB7C3', charSpacing: 1 });
  line(s, 1.5, 2.63, 1.5, 2.92, '8CA3B8', 1.2);
  line(s, 6.66, 2.63, 6.66, 2.92, '8CA3B8', 1.2);
  line(s, 11.65, 2.63, 11.65, 2.92, '8CA3B8', 1.2);
  const layers = [
    ['Policy and identity', 'Versioned policies · schedules · enrollment credentials', C.paleBlue, C.blue],
    ['Trusted data', 'Supabase PostgreSQL · immutable revisions · audit chain heads', C.paleTeal, C.teal],
    ['Resilient operations', 'Redis rate limiting · offline queue · retryable synchronization', C.paleAmber, C.amber],
  ];
  layers.forEach(([title, body, fill, accent], i) => {
    const x = 0.7 + i * 4.1;
    rect(s, x, 3.03, 3.74, 1.2, fill, 0.16);
    text(s, title, x + 0.22, 3.28, 3.22, 0.23, { fontSize: 13, bold: true, color: C.ink });
    text(s, body, x + 0.22, 3.63, 3.2, 0.33, { fontSize: 9.3, color: C.muted, valign: 'top' });
    line(s, x + 0.22, 4.06, x + 1.04, 4.06, accent, 2.4);
  });
  screenshot(s, assets.devices, 0.7, 4.62, 6.02, 1.86, 'Live device register');
  rect(s, 7.02, 4.62, 5.62, 1.86, C.panel, 0.18, C.line);
  text(s, 'The connected outcome', 7.36, 4.94, 3.2, 0.25, { fontSize: 17, bold: true, color: C.ink });
  text(s, 'A school rule travels through the system as a signed, versioned decision, is enforced offline on the device, and returns as privacy-limited evidence.', 7.36, 5.36, 4.78, 0.55, { fontSize: 11, color: C.muted, valign: 'top' });
  pill(s, 'FRONTEND', 7.36, 6.08, 0.92, C.paleBlue, C.blue);
  pill(s, 'BACKEND', 8.42, 6.08, 0.92, C.paleTeal, C.tealDark);
  pill(s, 'DPC', 9.48, 6.08, 0.62, C.paleRed, C.red);
  pill(s, 'EVIDENCE', 10.25, 6.08, 0.94, C.paleAmber, '9A6A00');
  footer(s, 3);
  notes(s, 'This is the project-wide architecture in plain language. The administrator uses the React and TypeScript dashboard to set intent. The Flask API authenticates and authorises each operation, stores versioned policy and device state in Supabase PostgreSQL, and uses Redis for rate limiting and operational resilience. The Android DPC receives signed state, applies it locally, and continues enforcing the last verified policy when connectivity is unavailable. The important point is the connection across layers: a school decision becomes a controlled device action and returns as privacy-limited evidence. The live device register is proof that the administrator surface is connected to device records and policy state.');
}

// 4 — Policy simplicity
{
  const s = pptx.addSlide();
  s.background = { color: C.ice };
  header(s, 'The experience', 'Teachers choose outcomes. EduGD handles the complexity.', 'Plain-language policy choices make consistent enforcement possible without technical package names.');
  screenshot(s, assets.policies, 0.62, 2.0, 7.05, 4.42, 'Policy management');
  rect(s, 8.04, 2.0, 4.66, 4.42, C.navy, 0.2);
  text(s, 'Policy building blocks', 8.42, 2.42, 3.6, 0.3, { fontSize: 18, bold: true, color: C.white });
  pill(s, 'CLASS TIME POLICY', 8.42, 2.98, 1.68, '204B59', '9EE9D6');
  pill(s, 'EXAM MODE POLICY', 10.22, 2.98, 1.62, '28405C', 'A9CFFF');
  bullet(s, 'Applications and domains', 'Choose blocked and approved learning categories from the catalogue.', 8.42, 3.58, '79D6C9', 3.72);
  bullet(s, 'Time-based controls', 'Class time, exam mode, screen time, lock-task, and network rules.', 8.42, 4.37, C.blue, 3.72);
  bullet(s, 'Safe delivery', 'Signed revisions support apply, clear, rollback, blocked, and offline states.', 8.42, 5.16, C.amber, 3.72);
  text(s, 'The admin chooses the intent. The DPC receives the enforceable policy.', 8.42, 6.03, 3.72, 0.26, { fontSize: 9.5, bold: true, color: 'AFC3D5', valign: 'top' });
  footer(s, 4);
  notes(s, 'This slide is about lowering the cognitive load while showing the breadth of the policy engine. An administrator can choose application and domain outcomes from a catalogue, define time-based modes, set screen-time and lock-task behavior, and include network or device restrictions. The backend publishes immutable revisions, and the DPC receives a signed operation: apply, no change, clear, rollback, or blocked. Offline enforcement keeps the last verified policy active rather than silently dropping protection. The live policy snapshot shows active policies with clear versions and update times.');
}

// 5 — Evidence and trust
{
  const s = pptx.addSlide();
  s.background = { color: C.ice };
  header(s, 'The proof', 'A violation becomes accountable evidence—not a mystery.', 'EduGD combines privacy-limited evidence, signed state, least privilege, and forensic traceability.');
  screenshot(s, assets.reports, 0.62, 1.98, 8.15, 4.7, 'DPC-recorded violations');
  rect(s, 9.18, 1.98, 3.52, 4.7, C.panel, 0.2, C.line);
  text(s, 'Security + evidence', 9.54, 2.38, 2.7, 0.28, { fontSize: 18, bold: true, color: C.ink });
  pill(s, 'SIGNED STATE', 9.54, 2.79, 1.18, C.paleBlue, C.blue);
  pill(s, 'HASH-LINKED', 10.87, 2.79, 1.2, C.paleTeal, C.tealDark);
  const ev = [
    ['01', 'Observed on device', 'Blocked app, domain, or restricted setting'],
    ['02', 'Sealed and synced', 'Append-only audit evidence moves through the outbox'],
    ['03', 'Visible to admins', 'Filter by device, class, policy, and date'],
  ];
  ev.forEach(([n, t, b], i) => {
    const y = 3.32 + i * 0.82;
    text(s, n, 9.55, y, 0.35, 0.2, { fontSize: 9, bold: true, color: C.teal });
    text(s, t, 10.08, y - 0.02, 2.18, 0.22, { fontSize: 11.4, bold: true, color: C.ink });
    text(s, b, 10.08, y + 0.28, 2.18, 0.42, { fontSize: 8.7, color: C.muted, valign: 'top' });
  });
  rect(s, 9.54, 5.95, 2.8, 0.42, C.paleTeal, 0.14);
  text(s, 'Private device content stays private.', 9.72, 6.06, 2.43, 0.16, { fontSize: 8.5, bold: true, color: C.tealDark, align: 'center' });
  footer(s, 5);
  notes(s, 'This is the trust slide. The platform applies security by design: signed policy state, trusted key verification, least-privilege administrator permissions, rate limiting, privacy-limited records, and a hash-linked audit chain. A blocked action is useful only if the school can explain what happened without overreaching into private device content. The lifecycle is visible: observed on the device, sealed and queued, synchronized to the service, and then available to administrators. This turns a complaint or a guess into a consistent operational record.');
}

// 6 — Dashboard value
{
  const s = pptx.addSlide();
  s.background = { color: C.ice };
  header(s, 'The control room', 'One screen for the school day.', 'The dashboard brings school, device, policy, synchronization, violation, and governance workflows into one operating view.');
  screenshot(s, assets.dashboard, 0.62, 1.96, 8.26, 4.75, 'Live dashboard');
  rect(s, 9.22, 1.96, 3.48, 4.75, C.navy, 0.2);
  text(s, 'At a glance', 9.58, 2.34, 2.5, 0.3, { fontSize: 19, bold: true, color: C.white });
  const ms = [
    ['2', 'enrolled devices', '79D6C9'],
    ['2', 'compliant devices', '79D6C9'],
    ['22', 'reported violations', 'FFB7C3'],
    ['0', 'pending commands', 'A9CFFF'],
  ];
  ms.forEach(([v, l, col], i) => {
    const y = 3.0 + i * 0.69;
    text(s, v, 9.6, y, 0.52, 0.28, { fontSize: 20, bold: true, color: col });
    text(s, l.toUpperCase(), 10.34, y + 0.05, 1.85, 0.18, { fontSize: 8.5, bold: true, color: 'C7D6E5', charSpacing: .5 });
    if (i < ms.length - 1) line(s, 9.58, y + 0.49, 12.28, y + 0.49, '355069', .7);
  });
  text(s, 'Designed for a non-technical school administrator.', 9.6, 5.96, 2.54, 0.42, { fontSize: 10.5, bold: true, color: C.white, valign: 'top' });
  pill(s, 'REACT', 9.58, 6.42, 0.62, '28405C', 'A9CFFF');
  pill(s, 'FLASK', 10.32, 6.42, 0.67, '204B59', '9EE9D6');
  pill(s, 'POSTGRES', 11.1, 6.42, 0.92, '3A2D39', 'FFB7C3');
  pill(s, 'REDIS', 12.14, 6.42, 0.52, '4A4025', 'FFE4A4');
  footer(s, 6);
  notes(s, 'Bring the story back to the person using the system. The dashboard is deliberately not a technical console. It starts with the questions a school administrator asks: how many devices are registered, how many are enrolled, which are compliant, are any offline for review, and how many DPC-reported violations need attention? The live snapshot also shows the navigation structure: devices, assignments, policy management, violations, administration, and provisioning. Under that experience are the React frontend, Flask API, PostgreSQL system of record, and Redis operational guardrails.');
}

// 7 — Call to action
{
  const s = pptx.addSlide();
  s.background = { color: C.ink };
  text(s, 'THE NEXT STEP', 0.72, 0.62, 3.2, 0.24, { fontSize: 10, bold: true, color: '79D6C9', charSpacing: 2.1 });
  text(s, 'Start with one class.\nScale with confidence.', 0.72, 1.33, 6.1, 1.1, { fontSize: 31, bold: true, color: C.white, valign: 'top' });
  text(s, 'EduGD turns safer learning time into an operating habit—not a one-off project.', 0.75, 2.78, 5.3, 0.55, { fontSize: 15, color: 'C7D6E5', valign: 'top' });
  const plan = [
    ['01', 'Validate', 'Complete physical Android and DPC verification.'],
    ['02', 'Pilot', 'Enroll one class through the staging workflow.'],
    ['03', 'Operate', 'Review policy, sync, compliance, and violations.'],
    ['04', 'Expand', 'Scale with governance and repeatable operations.'],
  ];
  plan.forEach(([n, t, b], i) => {
    const y = 4.02 + i * 0.59;
    text(s, n, 0.76, y, 0.38, 0.18, { fontSize: 9, bold: true, color: '79D6C9' });
    text(s, t, 1.35, y - 0.02, 1.2, 0.22, { fontSize: 12, bold: true, color: C.white });
    text(s, b, 2.38, y + 0.01, 3.95, 0.2, { fontSize: 9.4, color: 'AFC3D5' });
  });
  rect(s, 7.08, 1.02, 5.55, 4.62, '172738', 0.22);
  screenshot(s, assets.devices, 7.3, 1.25, 5.11, 3.2, 'Ready to scale');
  text(s, 'Safer learning. Simpler administration.\nEvidence when it matters.', 7.34, 4.88, 4.85, 0.6, { fontSize: 17, bold: true, color: C.white, valign: 'top' });
  pill(s, 'EDUGD', 7.34, 5.74, 0.84, '1F4D59', 'A9E9DE');
  text(s, 'School device policy control', 8.36, 5.79, 3.5, 0.18, { fontSize: 9.5, color: 'AFC3D5' });
  text(s, 'Current boundary: staging validation first; production remains outside this pitch scope.', 0.76, 6.48, 5.8, 0.2, { fontSize: 8.4, color: '91A8BC' });
  text(s, 'Thank you', 0.76, 6.75, 2.0, 0.22, { fontSize: 11, bold: true, color: C.white });
  text(s, '07', 12.18, 7.12, 0.54, 0.2, { fontSize: 8.5, bold: true, color: '7CE3D3', align: 'right' });
  notes(s, 'Close with a responsible path. The project is an academic proof-of-concept MVP for school-owned Android devices in Ugandan secondary schools. The next gate is physical Android and DPC verification, followed by a staging pilot with one class. The team then reviews policy application, synchronization acknowledgements, compliance, offline behavior, and DPC-recorded violations before expanding. The current project boundary is staging validation first; production deployment is not part of this pitch. The final message is simple: EduGD helps schools create safer learning conditions without asking teachers to become technical administrators.');
}

(async () => {
  await pptx.writeFile({ fileName: output });
  console.log(`DECK: ${output}`);
  console.log(`BYTES: ${fs.statSync(output).size}`);
})();
