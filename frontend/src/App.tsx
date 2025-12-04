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
import Agents from './pages/Agents'
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
            <Route
              path="incidents"
              element={<ComingSoon title="Инциденты" description="Управление инцидентами информационной безопасности" />}
            />
            <Route path="agents" element={<Agents />} />
            <Route
              path="network"
              element={<ComingSoon title="Мониторинг сети" description="Мониторинг сетевых устройств (SNMP, Syslog, NetFlow)" />}
            />
            <Route
              path="rules"
              element={<ComingSoon title="Правила детекции" description="Управление правилами обнаружения угроз" />}
            />
            <Route
              path="reports"
              element={<ComingSoon title="Отчёты" description="Отчёты для регуляторов и аудита" />}
            />
            <Route
              path="users"
              element={<ComingSoon title="Пользователи" description="Управление пользователями системы" />}
            />
            <Route
              path="settings"
              element={<ComingSoon title="Настройки" description="Настройки системы" />}
            />
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
