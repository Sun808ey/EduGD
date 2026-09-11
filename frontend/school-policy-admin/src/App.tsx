import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminShell } from '@/components/layout/AdminShell'
import { LoginPage } from '@/pages/LoginPage'
import { useAuth } from '@/hooks/useAuth'
import { LoadingState } from '@/components/ui/AsyncState'

const DashboardPage = lazy(() => import('@/pages/dashboard').then((module) => ({ default: module.DashboardPage })))
const DevicesPage = lazy(() => import('@/pages/devices').then((module) => ({ default: module.DevicesPage })))
const PoliciesPage = lazy(() => import('@/pages/policies').then((module) => ({ default: module.PoliciesPage })))
const PolicyDetailPage = lazy(() => import('@/pages/PolicyDetailPage').then((module) => ({ default: module.PolicyDetailPage })))
const LogsPage = lazy(() => import('@/pages/logs').then((module) => ({ default: module.LogsPage })))
const DeviceDetailPage = lazy(() => import('@/pages/DeviceDetailPage').then((module) => ({ default: module.DeviceDetailPage })))

function App() {
  const { isAuthenticated } = useAuth()

  return (
      <Suspense fallback={<LoadingState label="Loading page…" />}><Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute><AdminShell /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceUuid" element={<DeviceDetailPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/policies/:policyUuid" element={<PolicyDetailPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Route>
        <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
        <Route path="/forbidden" element={<MessagePage title="Permission denied" message="Your account does not have permission to perform that action." />} />
        <Route path="*" element={<MessagePage title="Page not found" message="The requested page does not exist." />} />
      </Routes></Suspense>
  )
}

function MessagePage({ title, message }: { title: string; message: string }) {
  return <main className="grid min-h-screen place-items-center bg-slate-100 p-6"><div className="max-w-md text-center"><h1 className="text-3xl font-semibold">{title}</h1><p className="mt-3 text-slate-600">{message}</p><a href="/" className="mt-6 inline-block font-semibold text-emerald-700">Return to EduG</a></div></main>
}

export default App
