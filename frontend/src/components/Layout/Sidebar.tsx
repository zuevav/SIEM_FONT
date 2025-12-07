import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  AlertOutlined,
  FileTextOutlined,
  WarningOutlined,
  LaptopOutlined,
  GlobalOutlined,
  SettingOutlined,
  UserOutlined,
  FileSearchOutlined,
  SafetyOutlined,
  BookOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'

const { Sider } = Layout

interface SidebarProps {
  collapsed: boolean
}

type MenuItem = Required<MenuProps>['items'][number]

function getItem(
  label: React.ReactNode,
  key: string,
  icon?: React.ReactNode,
  children?: MenuItem[]
): MenuItem {
  return {
    key,
    icon,
    children,
    label,
  } as MenuItem
}

export default function Sidebar({ collapsed }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems: MenuItem[] = [
    getItem('Dashboard', '/', <DashboardOutlined />),
    getItem('События', '/events', <FileTextOutlined />),
    getItem('Алерты', '/alerts', <AlertOutlined />),
    getItem('Инциденты', '/incidents', <WarningOutlined />),
    getItem('Агенты', '/agents', <LaptopOutlined />),
    getItem('Сеть', '/network', <GlobalOutlined />),
    getItem('Правила', '/rules', <SafetyOutlined />),
    getItem('Отчёты', '/reports', <FileSearchOutlined />),
    getItem('Управление', 'management', <SettingOutlined />, [
      getItem('Пользователи', '/users', <UserOutlined />),
      getItem('Настройки', '/settings', <SettingOutlined />),
      getItem('Документация', '/documentation', <BookOutlined />),
    ]),
  ]

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    navigate(e.key)
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={(value) => {}}
      trigger={null}
      width={250}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
      }}
    >
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: collapsed ? '18px' : '20px',
          fontWeight: 'bold',
          color: '#fff',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {collapsed ? '🛡️' : '🛡️ SIEM'}
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        defaultOpenKeys={['management']}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </Sider>
  )
}
