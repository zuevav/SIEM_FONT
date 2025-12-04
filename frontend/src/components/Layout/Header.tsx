import { Layout, Button, Space, Avatar, Dropdown, Badge, Popover, List, Typography, Tag } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  BulbOutlined,
  WifiOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuthStore, useNotificationsStore, useThemeStore } from '@/store'
import { formatRelativeTime } from '@/utils/formatters'

const { Header: AntHeader } = Layout
const { Text } = Typography

interface HeaderProps {
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void
  wsStatus?: string
}

export default function Header({ collapsed, setCollapsed, wsStatus }: HeaderProps) {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const notifications = useNotificationsStore((state) => state.notifications)
  const unreadCount = useNotificationsStore((state) => state.unreadCount)
  const markAsRead = useNotificationsStore((state) => state.markAsRead)
  const markAllAsRead = useNotificationsStore((state) => state.markAllAsRead)
  const { isDark, toggleTheme } = useThemeStore()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Профиль',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Настройки',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выход',
      onClick: handleLogout,
      danger: true,
    },
  ]

  const notificationsContent = (
    <div style={{ width: 380, maxHeight: 400, overflow: 'auto' }}>
      <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text strong>Уведомления ({unreadCount})</Text>
        {unreadCount > 0 && (
          <Button type="link" size="small" onClick={markAllAsRead}>
            Отметить все прочитанными
          </Button>
        )}
      </div>
      <List
        dataSource={notifications.slice(0, 10)}
        locale={{ emptyText: 'Нет уведомлений' }}
        renderItem={(item) => (
          <List.Item
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              background: item.read ? 'transparent' : 'rgba(24, 144, 255, 0.05)',
            }}
            onClick={() => markAsRead(item.id)}
          >
            <List.Item.Meta
              title={
                <Space>
                  <Text strong>{item.title}</Text>
                  {!item.read && <Badge status="processing" />}
                </Space>
              }
              description={
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text type="secondary">{item.message}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatRelativeTime(item.timestamp)}
                  </Text>
                </Space>
              }
            />
          </List.Item>
        )}
      />
      {notifications.length > 10 && (
        <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0', textAlign: 'center' }}>
          <Button type="link" size="small">
            Показать все
          </Button>
        </div>
      )}
    </div>
  )

  return (
    <AntHeader
      style={{
        padding: '0 24px',
        background: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 1,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        marginLeft: collapsed ? 80 : 250,
        width: collapsed ? 'calc(100% - 80px)' : 'calc(100% - 250px)',
        transition: 'all 0.2s',
      }}
    >
      <Space>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => setCollapsed(!collapsed)}
          style={{ fontSize: '16px', width: 64, height: 64 }}
        />
        {wsStatus && (
          <Tag icon={<WifiOutlined />} color={wsStatus === 'Подключено' ? 'success' : 'default'}>
            {wsStatus}
          </Tag>
        )}
      </Space>

      <Space size="large">
        <Button
          type="text"
          icon={<BulbOutlined />}
          onClick={toggleTheme}
          title={isDark ? 'Светлая тема' : 'Тёмная тема'}
        />

        <Popover content={notificationsContent} title={null} trigger="click" placement="bottomRight">
          <Badge count={unreadCount} overflowCount={99}>
            <Button type="text" icon={<BellOutlined />} />
          </Badge>
        </Popover>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} />
            <Space direction="vertical" size={0}>
              <Text strong>{user?.Username || 'User'}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {user?.Role || 'viewer'}
              </Text>
            </Space>
          </Space>
        </Dropdown>
      </Space>
    </AntHeader>
  )
}
