import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminShell } from '@/components/layout/AdminShell'
import { LoginPage } from '@/pages/LoginPage'
import { LoadingState } from '@/components/ui/AsyncState'
import { LandingPage } from '@/pages/LandingPage'
import { MarketingShell } from '@/components/marketing/MarketingShell'
import { AboutPage, ArchitecturePage, ContactPage, FeatureDetailPage, FeaturesPage, HowItWorksPage, ProductPage, ResourcesPage, SchoolsPage, SecurityPage } from '@/pages/MarketingPages'
import { LanguageProvider } from '@/i18n/LanguageContext'
import { LandingLanguageProvider } from '@/i18n/LandingLanguageContext'

const DashboardPage = lazy(() => import('@/pages/dashboard').then((module) => ({ default: module.DashboardPage })))
const DevicesPage = lazy(() => import('@/pages/devices').then((module) => ({ default: module.DevicesPage })))
const PoliciesPage = lazy(() => import('@/pages/policies').then((module) => ({ default: module.PoliciesPage })))
const PolicyDetailPage = lazy(() => import('@/pages/PolicyDetailPage').then((module) => ({ default: module.PolicyDetailPage })))
const PolicyCreatePage = lazy(() => import('@/pages/PolicyCreatePage').then((module) => ({ default: module.PolicyCreatePage })))
const LogsPage = lazy(() => import('@/pages/logs').then((module) => ({ default: module.LogsPage })))
const DeviceDetailPage = lazy(() => import('@/pages/DeviceDetailPage').then((module) => ({ default: module.DeviceDetailPage })))

function App() {
  return (
  <Suspense fallback={<LoadingState label="Loading page…" />}><Routes>
        <Route path="/landing" element={<LandingLanguageProvider><MarketingShell><LandingPage /></MarketingShell></LandingLanguageProvider>} />
        <Route path="/product" element={<MarketingShell><ProductPage /></MarketingShell>} />
        <Route path="/features" element={<MarketingShell><FeaturesPage /></MarketingShell>} />
        <Route path="/features/:slug" element={<MarketingShell><FeatureDetailPage /></MarketingShell>} />
        <Route path="/how-it-works" element={<MarketingShell><HowItWorksPage /></MarketingShell>} />
        <Route path="/schools" element={<MarketingShell><SchoolsPage /></MarketingShell>} />
        <Route path="/security" element={<MarketingShell><SecurityPage /></MarketingShell>} />
        <Route path="/architecture" element={<MarketingShell><ArchitecturePage /></MarketingShell>} />
        <Route path="/resources" element={<MarketingShell><ResourcesPage /></MarketingShell>} />
        <Route path="/about" element={<MarketingShell><AboutPage /></MarketingShell>} />
        <Route path="/contact" element={<MarketingShell><ContactPage /></MarketingShell>} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute><LanguageProvider><AdminShell /></LanguageProvider></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceUuid" element={<DeviceDetailPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/policies/new" element={<PolicyCreatePage />} />
          <Route path="/policies/:policyUuid" element={<PolicyDetailPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Route>
        <Route path="/" element={<LandingLanguageProvider><MarketingShell><LandingPage /></MarketingShell></LandingLanguageProvider>} />
        <Route path="/forbidden" element={<MessagePage title="Permission denied" message="Your account does not have permission to perform that action." />} />
        <Route path="*" element={<MessagePage title="Page not found" message="The requested page does not exist." />} />
      </Routes></Suspense>
  )
}

function MessagePage({ title, message }: { title: string; message: string }) {
  return <main className="grid min-h-screen place-items-center bg-slate-100 p-6"><div className="max-w-md text-center"><h1 className="text-3xl font-semibold">{title}</h1><p className="mt-3 text-slate-600">{message}</p><a href="/" className="mt-6 inline-block font-semibold text-emerald-700">Return to EduG</a></div></main>
}

export default App
