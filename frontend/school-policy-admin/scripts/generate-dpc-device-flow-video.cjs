const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const repoRoot = path.resolve(__dirname, '../../../');
const outputDir = path.join(repoRoot, 'output');
const outputPath = path.join(outputDir, 'edugd-android-device-flow.webm');
const tempDir = path.join(outputDir, '.device-flow-video');

fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(tempDir, { recursive: true });

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root { color-scheme: dark; font-family: Arial, Helvetica, sans-serif; }
    * { box-sizing: border-box; }
    html, body { margin: 0; width: 100%; height: 100%; background: #05070b; overflow: hidden; }
    body { display: grid; place-items: center; }
    .stage { width: 1080px; height: 1920px; position: relative; display: grid; place-items: center; background: radial-gradient(circle at 50% 38%, #172238 0, #080b12 42%, #030407 100%); }
    .stage::before { content: ''; position: absolute; inset: 0; background: linear-gradient(125deg, rgba(59,130,246,.12), transparent 28%, transparent 72%, rgba(38,211,163,.08)); }
    .device { position: relative; width: 760px; height: 1510px; padding: 15px; border-radius: 78px; background: linear-gradient(145deg, #333947, #0c1017 24%, #252b36 76%, #090c11); box-shadow: 0 42px 90px rgba(0,0,0,.72), inset 0 0 0 2px rgba(255,255,255,.12), 0 0 0 1px rgba(74,91,117,.35); }
    .screen { position: relative; width: 100%; height: 100%; overflow: hidden; border-radius: 65px; background: #0b1018; box-shadow: inset 0 0 0 1px rgba(255,255,255,.14); }
    .camera { position: absolute; z-index: 20; top: 18px; left: 50%; transform: translateX(-50%); width: 116px; height: 32px; border-radius: 22px; background: #050608; box-shadow: inset 0 0 0 1px rgba(255,255,255,.08); }
    .camera::after { content: ''; position: absolute; top: 10px; right: 23px; width: 12px; height: 12px; border-radius: 50%; background: #132034; box-shadow: inset 0 0 5px #68a5ff; }
    .status { position: absolute; z-index: 15; top: 24px; left: 34px; right: 34px; display: flex; justify-content: space-between; color: #e7edf7; font-size: 18px; letter-spacing: .3px; }
    .status-right { display: flex; gap: 12px; align-items: center; }
    .wifi { width: 17px; height: 12px; border: 2px solid #e7edf7; border-bottom: 0; border-radius: 18px 18px 0 0; transform: translateY(3px); opacity: .9; }
    .battery { width: 25px; height: 12px; border: 2px solid #e7edf7; border-radius: 3px; position: relative; }
    .battery::after { content: ''; position: absolute; right: -5px; top: 3px; width: 3px; height: 5px; border-radius: 1px; background: #e7edf7; }
    .battery::before { content: ''; position: absolute; inset: 2px 5px 2px 2px; border-radius: 1px; background: #55d694; }
    .scenes { position: absolute; inset: 0; }
    .scene { position: absolute; inset: 0; padding: 112px 58px 70px; opacity: 0; transform: translateY(22px); transition: opacity .45s ease, transform .45s ease; pointer-events: none; }
    .scene.active { opacity: 1; transform: translateY(0); }
    .eyebrow { color: #76aefc; font-size: 17px; font-weight: 700; letter-spacing: 2.6px; text-transform: uppercase; margin-bottom: 28px; }
    h1 { margin: 0 0 18px; color: #f5f8ff; font-size: 47px; line-height: 1.1; letter-spacing: -.8px; }
    h2 { margin: 0 0 12px; color: #f5f8ff; font-size: 31px; line-height: 1.16; }
    p { margin: 0; color: #9ba9bc; font-size: 23px; line-height: 1.45; }
    .muted { color: #8391a4; font-size: 18px; }
    .card { margin-top: 36px; padding: 29px; border: 1px solid #2a3a53; border-radius: 25px; background: linear-gradient(145deg, rgba(23,35,55,.95), rgba(13,19,30,.95)); box-shadow: 0 17px 38px rgba(0,0,0,.28); }
    .row { display: flex; align-items: center; gap: 18px; }
    .row + .row { margin-top: 24px; }
    .icon { width: 57px; height: 57px; display: grid; place-items: center; flex: 0 0 auto; border-radius: 18px; color: #d8e8ff; background: rgba(59,130,246,.18); border: 1px solid rgba(105,164,255,.42); font-size: 27px; font-weight: 700; }
    .icon.green { color: #a9f4cf; background: rgba(38,211,163,.16); border-color: rgba(93,224,177,.38); }
    .icon.red { color: #ffd2d2; background: rgba(242,95,95,.16); border-color: rgba(255,129,129,.4); }
    .row strong { display: block; color: #eff5ff; font-size: 22px; margin-bottom: 5px; }
    .row span { color: #97a6ba; font-size: 18px; }
    .qr { width: 350px; height: 350px; margin: 46px auto 34px; padding: 25px; border-radius: 29px; background: #f5f8fc; box-shadow: 0 0 0 12px rgba(255,255,255,.06), 0 25px 55px rgba(0,0,0,.35); position: relative; }
    .qr-grid { width: 100%; height: 100%; background: repeating-linear-gradient(90deg, #111 0 11px, #f5f8fc 11px 22px), repeating-linear-gradient(0deg, #111 0 11px, transparent 11px 22px); mix-blend-mode: multiply; opacity: .84; }
    .finder { position: absolute; width: 74px; height: 74px; border: 13px solid #111; background: #f5f8fc; }
    .finder::after { content: ''; position: absolute; inset: 12px; background: #111; }
    .finder.one { top: 38px; left: 38px; } .finder.two { top: 38px; right: 38px; } .finder.three { bottom: 38px; left: 38px; }
    .scan-line { position: absolute; left: 22px; right: 22px; top: 50%; height: 3px; background: #3b82f6; box-shadow: 0 0 16px #3b82f6; animation: scan 2.1s ease-in-out infinite; }
    @keyframes scan { 0%,100% { transform: translateY(-115px); opacity: .35; } 50% { transform: translateY(115px); opacity: 1; } }
    .progress { height: 11px; margin-top: 36px; overflow: hidden; border-radius: 20px; background: #202c3e; }
    .progress i { display: block; width: 78%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #3b82f6, #63a2ff); animation: progress 4.2s ease-in-out infinite; transform-origin: left; }
    @keyframes progress { 0% { transform: scaleX(.22); } 82% { transform: scaleX(1); } 100% { transform: scaleX(1); } }
    .check { width: 116px; height: 116px; margin: 50px auto 28px; display: grid; place-items: center; border-radius: 50%; color: #b4f8d8; font-size: 58px; background: rgba(38,211,163,.15); border: 2px solid #46d99f; box-shadow: 0 0 0 14px rgba(38,211,163,.06), 0 0 42px rgba(38,211,163,.25); }
    .center { text-align: center; }
    .center h1 { font-size: 43px; }
    .pill { display: inline-flex; align-items: center; gap: 9px; margin-top: 27px; padding: 11px 17px; border: 1px solid #2a4967; border-radius: 999px; color: #b9d7ff; background: rgba(59,130,246,.12); font-size: 17px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #57dda2; box-shadow: 0 0 13px #57dda2; }
    .launcher { padding-top: 118px; background: linear-gradient(180deg, #0d1828, #0a1019 62%, #101b2a); }
    .launcher h1 { font-size: 36px; }
    .launcher-sub { margin-bottom: 28px; }
    .app-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
    .app { min-height: 142px; display: grid; place-items: center; align-content: center; gap: 10px; border-radius: 23px; border: 1px solid #263c57; background: rgba(19,32,51,.86); color: #e2ebf9; font-size: 16px; text-align: center; }
    .app b { width: 56px; height: 56px; display: grid; place-items: center; border-radius: 17px; background: #1c4c8d; color: white; font-size: 24px; }
    .app.safe b { background: #176b58; } .app.blocked b { background: #7b3044; }
    .managed { margin-top: 30px; padding: 22px; border-radius: 22px; border: 1px solid #2c5d79; background: linear-gradient(100deg, rgba(20,67,88,.72), rgba(17,39,62,.72)); }
    .managed strong { color: #c7e8ff; font-size: 20px; } .managed p { margin-top: 8px; font-size: 17px; }
    .blocked-bg { background: radial-gradient(circle at 50% 28%, rgba(119,35,55,.27), transparent 40%), #0b1018; }
    .app-launch { margin: 54px auto 28px; width: 250px; height: 250px; display: grid; place-items: center; border-radius: 58px; background: linear-gradient(145deg, #982d53, #54172e); border: 1px solid #bd4e6f; box-shadow: 0 25px 60px rgba(120,34,63,.32); font-size: 108px; }
    .deny { padding: 25px 27px; border-radius: 23px; border: 1px solid #813e54; background: linear-gradient(145deg, rgba(76,23,42,.92), rgba(31,15,28,.92)); }
    .deny h2 { color: #ffd8df; font-size: 30px; } .deny p { color: #e4b3bf; font-size: 20px; }
    .deny .support { margin-top: 17px; padding-top: 17px; border-top: 1px solid rgba(255,180,198,.18); color: #f4dce2; font-size: 20px; line-height: 1.4; }
    .violation { margin-top: 23px; display: flex; align-items: center; gap: 13px; color: #ffc8d3; font-size: 17px; }
    .review { padding-top: 118px; }
    .lifecycle { padding-top: 118px; }
    .lifecycle .eyebrow { margin-bottom: 22px; }
    .lifecycle h1 { font-size: 39px; }
    .lifecycle-grid { display: grid; gap: 15px; margin-top: 29px; }
    .lifecycle-step { display: flex; align-items: center; gap: 15px; padding: 17px 18px; border-radius: 17px; border: 1px solid #29415c; background: rgba(19,32,51,.78); }
    .lifecycle-step.done { border-color: rgba(78,213,159,.4); background: rgba(20,61,58,.4); }
    .lifecycle-step .step-number { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 50%; color: #d8e9ff; background: #1c4c8d; font-size: 15px; font-weight: 700; }
    .lifecycle-step.done .step-number { color: #baf7d8; background: #176b58; }
    .lifecycle-step strong { display: block; color: #edf4ff; font-size: 18px; }
    .lifecycle-step span { display: block; margin-top: 4px; color: #91a3bb; font-size: 15px; }
    .final-state { padding-top: 151px; text-align: center; }
    .final-state .check { margin-top: 21px; }
    .final-state h1 { font-size: 42px; }
    .final-state .card { text-align: left; margin-top: 38px; }
    .heartbeat { display: inline-flex; align-items: center; gap: 9px; margin-top: 24px; color: #9aefc5; font-size: 17px; }
    .heartbeat i { width: 9px; height: 9px; border-radius: 50%; background: #57dda2; box-shadow: 0 0 13px #57dda2; animation: pulse 1.2s ease-in-out infinite; }
    @keyframes pulse { 50% { transform: scale(1.5); opacity: .65; } }
    .review-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 36px; }
    .review-top h1 { font-size: 37px; }
    .live { display: flex; align-items: center; gap: 8px; color: #87e4ba; font-size: 16px; padding-top: 10px; }
    .event { padding: 24px 0; border-bottom: 1px solid #253244; }
    .event:first-of-type { border-top: 1px solid #253244; }
    .event-head { display: flex; justify-content: space-between; gap: 14px; }
    .event strong { color: #ecf3ff; font-size: 20px; } .event time { color: #7890ae; font-size: 16px; }
    .event p { margin-top: 8px; font-size: 17px; }
    .state { display: inline-flex; margin-top: 13px; padding: 7px 11px; border-radius: 9px; color: #9cecc5; background: rgba(38,211,163,.11); font-size: 14px; }
    .nav { position: absolute; left: 50%; bottom: 24px; transform: translateX(-50%); width: 190px; height: 5px; border-radius: 10px; background: #e5e9f2; opacity: .78; }
    .brand { position: absolute; z-index: 3; bottom: 77px; left: 58px; color: rgba(190,210,238,.65); font-size: 14px; letter-spacing: 1.7px; }
    .timeline { position: absolute; left: 128px; right: 128px; bottom: 104px; height: 4px; border-radius: 10px; overflow: hidden; background: rgba(146,171,207,.18); z-index: 10; }
    .timeline i { display: block; width: 0; height: 100%; background: #5d9bff; box-shadow: 0 0 10px #5d9bff; }
    .scene-tag { position: absolute; top: 93px; right: 58px; z-index: 3; color: #6984a8; font-size: 13px; letter-spacing: 1.4px; }
  </style>
</head>
<body>
  <main class="stage">
    <section class="device">
      <div class="screen">
        <div class="camera"></div>
        <div class="status"><span id="clock">09:42</span><span class="status-right"><i class="wifi"></i><span>5G</span><i class="battery"></i></span></div>
        <div class="scene-tag">ANDROID ENTERPRISE</div>
        <div class="scenes">
          <section class="scene active" data-scene="0">
            <div class="eyebrow">Device setup</div>
            <h1>Set up your device</h1>
            <p>This school-owned device will be managed by your organization.</p>
            <div class="qr"><div class="qr-grid"></div><i class="finder one"></i><i class="finder two"></i><i class="finder three"></i><i class="scan-line"></i></div>
            <div class="center"><h2>Scan the enrollment QR code</h2><p class="muted">Provisioning is secured by Android Enterprise.</p></div>
            <div class="card"><div class="row"><div class="icon">▣</div><div><strong>School-owned device</strong><span>EduGD device policy controller</span></div></div></div>
          </section>
          <section class="scene" data-scene="1">
            <div class="eyebrow">Android Enterprise</div>
            <h1>Provisioning device owner</h1>
            <p>Applying managed configuration and preparing the secure work environment.</p>
            <div class="card"><div class="row"><div class="icon">↻</div><div><strong>EduGD Device Policy Controller</strong><span>Establishing organization controls</span></div></div><div class="progress"><i></i></div></div>
            <div class="card"><div class="row"><div class="icon green">✓</div><div><strong>Management profile ready</strong><span>Device owner mode will be activated</span></div></div><div class="row"><div class="icon">⌁</div><div><strong>Secure enrollment channel</strong><span>Waiting for policy synchronization</span></div></div></div>
          </section>
          <section class="scene" data-scene="2">
            <div class="center">
              <div class="check">✓</div>
              <div class="eyebrow">EduGD DPC</div>
              <h1>Device enrolled</h1>
              <p>The device is now connected to your school administration service.</p>
              <div class="pill"><i class="dot"></i>Policy synchronization active</div>
            </div>
            <div class="card"><div class="row"><div class="icon green">⌁</div><div><strong>Secure device identity</strong><span>Key-backed enrollment established</span></div></div><div class="row"><div class="icon green">↗</div><div><strong>Initial policy sync</strong><span>Class Time Policy received</span></div></div><div class="row"><div class="icon green">◉</div><div><strong>Connection status</strong><span>Healthy · Last sync just now</span></div></div></div>
          </section>
          <section class="scene launcher" data-scene="3">
            <div class="eyebrow">Managed device</div>
            <h1>Class Time Policy</h1>
            <p class="launcher-sub">Active now · Device owner controls enabled</p>
            <div class="app-grid"><div class="app safe"><b>∑</b><span>Khan Academy</span></div><div class="app safe"><b>文</b><span>Duolingo</span></div><div class="app safe"><b>ED</b><span>EduGD</span></div><div class="app blocked"><b>♪</b><span>Social video</span></div><div class="app blocked"><b>◎</b><span>Games</span></div><div class="app blocked"><b>◈</b><span>Entertainment</span></div></div>
            <div class="managed"><strong>Managed by your school</strong><p>Learning applications are available. Restricted applications remain unavailable during class time.</p></div>
          </section>
          <section class="scene blocked-bg" data-scene="4">
            <div class="eyebrow">Restricted application</div>
            <h1>Opening social video</h1>
            <div class="app-launch">♪</div>
            <div class="deny"><h2>Access blocked</h2><p>Class Time Policy does not allow this application right now.</p><div class="support">This action is blocked by your school administrator.</div></div>
            <div class="violation"><span class="icon red" style="width:34px;height:34px;border-radius:10px;font-size:18px">!</span><span>Policy violation recorded by EduGD DPC</span></div>
          </section>
          <section class="scene review" data-scene="5">
            <div class="review-top"><div><div class="eyebrow">EduGD activity</div><h1>Violation recorded</h1></div><div class="live"><i class="dot"></i>Synced</div></div>
            <div class="event"><div class="event-head"><strong>Blocked application launch</strong><time>09:47:18</time></div><p>Social video · package restricted by Class Time Policy</p><span class="state">Recorded by device policy controller</span></div>
            <div class="event"><div class="event-head"><strong>Policy enforcement</strong><time>09:47:19</time></div><p>Access denied and support message displayed on device</p><span class="state">Enforced on device</span></div>
            <div class="event"><div class="event-head"><strong>Administration sync</strong><time>09:47:21</time></div><p>Violation event acknowledged by school service</p><span class="state">Securely synchronized</span></div>
            <div class="card"><div class="row"><div class="icon green">✓</div><div><strong>Device remains protected</strong><span>Managed learning environment is active</span></div></div></div>
          </section>
          <section class="scene lifecycle" data-scene="6">
            <div class="eyebrow">Secure event lifecycle</div>
            <h1>Service acknowledged</h1>
            <p>The device outbox delivers the signed event and receives the administration result.</p>
            <div class="lifecycle-grid">
              <div class="lifecycle-step done"><i class="step-number">1</i><div><strong>Event sealed on device</strong><span>Hash-linked audit entry created</span></div></div>
              <div class="lifecycle-step done"><i class="step-number">2</i><div><strong>Outbox delivery</strong><span>Signed violation sent securely</span></div></div>
              <div class="lifecycle-step done"><i class="step-number">3</i><div><strong>Backend receipt</strong><span>Evidence accepted and indexed</span></div></div>
              <div class="lifecycle-step done"><i class="step-number">4</i><div><strong>Device acknowledgement</strong><span>Protection state remains active</span></div></div>
            </div>
          </section>
          <section class="scene final-state" data-scene="7">
            <div class="eyebrow">Continuous management</div>
            <div class="check">✓</div>
            <h1>Compliant and protected</h1>
            <p>The restricted action is closed and the managed learning environment continues.</p>
            <div class="heartbeat"><i></i>Device check-in active</div>
            <div class="card"><div class="row"><div class="icon green">↻</div><div><strong>Next policy check-in scheduled</strong><span>Current policy remains active on device</span></div></div><div class="row"><div class="icon green">✓</div><div><strong>Lifecycle complete</strong><span>Provisioned · enrolled · enforced · recorded · acknowledged</span></div></div></div>
          </section>
        </div>
        <div class="brand">EDUGD · DEVICE POLICY CONTROLLER</div>
        <div class="timeline"><i id="timelineFill"></i></div>
        <div class="nav"></div>
      </div>
    </section>
  </main>
  <script>
    const started = performance.now();
    const marks = [0, 3, 6, 10, 14, 18, 22, 26];
    const scenes = [...document.querySelectorAll('.scene')];
    const fill = document.getElementById('timelineFill');
    const clock = document.getElementById('clock');
    function tick() {
      const elapsed = (performance.now() - started) / 1000;
      const active = Math.min(marks.length - 1, marks.reduce((last, mark, index) => elapsed >= mark ? index : last, 0));
      scenes.forEach((scene, index) => scene.classList.toggle('active', index === active));
      fill.style.width = Math.min(100, elapsed / 30 * 100) + '%';
      const seconds = 42 + Math.floor(elapsed);
      clock.textContent = '09:' + String(seconds % 60).padStart(2, '0');
      if (elapsed < 30.2) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  </script>
</body>
</html>`;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1920 },
    deviceScaleFactor: 1,
    recordVideo: { dir: tempDir, size: { width: 1080, height: 1920 } },
  });
  const page = await context.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  await page.waitForTimeout(30000);
  const video = page.video();
  await page.close();
  const recordedPath = await video.path();
  await context.close();
  fs.copyFileSync(recordedPath, outputPath);
  fs.rmSync(tempDir, { recursive: true, force: true });
  console.log(`VIDEO: ${outputPath}`);
  console.log(`BYTES: ${fs.statSync(outputPath).size}`);
  // The local Chromium process can keep a shutdown pipe open indefinitely;
  // the page/context lifecycle above has already finalized the recording.
  browser.close().catch(() => {});
  process.exit(0);
})();
