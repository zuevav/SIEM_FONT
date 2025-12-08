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
import ComingSoon from './pages/ComingSoon'
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
          colorPrimary: '#1890ff',
          borderRadius: 6,
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
            <Route
              path="reports"
              element={<ComingSoon title="Отчёты" description="Отчёты для регуляторов и аудита" />}
            />
            <Route
              path="users"
              element={<ComingSoon title="Пользователи" description="Управление пользователями системы" />}
            />
            <Route path="settings" element={<Settings />} />
            <Route path="documentation" element={<Documentation />} />
            <Route path="playbooks" element={<Playbooks />} />
            <Route path="playbook-executions" element={<PlaybookExecutions />} />
            <Route path="fim" element={<FileIntegrityMonitoring />} />
            <Route
              path="profile"
              element={<ComingSoon title="Профиль" description="Настройки профиля пользователя" />}
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
