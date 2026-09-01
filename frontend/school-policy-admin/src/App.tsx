import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminShell } from '@/components/layout/AdminShell'
import { LoginPage } from '@/pages/LoginPage'
import { useAuth } from '@/hooks/useAuth'
import { DashboardPage } from '@/pages/dashboard'
import { DevicesPage } from '@/pages/devices'
import { PoliciesPage } from '@/pages/policies'
import { PolicyDetailPage } from '@/pages/PolicyDetailPage'
import { LogsPage } from '@/pages/logs'
import { DeviceDetailPage } from '@/pages/DeviceDetailPage'

function App() {
  const { isAuthenticated } = useAuth()

  return (
    <BrowserRouter>
      <Routes>
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
        <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
