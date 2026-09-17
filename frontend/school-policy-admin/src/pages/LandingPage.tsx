import { useEffect, useState } from 'react'
import { ArrowRight, Check, CircleAlert, CircleCheck, CloudOff, LockKeyhole, Menu, Radio, RefreshCw, ShieldCheck, Smartphone, WifiOff, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { publicHealthService, type PublicHealthResult } from '@/services/public-health.service'

const capabilityRows = [
  { label: 'Device enrollment', detail: 'Register school-owned Android devices through an administrator-controlled workflow.', icon: Smartphone },
  { label: 'Policy assignment', detail: 'Publish reviewed policy revisions to the devices your school manages.', icon: ShieldCheck },
  { label: 'Audit visibility', detail: 'Keep administrative, enrollment, assignment, and synchronization events reviewable.', icon: Radio },
  { label: 'Access control', detail: 'Give approved learning tools a governed place in the school day.', icon: LockKeyhole },
]

function StatusBadge({ result, label }: { result: PublicHealthResult | null; label: string }) {
  const isGood = result?.status === 'ready' || result?.status === 'running'
  return <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3 py-2 text-xs font-medium text-white/80 backdrop-blur-sm" aria-live="polite">
    {isGood ? <CircleCheck className="size-4 text-lime-300" aria-hidden="true" /> : result?.status === 'unavailable' ? <WifiOff className="size-4 text-amber-300" aria-hidden="true" /> : <CircleAlert className="size-4 text-amber-300" aria-hidden="true" />}
    <span>{label}: {result?.status === 'ready' ? 'ready' : result?.status === 'running' ? 'responding' : result?.status === 'unavailable' ? 'offline' : 'checking'}</span>
  </div>
}

function usePublicHealth() {
  const [health, setHealth] = useState<PublicHealthResult | null>(null)
  const [readiness, setReadiness] = useState<PublicHealthResult | null>(null)
  const [checking, setChecking] = useState(true)

  async function check() {
    setChecking(true)
    const controller = new AbortController()
    const [healthResult, readinessResult] = await Promise.all([
      publicHealthService.checkHealth(controller.signal),
      publicHealthService.checkReadiness(controller.signal),
    ])
    setHealth(healthResult)
    setReadiness(readinessResult)
    setChecking(false)
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void check() }, 0)
    return () => window.clearTimeout(timer)
  }, [])
  return { health, readiness, checking, check }
}

export function LandingPage() {
  const { health, readiness, checking, check } = usePublicHealth()
  const [menuOpen, setMenuOpen] = useState(false)
  const systemReady = readiness?.status === 'ready'

  return <main className="min-h-screen overflow-hidden bg-[#f4f1e8] text-[#11211d]">
    <a href="#main-content" className="sr-only z-50 bg-white p-3 focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Skip to content</a>
    <section className="relative isolate bg-[#11211d] text-white">
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-size-[48px_48px] opacity-80" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <nav className="flex h-20 items-center justify-between border-b border-white/10" aria-label="Public navigation">
          <Link to="/landing" className="flex items-center gap-3 font-semibold tracking-tight"><span className="grid size-9 place-items-center rounded-xl bg-lime-300 text-[#11211d]"><ShieldCheck className="size-5" aria-hidden="true" /></span><span>EduGuard</span></Link>
          <div className={`${menuOpen ? 'absolute left-5 right-5 top-20 flex' : 'hidden'} z-10 flex-col gap-4 rounded-2xl border border-white/10 bg-[#17332d] p-5 text-sm md:static md:flex md:flex-row md:items-center md:border-0 md:bg-transparent md:p-0`}>
            <a href="#why" onClick={() => setMenuOpen(false)} className="text-white/70 hover:text-white">Why EduGuard</a>
            <a href="#controls" onClick={() => setMenuOpen(false)} className="text-white/70 hover:text-white">Controls</a>
            <Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-full bg-lime-300 px-4 py-2.5 font-semibold text-[#11211d] hover:bg-lime-200">Access admin console <ArrowRight className="size-4" aria-hidden="true" /></Link>
          </div>
          <button type="button" className="grid size-10 place-items-center rounded-full border border-white/15 md:hidden" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}</button>
        </nav>

        <div className="grid gap-14 py-16 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:py-24">
          <div className="max-w-2xl">
            <div className="mb-7 flex flex-wrap gap-2"><StatusBadge result={health} label="API" /><StatusBadge result={readiness} label="Readiness" /></div>
            <p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-lime-300">School-owned. Offline-first. Built for Uganda.</p>
            <h1 className="max-w-3xl text-5xl font-semibold leading-[0.96] tracking-[-0.04em] sm:text-7xl">Keep learning moving when the network does not.</h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-white/70">EduGuard helps secondary schools govern Android learning devices with local policy enforcement, accountable administration, and resilient synchronization for real infrastructure conditions.</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row"><Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-full bg-lime-300 px-6 py-3.5 font-semibold text-[#11211d] hover:bg-lime-200">Access admin console <ArrowRight className="size-4" aria-hidden="true" /></Link><a href="#why" className="inline-flex items-center justify-center rounded-full border border-white/20 px-6 py-3.5 font-semibold text-white hover:bg-white/10">See the operating model</a></div>
            <p className="mt-6 text-xs text-white/45">Live status checks use the public EduGuard API. No device or administrator data is exposed here.</p>
          </div>
          <div className="relative mx-auto w-full max-w-xl" aria-label="EduGuard administration preview">
            <div className="absolute -inset-8 rounded-[3rem] bg-lime-300/10 blur-3xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/15 bg-[#f7f8f1] p-3 text-[#11211d] shadow-2xl shadow-black/30">
              <div className="flex items-center justify-between border-b border-[#11211d]/10 px-4 py-3"><div className="flex items-center gap-2"><span className="size-2 rounded-full bg-lime-500" /><span className="text-xs font-semibold">School control room</span></div><span className="rounded-full bg-[#e4efc8] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#33551e]">{systemReady ? 'Ready' : 'Observe'}</span></div>
              <div className="grid gap-3 p-4 sm:grid-cols-2"><div className="rounded-2xl bg-[#11211d] p-5 text-white sm:col-span-2"><div className="flex items-start justify-between"><div><p className="text-xs text-white/50">Policy state</p><p className="mt-2 text-2xl font-semibold">Local rules stay active</p></div><LockKeyhole className="size-5 text-lime-300" aria-hidden="true" /></div><div className="mt-7 flex items-center gap-2 text-xs text-white/55"><span className="size-2 rounded-full bg-lime-300" />Policy evaluation is designed to continue locally.</div></div><div className="rounded-2xl border border-[#11211d]/10 bg-white p-4"><p className="text-xs text-[#11211d]/50">Connection</p><p className="mt-2 flex items-center gap-2 font-semibold"><span className={`size-2 rounded-full ${health?.status === 'unavailable' ? 'bg-amber-500' : 'bg-lime-500'}`} />{health?.detail ?? 'Checking API'}</p></div><div className="rounded-2xl border border-[#11211d]/10 bg-white p-4"><p className="text-xs text-[#11211d]/50">Audit trail</p><p className="mt-2 font-semibold">Append-only review</p><p className="mt-1 text-xs text-[#11211d]/50">Events reconcile after reconnection.</p></div></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div id="main-content">
      <section id="why" className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-28"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#8a5a27]">Designed around the school day</p><h2 className="mt-4 max-w-lg text-4xl font-semibold leading-tight tracking-[-0.03em] sm:text-5xl">A safer way to make school-owned phones useful.</h2></div><div className="grid gap-4 sm:grid-cols-2"><article className="border-t-2 border-[#11211d] pt-5"><CloudOff className="size-6 text-[#8a5a27]" aria-hidden="true" /><h3 className="mt-6 text-xl font-semibold">Local continuity</h3><p className="mt-3 leading-7 text-[#11211d]/65">Policy evaluation belongs close to the device, so a power cut or weak WAN link does not decide whether learning controls remain in force.</p></article><article className="border-t-2 border-[#11211d] pt-5"><LockKeyhole className="size-6 text-[#8a5a27]" aria-hidden="true" /><h3 className="mt-6 text-xl font-semibold">Institutional control</h3><p className="mt-3 leading-7 text-[#11211d]/65">Administrators define approved learning access, device assignments, and reviewable events from a focused control surface.</p></article><article className="border-t-2 border-[#11211d] pt-5"><WifiOff className="size-6 text-[#8a5a27]" aria-hidden="true" /><h3 className="mt-6 text-xl font-semibold">Low-connectivity aware</h3><p className="mt-3 leading-7 text-[#11211d]/65">Reconnection is treated as a synchronization moment, not a prerequisite for every local decision.</p></article><article className="border-t-2 border-[#11211d] pt-5"><Radio className="size-6 text-[#8a5a27]" aria-hidden="true" /><h3 className="mt-6 text-xl font-semibold">Accountable operations</h3><p className="mt-3 leading-7 text-[#11211d]/65">Enrollment, assignment, authentication, and synchronization activity have a place in the administrative record.</p></article></div></section>

      <section id="controls" className="bg-[#dfe9d2] px-5 py-20 sm:px-8 lg:py-28"><div className="mx-auto max-w-7xl"><div className="max-w-2xl"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#33551e]">Control surface</p><h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">A clear operational picture, without the noise.</h2><p className="mt-5 text-lg leading-8 text-[#11211d]/65">The existing administration API centers the workflows that matter: registered devices, policy revisions, assignments, enrollment, and audit events.</p></div><div className="mt-12 grid gap-4 md:grid-cols-2">{capabilityRows.map(({ label, detail, icon: Icon }) => <article key={label} className="flex gap-4 border-t border-[#11211d]/20 pt-5"><div className="grid size-11 shrink-0 place-items-center rounded-full bg-[#11211d] text-lime-300"><Icon className="size-5" aria-hidden="true" /></div><div><h3 className="text-lg font-semibold">{label}</h3><p className="mt-2 max-w-md leading-7 text-[#11211d]/65">{detail}</p></div><Check className="ml-auto mt-1 size-5 text-[#33551e]" aria-hidden="true" /></article>)}</div></div></section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28"><div className="grid gap-10 lg:grid-cols-[1fr_0.8fr] lg:items-end"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#8a5a27]">Public system telemetry</p><h2 className="mt-4 text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">Know whether the service is reachable.</h2><p className="mt-5 max-w-xl text-lg leading-8 text-[#11211d]/65">This public view checks only the API process and readiness contract. Protected device, policy, and audit data remains behind administrator authentication.</p></div><div className="rounded-[1.5rem] border border-[#11211d]/15 bg-white p-5"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-wider text-[#11211d]/50">Live checks</p><p className="mt-2 font-semibold">{checking ? 'Checking service state' : 'Last checked just now'}</p></div><button type="button" onClick={() => void check()} disabled={checking} className="grid size-10 place-items-center rounded-full border border-[#11211d]/15 hover:bg-[#f4f1e8] disabled:opacity-50" aria-label="Refresh public system status" title="Refresh public system status"><RefreshCw className={`size-4 ${checking ? 'animate-spin' : ''}`} aria-hidden="true" /></button></div><div className="mt-5 space-y-3"><div className="flex items-center justify-between rounded-xl bg-[#f4f1e8] px-4 py-3 text-sm"><span>API process</span><span className="font-semibold">{health?.status === 'running' || health?.status === 'ready' ? 'Responding' : health?.status === 'unavailable' ? 'Unavailable' : 'Checking'}</span></div><div className="flex items-center justify-between rounded-xl bg-[#f4f1e8] px-4 py-3 text-sm"><span>Application readiness</span><span className="font-semibold">{readiness?.status === 'ready' ? 'Ready' : readiness?.status === 'unavailable' ? 'Unavailable' : readiness ? 'Not ready' : 'Checking'}</span></div></div></div></div></section>

      <section className="bg-[#11211d] px-5 py-20 text-white sm:px-8 lg:py-24"><div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 md:flex-row md:items-end"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-lime-300">For the people running the school</p><h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight tracking-[-0.03em] sm:text-5xl">Put digital learning inside a system your school can govern.</h2></div><Link to="/login" className="inline-flex shrink-0 items-center gap-2 rounded-full bg-lime-300 px-6 py-3.5 font-semibold text-[#11211d] hover:bg-lime-200">Access admin console <ArrowRight className="size-4" aria-hidden="true" /></Link></div></section>
    </div>
    <footer className="bg-[#11211d] px-5 pb-8 text-sm text-white/45 sm:px-8"><div className="mx-auto flex max-w-7xl flex-col gap-3 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between"><span>EduGuard by EduGD</span><span>Offline-first policy control for school-owned Android devices.</span></div></footer>
  </main>
}