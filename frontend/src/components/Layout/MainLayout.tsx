import { useState, useEffect } from 'react'
import { Layout, theme } from 'antd'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore, useThemeStore } from '@/store'
import { useSiemWebSocket } from '@/hooks/useWebSocket'
import Sidebar from './Sidebar'
import Header from './Header'

const { Content } = Layout

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const { token: themeToken } = theme.useToken()
  const isDark = useThemeStore((state) => state.isDark)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  // Connect WebSocket for real-time updates
  const { isConnected, connectionStatus } = useSiemWebSocket({
    enabled: isAuthenticated,
  })

  // Update page title based on route
  useEffect(() => {
    const titles: Record<string, string> = {
      '/': 'Dashboard',
      '/events': 'События',
      '/alerts': 'Алерты',
      '/incidents': 'Инциденты',
      '/agents': 'Агенты',
      '/network': 'Сеть',
      '/rules': 'Правила',
      '/reports': 'Отчёты',
      '/users': 'Пользователи',
      '/settings': 'Настройки',
    }

    const title = titles[location.pathname] || 'SIEM'
    document.title = `${title} - SIEM System`
  }, [location])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar collapsed={collapsed} />
      <Layout style={{ marginLeft: collapsed ? 80 : 250, transition: 'margin-left 0.2s' }}>
        <Header collapsed={collapsed} setCollapsed={setCollapsed} wsStatus={connectionStatus} />
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: isDark ? themeToken.colorBgContainer : '#f0f2f5',
            borderRadius: themeToken.borderRadiusLG,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
