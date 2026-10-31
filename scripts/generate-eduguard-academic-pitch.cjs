const path = require('path');
const fs = require('fs');
const pptxgen = require('../tmp/pptx-build/node_modules/pptxgenjs');

const root = path.resolve(__dirname, '..');
const outputDir = path.join(root, 'output', 'powerpoint');
const output = path.join(outputDir, 'EduGuard_Academic_Pitch.pptx');
const assetDir = path.join(root, 'output', 'edugd-pitch-assets');
const assets = {
  dashboard: path.join(assetDir, 'dashboard.png'),
  policies: path.join(assetDir, 'policies.png'),
};

for (const file of Object.values(assets)) {
  if (!fs.existsSync(file)) throw new Error(`Missing visual asset: ${file}`);
}
fs.mkdirSync(outputDir, { recursive: true });

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'EduGuard project team';
pptx.company = 'EduGuard';
pptx.subject = 'Academic pitch deck for an offline-first Android policy enforcement system';
pptx.title = 'EduGuard: An Offline-First Android Policy Enforcement System for Ugandan Secondary Schools';
pptx.lang = 'en-US';
pptx.theme = { headFontFace: 'Aptos Display', bodyFontFace: 'Aptos', lang: 'en-US' };

const W = 13.333;
const H = 7.5;
const C = {
  navy: '12304A',
  navy2: '1D4965',
  teal: '0F8A82',
  tealDark: '08665F',
  gold: 'D89B2B',
  ink: '172A3A',
  muted: '5B6E7C',
  pale: 'F5F8FA',
  white: 'FFFFFF',
  line: 'D7E1E8',
  sky: 'E6F1F6',
  greenPale: 'E5F5F1',
  goldPale: 'FFF3D8',
  redPale: 'FCECEF',
  red: 'C34E5D',
};
const HEAD = 'Aptos Display';
const BODY = 'Aptos';

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x, y, w, h,
    fontFace: opts.fontFace || BODY,
    fontSize: opts.fontSize || 16,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || 'left',
    valign: opts.valign || 'mid',
    margin: opts.margin === undefined ? 0 : opts.margin,
    fit: 'shrink',
    breakLine: false,
    paraSpaceAfterPt: 0,
    charSpacing: opts.charSpacing || 0,
    transparency: opts.transparency,
    isTextBox: true,
  });
}

function rect(slide, x, y, w, h, fill, radius = 0.14, border = fill, borderWidth = 1) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: radius,
    fill: { color: fill },
    line: { color: border, width: borderWidth, transparency: border === fill ? 100 : 0 },
  });
}

function line(slide, x1, y1, x2, y2, color = C.line, width = 1.4, endArrowType) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width, endArrowType: endArrowType || 'none' },
  });
}

function circle(slide, x, y, d, fill, label, labelColor = C.white, fontSize = 14) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, transparency: 100 } });
  text(slide, label, x, y + 0.01, d, d - 0.02, { fontSize, color: labelColor, bold: true, align: 'center' });
}

function header(slide, kicker, heading, subheading, page) {
  text(slide, kicker.toUpperCase(), 0.62, 0.36, 4.4, 0.2, { fontSize: 9.5, color: C.tealDark, bold: true, charSpacing: 1.5 });
  text(slide, heading, 0.62, 0.7, 11.7, 0.62, { fontFace: HEAD, fontSize: 27, color: C.navy, bold: true });
  text(slide, subheading, 0.64, 1.38, 11.5, 0.32, { fontSize: 13, color: C.muted });
  line(slide, 0.62, 1.82, 12.72, 1.82, C.line, 1.1);
  text(slide, String(page).padStart(2, '0'), 12.14, 7.12, 0.56, 0.16, { fontSize: 8.5, color: C.muted, align: 'right' });
}

function card(slide, x, y, w, h, fill = C.white, border = C.line) {
  rect(slide, x, y, w, h, fill, 0.13, border, 1);
}

function pill(slide, value, x, y, w, fill, color = C.ink) {
  rect(slide, x, y, w, 0.3, fill, 0.14, fill);
  text(slide, value, x + 0.08, y + 0.04, w - 0.16, 0.2, { fontSize: 8.5, color, bold: true, align: 'center', charSpacing: 0.5 });
}

function note(slide, value) {
  slide.addNotes(value);
}

function imageFrame(slide, file, x, y, w, h, label) {
  rect(slide, x + 0.08, y + 0.1, w, h, 'D5DEE5', 0.13, 'D5DEE5');
  slide.addImage({ path: file, x, y, w, h });
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: C.white, transparency: 100 }, line: { color: 'B9CAD5', width: 0.8 } });
  if (label) {
    rect(slide, x + 0.15, y + 0.15, 1.35, 0.28, C.navy, 0.12, C.navy);
    text(slide, label.toUpperCase(), x + 0.24, y + 0.19, 1.17, 0.14, { fontSize: 7, color: C.white, bold: true, align: 'center', charSpacing: 0.7 });
  }
}

// Slide 1: title only.
{
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  text(s, 'EduGuard:\nAn Offline-First Android Policy Enforcement System\nfor Ugandan Secondary Schools', 1.05, 2.15, 11.25, 2.15, {
    fontFace: HEAD, fontSize: 31, color: C.white, bold: true, align: 'center', valign: 'mid',
  });
}

// Slide 2: the problem.
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The problem', 'School phone-use policies must work even when the network does not.', 'The practical challenge is keeping rules clear, active, and reviewable across changing school conditions.', 2);

  const items = [
    ['01', 'Connectivity is not always reliable.', 'A policy should not disappear simply because the device is temporarily offline.', C.teal],
    ['02', 'Manual enforcement is difficult to monitor.', 'Staff need a simple way to see devices, policies, and status in one place.', C.gold],
    ['03', 'Schools need accountability.', 'Important actions should leave a clear record for later review.', C.navy2],
  ];
  items.forEach(([num, title, body, accent], i) => {
    const y = 2.2 + i * 1.23;
    card(s, 0.68, y, 6.25, 0.96, C.white, C.line);
    circle(s, 0.94, y + 0.24, 0.42, accent, num, C.white, 10);
    text(s, title, 1.55, y + 0.18, 4.95, 0.24, { fontSize: 15, color: C.navy, bold: true });
    text(s, body, 1.55, y + 0.5, 4.95, 0.22, { fontSize: 11.5, color: C.muted });
  });

  card(s, 7.42, 2.2, 5.2, 4.44, C.navy, C.navy);
  text(s, 'When the connection changes', 7.8, 2.58, 4.35, 0.28, { fontFace: HEAD, fontSize: 19, color: C.white, bold: true, align: 'center' });
  // Editable school/device illustration.
  rect(s, 8.18, 3.23, 3.68, 1.14, C.white, 0.16, C.white);
  rect(s, 8.43, 3.5, 1.12, 0.65, C.sky, 0.08, C.sky);
  text(s, 'SCHOOL', 8.55, 3.72, 0.88, 0.16, { fontSize: 9, color: C.navy, bold: true, align: 'center' });
  line(s, 9.58, 3.82, 10.1, 3.82, C.gold, 2, 'triangle');
  rect(s, 10.23, 3.4, 0.95, 0.86, C.greenPale, 0.11, C.teal);
  text(s, 'RULE', 10.37, 3.74, 0.67, 0.16, { fontSize: 9, color: C.tealDark, bold: true, align: 'center' });
  line(s, 11.18, 3.82, 11.7, 3.82, C.gold, 2, 'triangle');
  circle(s, 11.82, 3.52, 0.57, C.teal, 'OK', C.white, 10);
  text(s, 'The device keeps the last approved rule while offline.', 7.92, 4.72, 4.18, 0.48, { fontSize: 14, color: C.white, bold: true, align: 'center', valign: 'top' });
  pill(s, 'ONLINE', 8.18, 5.56, 1.12, C.greenPale, C.tealDark);
  pill(s, 'OFFLINE', 9.54, 5.56, 1.12, C.goldPale, C.navy);
  pill(s, 'REVIEWABLE', 10.9, 5.56, 1.34, C.sky, C.navy);
  text(s, 'A school-owned device needs continuity, not guesswork.', 7.85, 6.18, 4.32, 0.24, { fontSize: 12, color: 'D6E7EC', align: 'center' });

  note(s, 'The problem is practical rather than abstract. A school may have a clear phone-use policy, but connectivity can change and manual supervision is difficult to scale. Staff need to know which devices are registered, which policies are active, and what happened when a restricted action was attempted. Without a trusted record, every exception becomes a conversation and the school has to guess. EduGuard focuses on school-owned Android devices and keeps the important policy decision close to the device. That creates continuity when the network is unavailable and gives administrators a clearer way to review status later. This is the problem the project is designed to solve.');
}

// Slide 3: aim and contribution.
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'The aim', 'EduGuard brings policy control closer to the device.', 'The project connects one administrator decision to local enforcement and reviewable evidence.', 3);
  card(s, 0.7, 2.15, 11.95, 0.82, C.navy, C.navy);
  text(s, 'Aim: design a practical offline-first system for enforcing school phone-use policies on school-owned Android devices.', 1.0, 2.36, 11.35, 0.34, { fontFace: HEAD, fontSize: 18, color: C.white, bold: true, align: 'center' });

  const cols = [0.7, 4.55, 8.4];
  const cards = [
    ['CONTROL', 'Manage devices and policies from one administrator surface.', C.sky, C.blue || C.navy2, '01'],
    ['ENFORCEMENT', 'Keep approved rules active on the Android device, even offline.', C.greenPale, C.teal, '02'],
    ['ACCOUNTABILITY', 'Keep security-relevant records for review and follow-up.', C.goldPale, C.gold, '03'],
  ];
  cards.forEach(([title, body, fill, accent, num], i) => {
    card(s, cols[i], 3.42, 3.55, 2.45, fill, fill);
    circle(s, cols[i] + 0.28, 3.7, 0.52, accent, num, C.white, 11);
    text(s, title, cols[i] + 0.28, 4.42, 2.95, 0.25, { fontFace: HEAD, fontSize: 17, color: C.navy, bold: true });
    text(s, body, cols[i] + 0.28, 4.86, 2.92, 0.55, { fontSize: 13, color: C.ink, valign: 'top' });
    if (i < 2) line(s, cols[i] + 3.56, 4.62, cols[i + 1] - 0.12, 4.62, C.teal, 1.8, 'triangle');
  });
  text(s, 'Scope: a school-owned Android proof of concept, not a consumer parental-control product or a full commercial MDM platform.', 0.86, 6.42, 11.6, 0.28, { fontSize: 12, color: C.tealDark, bold: true, align: 'center' });

  note(s, 'The aim is to make policy enforcement practical in the environment the project is targeting. EduGuard is built for school-owned Android devices, where an authorised administrator can define a rule and the device can apply that rule locally. The contribution has three parts. First, control: the school has one place to manage devices and policies. Second, enforcement: the approved rule stays active on the device even when connectivity is unavailable. Third, accountability: important policy and security events can be reviewed later. This is an academic proof of concept with a focused scope. It is not intended to be a consumer parental-control product or to claim the complete feature set of a commercial mobile-device-management platform.');
}

// Slide 4: how it works.
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'How it works', 'The device keeps the latest approved policy and continues working offline.', 'Four simple steps connect school administration to local Android enforcement.', 4);
  const steps = [
    ['1', 'Create', 'Administrator creates a clear school policy.', C.navy2],
    ['2', 'Assign', 'School assigns it to an approved device.', C.teal],
    ['3', 'Enforce', 'Android stores and applies it offline.', C.gold],
    ['4', 'Synchronise', 'Status and events return when connected.', C.navy2],
  ];
  steps.forEach(([num, title, body, accent], i) => {
    const x = 0.7 + i * 3.08;
    card(s, x, 2.28, 2.5, 1.65, C.white, C.line);
    circle(s, x + 0.22, 2.5, 0.5, accent, num, C.white, 12);
    text(s, title, x + 0.88, 2.58, 1.25, 0.24, { fontFace: HEAD, fontSize: 17, color: C.navy, bold: true });
    text(s, body, x + 0.22, 3.18, 2.05, 0.43, { fontSize: 12, color: C.muted, valign: 'top' });
    if (i < 3) line(s, x + 2.5, 3.05, x + 2.94, 3.05, C.teal, 1.9, 'triangle');
  });

  card(s, 0.7, 4.45, 11.94, 1.44, C.navy, C.navy);
  text(s, 'WHEN CONNECTIVITY IS LOST', 1.0, 4.73, 2.1, 0.18, { fontSize: 9.5, color: C.gold, bold: true, charSpacing: 1.0 });
  const offline = [
    ['Keep', 'last approved policy'],
    ['Apply', 'rules on the device'],
    ['Store', 'events for later'],
    ['Sync', 'when the network returns'],
  ];
  offline.forEach(([verb, body], i) => {
    const x = 3.18 + i * 2.28;
    circle(s, x, 4.75, 0.34, i === 3 ? C.teal : C.navy2, String(i + 1), C.white, 9);
    text(s, verb, x + 0.46, 4.75, 0.7, 0.18, { fontSize: 11.5, color: C.white, bold: true });
    text(s, body, x + 0.46, 5.08, 1.45, 0.22, { fontSize: 10.5, color: 'D6E7EC' });
  });
  text(s, 'Central control  >  local continuity  >  later review', 1.0, 6.42, 11.3, 0.25, { fontFace: HEAD, fontSize: 17, color: C.tealDark, bold: true, align: 'center' });

  note(s, 'The workflow is deliberately simple. First, an administrator creates a policy in the school control surface. Second, the school assigns that policy to an approved device. Third, the Android device stores the approved policy and enforces it locally. If the network connection is lost, the device does not simply forget the rules. It keeps the last accepted policy, applies the relevant restrictions, and stores important events for later synchronisation. Fourth, when connectivity returns, the device reports status and queued events back to the service. The panel does not need to follow the underlying protocols to understand the value: the school sets the rule, the device continues the rule, and the system supports later review.');
}

// Slide 5: key capabilities and product evidence.
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'Key capabilities', 'One workflow for control, enforcement, and accountability.', 'The prototype gives administrators a clear view of policies, devices, and status.', 5);
  imageFrame(s, assets.dashboard, 0.65, 2.12, 7.3, 3.5, 'Dashboard');
  imageFrame(s, assets.policies, 8.28, 2.12, 4.4, 3.5, 'Policies');

  const caps = [
    ['Manage devices', 'See registered and enrolled school-owned devices.', C.sky, C.navy2],
    ['Create and assign policies', 'Set approved rules and track revisions.', C.greenPale, C.teal],
    ['Review status and events', 'Follow compliance and security-relevant records.', C.goldPale, C.gold],
  ];
  caps.forEach(([title, body, fill, accent], i) => {
    const x = 0.65 + i * 4.02;
    card(s, x, 5.95, 3.72, 0.77, fill, fill);
    circle(s, x + 0.18, 6.15, 0.28, accent, '', C.white, 8);
    text(s, title, x + 0.58, 6.06, 2.9, 0.18, { fontSize: 11.5, color: C.navy, bold: true });
    text(s, body, x + 0.58, 6.32, 2.92, 0.2, { fontSize: 9.5, color: C.muted });
  });

  note(s, 'This slide shows the user-facing part of the system. The dashboard provides a single view of school-owned devices, their reported status, and the policy signals that need attention. The policy page shows that administrators can review policy definitions and their revision history instead of relying on informal instructions. Together, these surfaces support the main workflow: manage devices, create and assign phone-use policies, apply restrictions through the Android device, and review compliance or security-relevant events. The screenshots are evidence of the implemented administration surfaces. They are not a claim that every field deployment condition has already been validated. The emphasis is on a clear workflow that a non-technical school administrator can understand.');
}

// Slide 6: evidence, value, and next step.
{
  const s = pptx.addSlide();
  s.background = { color: C.pale };
  header(s, 'Evidence and next step', 'EduGuard is built for practical school use.', 'Near-complete software scope; responsible field validation is still ahead.', 6);
  const cards = [
    ['SHOWN', 'Verified demonstrations', 'Implemented administration surfaces, tested policy workflows, and a clear offline-first design.', C.greenPale, C.tealDark],
    ['USEFUL', 'Practical school value', 'Continuity during connectivity gaps, simpler administration, and better accountability.', C.sky, C.navy2],
    ['NEXT', 'Validation before scale', 'Supervised pilot, longer offline testing, and final Android/runtime verification.', C.goldPale, C.gold],
  ];
  cards.forEach(([label, title, body, fill, accent], i) => {
    const x = 0.68 + i * 4.02;
    card(s, x, 2.35, 3.72, 2.85, fill, fill);
    pill(s, label, x + 0.28, 2.66, 0.75, accent, C.white);
    text(s, title, x + 0.28, 3.25, 3.0, 0.32, { fontFace: HEAD, fontSize: 18, color: C.navy, bold: true });
    text(s, body, x + 0.28, 3.82, 3.05, 0.82, { fontSize: 13, color: C.ink, valign: 'top' });
  });
  card(s, 0.68, 5.68, 11.98, 0.78, C.navy, C.navy);
  text(s, 'The responsible claim: a credible, near-complete proof of concept that should earn evidence before scale.', 1.0, 5.9, 11.35, 0.3, { fontFace: HEAD, fontSize: 17, color: C.white, bold: true, align: 'center' });
  text(s, 'Practical local fit is the central takeaway.', 1.0, 6.65, 11.35, 0.2, { fontSize: 11.5, color: C.tealDark, bold: true, align: 'center' });

  note(s, 'The project is presented as a near-complete proof of concept, but the claim remains evidence-safe. What has been shown is the implemented administration experience, tested policy workflows, and an architecture designed to keep approved rules active during connectivity gaps. The practical value is continuity, simpler administration, and a clearer record of important events. The next step is not immediate large-scale deployment. It is a supervised pilot with approved school-owned devices, longer offline and recovery testing, and final Android and runtime verification. This distinction matters to an academic panel: the system is far enough along to demonstrate a credible contribution, while the remaining work is clearly defined. EduGuard should earn evidence before scale, especially in the real conditions of Ugandan secondary schools.');
}

// Slide 7: closing only.
{
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  text(s, 'Thank You', 1.0, 3.05, 11.33, 0.78, { fontFace: HEAD, fontSize: 42, color: C.white, bold: true, align: 'center' });
}

pptx.writeFile({ fileName: output })
  .then(() => console.log(`Wrote ${output}`))
  .catch((err) => { console.error(err); process.exitCode = 1; });
