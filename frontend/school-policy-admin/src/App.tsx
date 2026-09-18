import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminShell } from '@/components/layout/AdminShell'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/dashboard'
import { DevicesPage } from '@/pages/devices'
import { PoliciesPage } from '@/pages/policies'
import { PolicyDetailPage } from '@/pages/PolicyDetailPage'
import { LogsPage } from '@/pages/logs'
import { DeviceDetailPage } from '@/pages/DeviceDetailPage'
import { LandingPage } from '@/pages/LandingPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute><AdminShell /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceUuid" element={<DeviceDetailPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/policies/:policyUuid" element={<PolicyDetailPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Route>
        <Route path="/" element={<LandingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
