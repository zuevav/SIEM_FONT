/**
 * Active Directory Page
 * View AD users, computers, and groups synchronized from Active Directory
 */

import { useState, useEffect } from 'react'
import {
  Card,
  Tabs,
  Table,
  Tag,
  Space,
  Input,
  Select,
  Button,
  Badge,
  Statistic,
  Row,
  Col,
  Typography,
  Tooltip,
  Modal,
  Descriptions,
  Alert,
  message,
} from 'antd'
import {
  UserOutlined,
  DesktopOutlined,
  TeamOutlined,
  SearchOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LockOutlined,
  ExclamationCircleOutlined,
  CloudServerOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { TabPane } = Tabs
const { Option } = Select

interface ADUser {
  ADUserId: number
  ObjectGUID: string
  SamAccountName: string
  UserPrincipalName: string
  DisplayName: string
  FirstName: string
  LastName: string
  Email: string
  Phone: string
  Department: string
  Title: string
  ManagerDisplayName: string
  Company: string
  OrganizationalUnit: string
  Domain: string
  IsEnabled: boolean
  IsLocked: boolean
  LastLogon: string
  RiskScore: number
}

interface ADComputer {
  ADComputerId: number
  ObjectGUID: string
  Name: string
  DNSHostName: string
  Description: string
  IPv4Address: string
  OperatingSystem: string
  OperatingSystemVersion: string
  OrganizationalUnit: string
  Domain: string
  IsEnabled: boolean
  LastLogon: string
  AgentId: string | null
  CriticalityLevel: string
}

interface ADGroup {
  ADGroupId: number
  Name: string
  SamAccountName: string
  Description: string
  GroupCategory: string
  GroupScope: string
  Domain: string
  MemberCount: number
  IsPrivileged: boolean
}

interface ADStats {
  users: {
    total: number
    enabled: number
    disabled: number
    locked: number
  }
  computers: {
    total: number
    enabled: number
    with_agent: number
  }
  groups: {
    total: number
    privileged: number
  }
  software_requests: {
    pending: number
    approved: number
    denied: number
  }
}

export default function ActiveDirectory() {
  const [activeTab, setActiveTab] = useState('users')
  const [users, setUsers] = useState<ADUser[]>([])
  const [computers, setComputers] = useState<ADComputer[]>([])
  const [groups, setGroups] = useState<ADGroup[]>([])
  const [stats, setStats] = useState<ADStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // Pagination
  const [userPage, setUserPage] = useState(1)
  const [userTotal, setUserTotal] = useState(0)
  const [computerPage, setComputerPage] = useState(1)
  const [computerTotal, setComputerTotal] = useState(0)
  const [groupPage, setGroupPage] = useState(1)
  const [groupTotal, setGroupTotal] = useState(0)
  const pageSize = 50

  // Filters
  const [searchText, setSearchText] = useState('')
  const [departments, setDepartments] = useState<string[]>([])
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>()
  const [enabledOnly, setEnabledOnly] = useState(true)
  const [hasAgentFilter, setHasAgentFilter] = useState<boolean | undefined>()

  // Detail modal
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedItem, setSelectedItem] = useState<ADUser | ADComputer | ADGroup | null>(null)
  const [selectedType, setSelectedType] = useState<'user' | 'computer' | 'group'>('user')

  // Load stats
  const loadStats = async () => {
    try {
      const data = await apiService.client.get('/ad/stats')
      setStats(data.data)
    } catch (error) {
      console.error('Failed to load AD stats:', error)
    }
  }

  // Load users
  const loadUsers = async () => {
    setLoading(true)
    try {
      const params = {
        page: userPage,
        page_size: pageSize,
        search: searchText || undefined,
        department: selectedDepartment || undefined,
        enabled_only: enabledOnly,
      }
      const response = await apiService.client.get('/ad/users', { params })
      setUsers(response.data.items)
      setUserTotal(response.data.total)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load computers
  const loadComputers = async () => {
    setLoading(true)
    try {
      const params = {
        page: computerPage,
        page_size: pageSize,
        search: searchText || undefined,
        enabled_only: enabledOnly,
        has_agent: hasAgentFilter,
      }
      const response = await apiService.client.get('/ad/computers', { params })
      setComputers(response.data.items)
      setComputerTotal(response.data.total)
    } catch (error) {
      console.error('Failed to load computers:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load groups
  const loadGroups = async () => {
    setLoading(true)
    try {
      const params = {
        page: groupPage,
        page_size: pageSize,
        search: searchText || undefined,
      }
      const response = await apiService.client.get('/ad/groups', { params })
      setGroups(response.data.items)
      setGroupTotal(response.data.total)
    } catch (error) {
      console.error('Failed to load groups:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load departments
  const loadDepartments = async () => {
    try {
      const response = await apiService.client.get('/ad/users/departments/list')
      setDepartments(response.data)
    } catch (error) {
      console.error('Failed to load departments:', error)
    }
  }

  // Start sync
  const handleSync = async () => {
    setSyncing(true)
    try {
      await apiService.client.post('/ad/sync', null, { params: { sync_type: 'full' } })
      message.success('Синхронизация AD запущена')
    } catch (error) {
      message.error('Ошибка запуска синхронизации')
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    loadStats()
    loadDepartments()
  }, [])

  useEffect(() => {
    if (activeTab === 'users') loadUsers()
    else if (activeTab === 'computers') loadComputers()
    else if (activeTab === 'groups') loadGroups()
  }, [activeTab, userPage, computerPage, groupPage, searchText, selectedDepartment, enabledOnly, hasAgentFilter])

  // User columns
  const userColumns: ColumnsType<ADUser> = [
    {
      title: 'Пользователь',
      key: 'user',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.DisplayName || record.SamAccountName}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.SamAccountName}</Text>
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'Email',
      key: 'Email',
      ellipsis: true,
    },
    {
      title: 'Отдел',
      dataIndex: 'Department',
      key: 'Department',
      ellipsis: true,
    },
    {
      title: 'Должность',
      dataIndex: 'Title',
      key: 'Title',
      ellipsis: true,
    },
    {
      title: 'Домен',
      dataIndex: 'Domain',
      key: 'Domain',
    },
    {
      title: 'Статус',
      key: 'status',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.IsEnabled ? (
            <Tag color="success" icon={<CheckCircleOutlined />}>Активен</Tag>
          ) : (
            <Tag color="default" icon={<CloseCircleOutlined />}>Отключён</Tag>
          )}
          {record.IsLocked && (
            <Tag color="error" icon={<LockOutlined />}>Заблокирован</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Последний вход',
      dataIndex: 'LastLogon',
      key: 'LastLogon',
      width: 150,
      render: (date: string) => date ? dayjs(date).format('DD.MM.YYYY HH:mm') : '-',
    },
    {
      title: 'Риск',
      dataIndex: 'RiskScore',
      key: 'RiskScore',
      width: 80,
      render: (score: number) => {
        const color = score >= 70 ? 'red' : score >= 40 ? 'orange' : 'green'
        return <Tag color={color}>{score}</Tag>
      },
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedItem(record)
            setSelectedType('user')
            setDetailModalVisible(true)
          }}
        >
          Подробнее
        </Button>
      ),
    },
  ]

  // Computer columns
  const computerColumns: ColumnsType<ADComputer> = [
    {
      title: 'Компьютер',
      key: 'computer',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.Name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.DNSHostName}</Text>
        </Space>
      ),
    },
    {
      title: 'IP-адрес',
      dataIndex: 'IPv4Address',
      key: 'IPv4Address',
    },
    {
      title: 'ОС',
      key: 'os',
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.OperatingSystem}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.OperatingSystemVersion}</Text>
        </Space>
      ),
    },
    {
      title: 'OU',
      dataIndex: 'OrganizationalUnit',
      key: 'OrganizationalUnit',
      ellipsis: true,
    },
    {
      title: 'Статус',
      key: 'status',
      width: 120,
      render: (_, record) => (
        record.IsEnabled ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>Активен</Tag>
        ) : (
          <Tag color="default" icon={<CloseCircleOutlined />}>Отключён</Tag>
        )
      ),
    },
    {
      title: 'Агент',
      key: 'agent',
      width: 100,
      render: (_, record) => (
        record.AgentId ? (
          <Tag color="success" icon={<CloudServerOutlined />}>Установлен</Tag>
        ) : (
          <Tag color="default">Нет</Tag>
        )
      ),
    },
    {
      title: 'Критичность',
      dataIndex: 'CriticalityLevel',
      key: 'CriticalityLevel',
      width: 100,
      render: (level: string) => {
        const colors: Record<string, string> = {
          critical: 'red',
          high: 'orange',
          medium: 'blue',
          low: 'green',
        }
        return <Tag color={colors[level] || 'default'}>{level}</Tag>
      },
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedItem(record)
            setSelectedType('computer')
            setDetailModalVisible(true)
          }}
        >
          Подробнее
        </Button>
      ),
    },
  ]

  // Group columns
  const groupColumns: ColumnsType<ADGroup> = [
    {
      title: 'Группа',
      key: 'group',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <Text strong>{record.Name}</Text>
            {record.IsPrivileged && (
              <Tag color="red" icon={<ExclamationCircleOutlined />}>Привилегированная</Tag>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.Description}</Text>
        </Space>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'GroupCategory',
      key: 'GroupCategory',
      width: 120,
    },
    {
      title: 'Область',
      dataIndex: 'GroupScope',
      key: 'GroupScope',
      width: 120,
    },
    {
      title: 'Домен',
      dataIndex: 'Domain',
      key: 'Domain',
    },
    {
      title: 'Участников',
      dataIndex: 'MemberCount',
      key: 'MemberCount',
      width: 120,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#1890ff' }} />
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedItem(record)
            setSelectedType('group')
            setDetailModalVisible(true)
          }}
        >
          Подробнее
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={3} style={{ margin: 0 }}>Active Directory</Title>
          <Button
            type="primary"
            icon={<SyncOutlined spin={syncing} />}
            onClick={handleSync}
            loading={syncing}
          >
            Синхронизировать AD
          </Button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Пользователи AD"
                  value={stats.users.total}
                  prefix={<UserOutlined />}
                  suffix={
                    <Space>
                      <Tag color="success">{stats.users.enabled} активных</Tag>
                      {stats.users.locked > 0 && <Tag color="error">{stats.users.locked} заблок.</Tag>}
                    </Space>
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Компьютеры AD"
                  value={stats.computers.total}
                  prefix={<DesktopOutlined />}
                  suffix={
                    <Tag color="blue">{stats.computers.with_agent} с агентом</Tag>
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Группы AD"
                  value={stats.groups.total}
                  prefix={<TeamOutlined />}
                  suffix={
                    <Tag color="red">{stats.groups.privileged} привилег.</Tag>
                  }
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Запросы на ПО"
                  value={stats.software_requests.pending}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: stats.software_requests.pending > 0 ? '#faad14' : '#52c41a' }}
                  suffix={<Text type="secondary">ожидают</Text>}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* Main Content */}
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane
              tab={<span><UserOutlined />Пользователи ({userTotal})</span>}
              key="users"
            >
              {/* Filters */}
              <Space style={{ marginBottom: 16 }} wrap>
                <Input
                  placeholder="Поиск по имени, email..."
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  style={{ width: 250 }}
                  allowClear
                />
                <Select
                  placeholder="Отдел"
                  value={selectedDepartment}
                  onChange={setSelectedDepartment}
                  style={{ width: 200 }}
                  allowClear
                >
                  {departments.map((d) => (
                    <Option key={d} value={d}>{d}</Option>
                  ))}
                </Select>
                <Select
                  value={enabledOnly}
                  onChange={setEnabledOnly}
                  style={{ width: 150 }}
                >
                  <Option value={true}>Только активные</Option>
                  <Option value={false}>Все</Option>
                </Select>
                <Button icon={<ReloadOutlined />} onClick={loadUsers}>Обновить</Button>
              </Space>

              <Table
                columns={userColumns}
                dataSource={users}
                rowKey="ADUserId"
                loading={loading}
                pagination={{
                  current: userPage,
                  total: userTotal,
                  pageSize,
                  onChange: setUserPage,
                  showTotal: (total) => `Всего ${total} пользователей`,
                }}
                size="middle"
              />
            </TabPane>

            <TabPane
              tab={<span><DesktopOutlined />Компьютеры ({computerTotal})</span>}
              key="computers"
            >
              <Space style={{ marginBottom: 16 }} wrap>
                <Input
                  placeholder="Поиск по имени..."
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  style={{ width: 250 }}
                  allowClear
                />
                <Select
                  placeholder="Агент"
                  value={hasAgentFilter}
                  onChange={setHasAgentFilter}
                  style={{ width: 180 }}
                  allowClear
                >
                  <Option value={true}>С агентом</Option>
                  <Option value={false}>Без агента</Option>
                </Select>
                <Select
                  value={enabledOnly}
                  onChange={setEnabledOnly}
                  style={{ width: 150 }}
                >
                  <Option value={true}>Только активные</Option>
                  <Option value={false}>Все</Option>
                </Select>
                <Button icon={<ReloadOutlined />} onClick={loadComputers}>Обновить</Button>
              </Space>

              <Table
                columns={computerColumns}
                dataSource={computers}
                rowKey="ADComputerId"
                loading={loading}
                pagination={{
                  current: computerPage,
                  total: computerTotal,
                  pageSize,
                  onChange: setComputerPage,
                  showTotal: (total) => `Всего ${total} компьютеров`,
                }}
                size="middle"
              />
            </TabPane>

            <TabPane
              tab={<span><TeamOutlined />Группы ({groupTotal})</span>}
              key="groups"
            >
              <Space style={{ marginBottom: 16 }} wrap>
                <Input
                  placeholder="Поиск по названию..."
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  style={{ width: 250 }}
                  allowClear
                />
                <Button icon={<ReloadOutlined />} onClick={loadGroups}>Обновить</Button>
              </Space>

              <Table
                columns={groupColumns}
                dataSource={groups}
                rowKey="ADGroupId"
                loading={loading}
                pagination={{
                  current: groupPage,
                  total: groupTotal,
                  pageSize,
                  onChange: setGroupPage,
                  showTotal: (total) => `Всего ${total} групп`,
                }}
                size="middle"
              />
            </TabPane>
          </Tabs>
        </Card>
      </Space>

      {/* Detail Modal */}
      <Modal
        title={
          selectedType === 'user' ? 'Информация о пользователе' :
          selectedType === 'computer' ? 'Информация о компьютере' :
          'Информация о группе'
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Закрыть
          </Button>,
        ]}
        width={700}
      >
        {selectedItem && selectedType === 'user' && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Имя" span={2}>
              {(selectedItem as ADUser).DisplayName}
            </Descriptions.Item>
            <Descriptions.Item label="Логин">
              {(selectedItem as ADUser).SamAccountName}
            </Descriptions.Item>
            <Descriptions.Item label="UPN">
              {(selectedItem as ADUser).UserPrincipalName}
            </Descriptions.Item>
            <Descriptions.Item label="Email">
              {(selectedItem as ADUser).Email}
            </Descriptions.Item>
            <Descriptions.Item label="Телефон">
              {(selectedItem as ADUser).Phone}
            </Descriptions.Item>
            <Descriptions.Item label="Отдел">
              {(selectedItem as ADUser).Department}
            </Descriptions.Item>
            <Descriptions.Item label="Должность">
              {(selectedItem as ADUser).Title}
            </Descriptions.Item>
            <Descriptions.Item label="Руководитель" span={2}>
              {(selectedItem as ADUser).ManagerDisplayName}
            </Descriptions.Item>
            <Descriptions.Item label="Домен">
              {(selectedItem as ADUser).Domain}
            </Descriptions.Item>
            <Descriptions.Item label="OU">
              {(selectedItem as ADUser).OrganizationalUnit}
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              {(selectedItem as ADUser).IsEnabled ? 'Активен' : 'Отключён'}
            </Descriptions.Item>
            <Descriptions.Item label="Заблокирован">
              {(selectedItem as ADUser).IsLocked ? 'Да' : 'Нет'}
            </Descriptions.Item>
            <Descriptions.Item label="Последний вход">
              {(selectedItem as ADUser).LastLogon
                ? dayjs((selectedItem as ADUser).LastLogon).format('DD.MM.YYYY HH:mm')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Оценка риска">
              <Tag color={(selectedItem as ADUser).RiskScore >= 70 ? 'red' : (selectedItem as ADUser).RiskScore >= 40 ? 'orange' : 'green'}>
                {(selectedItem as ADUser).RiskScore}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}

        {selectedItem && selectedType === 'computer' && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Имя" span={2}>
              {(selectedItem as ADComputer).Name}
            </Descriptions.Item>
            <Descriptions.Item label="DNS">
              {(selectedItem as ADComputer).DNSHostName}
            </Descriptions.Item>
            <Descriptions.Item label="IP-адрес">
              {(selectedItem as ADComputer).IPv4Address}
            </Descriptions.Item>
            <Descriptions.Item label="ОС" span={2}>
              {(selectedItem as ADComputer).OperatingSystem} {(selectedItem as ADComputer).OperatingSystemVersion}
            </Descriptions.Item>
            <Descriptions.Item label="Описание" span={2}>
              {(selectedItem as ADComputer).Description}
            </Descriptions.Item>
            <Descriptions.Item label="Домен">
              {(selectedItem as ADComputer).Domain}
            </Descriptions.Item>
            <Descriptions.Item label="OU">
              {(selectedItem as ADComputer).OrganizationalUnit}
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              {(selectedItem as ADComputer).IsEnabled ? 'Активен' : 'Отключён'}
            </Descriptions.Item>
            <Descriptions.Item label="Агент">
              {(selectedItem as ADComputer).AgentId ? 'Установлен' : 'Нет'}
            </Descriptions.Item>
            <Descriptions.Item label="Критичность">
              {(selectedItem as ADComputer).CriticalityLevel}
            </Descriptions.Item>
            <Descriptions.Item label="Последний вход">
              {(selectedItem as ADComputer).LastLogon
                ? dayjs((selectedItem as ADComputer).LastLogon).format('DD.MM.YYYY HH:mm')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}

        {selectedItem && selectedType === 'group' && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Название" span={2}>
              {(selectedItem as ADGroup).Name}
            </Descriptions.Item>
            <Descriptions.Item label="Описание" span={2}>
              {(selectedItem as ADGroup).Description}
            </Descriptions.Item>
            <Descriptions.Item label="Тип">
              {(selectedItem as ADGroup).GroupCategory}
            </Descriptions.Item>
            <Descriptions.Item label="Область">
              {(selectedItem as ADGroup).GroupScope}
            </Descriptions.Item>
            <Descriptions.Item label="Домен">
              {(selectedItem as ADGroup).Domain}
            </Descriptions.Item>
            <Descriptions.Item label="Участников">
              {(selectedItem as ADGroup).MemberCount}
            </Descriptions.Item>
            <Descriptions.Item label="Привилегированная" span={2}>
              {(selectedItem as ADGroup).IsPrivileged ? (
                <Tag color="red" icon={<ExclamationCircleOutlined />}>Да</Tag>
              ) : (
                <Tag color="default">Нет</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
