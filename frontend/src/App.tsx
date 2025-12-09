import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import { useAuthStore, useThemeStore } from './store'
import PrivateRoute from './components/PrivateRoute'
import MainLayout from './components/Layout/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Events from './pages/Events'
import Alerts from './pages/Alerts'
import Incidents from './pages/Incidents'
import Agents from './pages/Agents'
import Settings from './pages/Settings'
import Documentation from './pages/Documentation'
import Playbooks from './pages/Playbooks'
import PlaybookExecutions from './pages/PlaybookExecutions'
import FileIntegrityMonitoring from './pages/FileIntegrityMonitoring'
import DetectionRules from './pages/DetectionRules'
import NetworkMonitoring from './pages/NetworkMonitoring'
import UserManagement from './pages/UserManagement'
import Profile from './pages/Profile'
import Reports from './pages/Reports'
import ActiveDirectory from './pages/ActiveDirectory'
import SoftwareRequests from './pages/SoftwareRequests'
import RemoteSessions from './pages/RemoteSessions'
import './App.css'

function App() {
  const loadUser = useAuthStore((state) => state.loadUser)
  const isDark = useThemeStore((state) => state.isDark)

  useEffect(() => {
    loadUser()
  }, [loadUser])

  return (
    <ConfigProvider
      locale={ruRU}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          // Apple-like colors
          colorPrimary: '#007AFF',
          colorSuccess: '#34C759',
          colorWarning: '#FF9500',
          colorError: '#FF3B30',
          colorInfo: '#5856D6',

          // Apple-like rounded corners
          borderRadius: 12,
          borderRadiusLG: 16,
          borderRadiusSM: 8,
          borderRadiusXS: 6,

          // Apple-like typography
          fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif",
          fontSize: 14,

          // Apple-like motion
          motionDurationFast: '0.1s',
          motionDurationMid: '0.2s',
          motionDurationSlow: '0.3s',

          // Spacing
          padding: 16,
          paddingLG: 24,
          paddingSM: 12,
          paddingXS: 8,
        },
        components: {
          Card: {
            borderRadiusLG: 16,
            boxShadowTertiary: '0 2px 8px rgba(0, 0, 0, 0.08)',
          },
          Button: {
            borderRadius: 10,
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 32,
          },
          Input: {
            borderRadius: 10,
            controlHeight: 40,
          },
          Select: {
            borderRadius: 10,
            controlHeight: 40,
          },
          Modal: {
            borderRadiusLG: 20,
          },
          Notification: {
            borderRadiusLG: 16,
          },
          Message: {
            borderRadiusLG: 12,
          },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <MainLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="events" element={<Events />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="incidents" element={<Incidents />} />
            <Route path="agents" element={<Agents />} />
            <Route path="network" element={<NetworkMonitoring />} />
            <Route path="rules" element={<DetectionRules />} />
            <Route path="reports" element={<Reports />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="settings" element={<Settings />} />
            <Route path="documentation" element={<Documentation />} />
            <Route path="playbooks" element={<Playbooks />} />
            <Route path="playbook-executions" element={<PlaybookExecutions />} />
            <Route path="fim" element={<FileIntegrityMonitoring />} />
            <Route path="profile" element={<Profile />} />
            <Route path="active-directory" element={<ActiveDirectory />} />
            <Route path="software-requests" element={<SoftwareRequests />} />
            <Route path="remote-sessions" element={<RemoteSessions />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
