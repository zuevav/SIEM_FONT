import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tooltip,
  Badge,
  Typography,
  Row,
  Col,
  Statistic,
  Descriptions,
  Popconfirm,
  Spin,
} from 'antd'
import {
  DesktopOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  CopyOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

const { Text, Title } = Typography
const { TextArea } = Input

interface RemoteSession {
  SessionId: number
  SessionGUID: string
  AgentId: string
  ComputerName: string
  ComputerIP: string
  TargetUserName: string
  TargetUserDisplayName: string
  InitiatedByName: string
  SessionType: string
  Reason: string
  TicketNumber: string
  Status: string
  RequestedAt: string
  UserRespondedAt: string | null
  ConnectedAt: string | null
  EndedAt: string | null
  ConnectionString: string | null
  ConnectionPassword: string | null
  Port: number | null
  UserConsented: boolean
  DurationSeconds: number | null
}

interface ADUser {
  ADUserId: number
  SamAccountName: string
  DisplayName: string
  Department: string
}

interface ADComputer {
  ADComputerId: number
  Name: string
  IPv4Address: string
  AgentId: string | null
}

export default function RemoteSessions() {
  const [sessions, setSessions] = useState<RemoteSession[]>([])
  const [activeSessions, setActiveSessions] = useState<RemoteSession[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedSession, setSelectedSession] = useState<RemoteSession | null>(null)
  const [users, setUsers] = useState<ADUser[]>([])
  const [computers, setComputers] = useState<ADComputer[]>([])
  const [form] = Form.useForm()

  const fetchSessions = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/remote-sessions?page_size=100', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setSessions(data.items || [])
    } catch (error) {
      message.error('Ошибка загрузки сессий')
    } finally {
      setLoading(false)
    }
  }

  const fetchActiveSessions = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/remote-sessions/active', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setActiveSessions(data || [])
    } catch (error) {
      console.error('Error fetching active sessions:', error)
    }
  }

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/users?page_size=200', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setUsers(data.items || [])
    } catch (error) {
      console.error('Error fetching users:', error)
    }
  }

  const fetchComputers = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/computers?has_agent=true&page_size=200', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setComputers(data.items || [])
    } catch (error) {
      console.error('Error fetching computers:', error)
    }
  }

  useEffect(() => {
    fetchSessions()
    fetchActiveSessions()
    fetchUsers()
    fetchComputers()

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchActiveSessions()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleCreateSession = async (values: any) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/remote-sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          target_user_id: values.target_user_id || null,
          target_computer_id: values.target_computer_id || null,
          session_type: values.session_type,
          reason: values.reason,
          ticket_number: values.ticket_number,
          record_session: values.record_session || false,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        message.success('Запрос на подключение отправлен')
        setCreateModalVisible(false)
        form.resetFields()
        fetchSessions()
        fetchActiveSessions()
      } else {
        message.error(data.detail || 'Ошибка создания сессии')
      }
    } catch (error) {
      message.error('Ошибка отправки запроса')
    }
  }

  const handleCancelSession = async (sessionGuid: string) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/remote-sessions/${sessionGuid}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        message.success('Сессия отменена')
        fetchSessions()
        fetchActiveSessions()
      } else {
        message.error('Ошибка отмены сессии')
      }
    } catch (error) {
      message.error('Ошибка отмены сессии')
    }
  }

  const handleEndSession = async (sessionGuid: string) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/remote-sessions/${sessionGuid}/end`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        message.success('Сессия завершена')
        fetchSessions()
        fetchActiveSessions()
      } else {
        message.error('Ошибка завершения сессии')
      }
    } catch (error) {
      message.error('Ошибка завершения сессии')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    message.success('Скопировано в буфер обмена')
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'processing', text: 'Ожидание' },
      connecting: { color: 'warning', text: 'Подключение' },
      active: { color: 'success', text: 'Активна' },
      completed: { color: 'default', text: 'Завершена' },
      user_declined: { color: 'error', text: 'Отклонена' },
      timeout: { color: 'error', text: 'Таймаут' },
      cancelled: { color: 'default', text: 'Отменена' },
      failed: { color: 'error', text: 'Ошибка' },
    }

    const config = statusConfig[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns: ColumnsType<RemoteSession> = [
    {
      title: 'Компьютер',
      dataIndex: 'ComputerName',
      key: 'computer',
      render: (name, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <DesktopOutlined />
            <Text strong>{name}</Text>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.ComputerIP}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Пользователь',
      dataIndex: 'TargetUserName',
      key: 'user',
      render: (name, record) => (
        <Space>
          <UserOutlined />
          {record.TargetUserDisplayName || name || '-'}
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'status',
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Инициатор',
      dataIndex: 'InitiatedByName',
      key: 'initiator',
    },
    {
      title: 'Причина',
      dataIndex: 'Reason',
      key: 'reason',
      ellipsis: true,
      render: (reason) => reason || '-',
    },
    {
      title: 'Время',
      dataIndex: 'RequestedAt',
      key: 'time',
      render: (time) => new Date(time).toLocaleString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Подробности">
            <Button
              icon={<EyeOutlined />}
              size="small"
              onClick={() => {
                setSelectedSession(record)
                setDetailModalVisible(true)
              }}
            />
          </Tooltip>

          {record.Status === 'connecting' && record.ConnectionString && (
            <Tooltip title="Подключиться">
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                size="small"
                onClick={() => {
                  // Open connection
                  if (record.ConnectionPassword) {
                    copyToClipboard(record.ConnectionPassword)
                    message.info('Пароль скопирован. Используйте msra.exe для подключения')
                  }
                }}
              >
                Connect
              </Button>
            </Tooltip>
          )}

          {['pending', 'connecting'].includes(record.Status) && (
            <Popconfirm
              title="Отменить запрос на подключение?"
              onConfirm={() => handleCancelSession(record.SessionGUID)}
            >
              <Button danger icon={<CloseCircleOutlined />} size="small" />
            </Popconfirm>
          )}

          {record.Status === 'active' && (
            <Popconfirm
              title="Завершить сессию?"
              onConfirm={() => handleEndSession(record.SessionGUID)}
            >
              <Button danger icon={<StopOutlined />} size="small">
                Завершить
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const activeCount = activeSessions.filter((s) => s.Status === 'active').length
  const pendingCount = activeSessions.filter((s) => s.Status === 'pending').length

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Активные сессии"
              value={activeCount}
              prefix={<PlayCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Ожидают ответа"
              value={pendingCount}
              prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Всего за сегодня"
              value={sessions.filter((s) => {
                const today = new Date().toDateString()
                return new Date(s.RequestedAt).toDateString() === today
              }).length}
              prefix={<DesktopOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Button
              type="primary"
              size="large"
              icon={<DesktopOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              Новое подключение
            </Button>
          </Card>
        </Col>
      </Row>

      {/* Active sessions alert */}
      {activeSessions.length > 0 && (
        <Card
          title={
            <Space>
              <Badge status="processing" />
              <span>Активные подключения</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
          size="small"
        >
          <Table
            dataSource={activeSessions}
            columns={columns}
            rowKey="SessionId"
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* All sessions */}
      <Card
        title="История подключений"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchSessions} loading={loading}>
            Обновить
          </Button>
        }
      >
        <Table
          dataSource={sessions}
          columns={columns}
          rowKey="SessionId"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      {/* Create session modal */}
      <Modal
        title="Новое удаленное подключение"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateSession}>
          <Form.Item
            name="target_computer_id"
            label="Компьютер"
            rules={[{ required: true, message: 'Выберите компьютер' }]}
          >
            <Select
              showSearch
              placeholder="Выберите компьютер с агентом"
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {computers
                .filter((c) => c.AgentId)
                .map((computer) => (
                  <Select.Option key={computer.ADComputerId} value={computer.ADComputerId}>
                    {computer.Name} ({computer.IPv4Address})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item name="target_user_id" label="Пользователь (опционально)">
            <Select
              showSearch
              allowClear
              placeholder="Выберите пользователя"
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {users.map((user) => (
                <Select.Option key={user.ADUserId} value={user.ADUserId}>
                  {user.DisplayName || user.SamAccountName} ({user.Department || 'Без отдела'})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="session_type"
            label="Тип подключения"
            initialValue="remote_assistance"
          >
            <Select>
              <Select.Option value="remote_assistance">
                Remote Assistance (с согласием пользователя)
              </Select.Option>
              <Select.Option value="screen_share">
                Только просмотр экрана
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="reason"
            label="Причина подключения"
            rules={[{ required: true, message: 'Укажите причину' }]}
          >
            <TextArea rows={3} placeholder="Опишите причину подключения..." />
          </Form.Item>

          <Form.Item name="ticket_number" label="Номер заявки (опционально)">
            <Input placeholder="INC-12345" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Отправить запрос
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>Отмена</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Session detail modal */}
      <Modal
        title="Детали сессии"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedSession && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="ID сессии" span={2}>
              <Text copyable>{selectedSession.SessionGUID}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Компьютер">
              {selectedSession.ComputerName}
            </Descriptions.Item>
            <Descriptions.Item label="IP">
              {selectedSession.ComputerIP}
            </Descriptions.Item>
            <Descriptions.Item label="Пользователь">
              {selectedSession.TargetUserDisplayName || selectedSession.TargetUserName || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              {getStatusTag(selectedSession.Status)}
            </Descriptions.Item>
            <Descriptions.Item label="Инициатор">
              {selectedSession.InitiatedByName}
            </Descriptions.Item>
            <Descriptions.Item label="Тип">
              {selectedSession.SessionType}
            </Descriptions.Item>
            <Descriptions.Item label="Причина" span={2}>
              {selectedSession.Reason || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Номер заявки">
              {selectedSession.TicketNumber || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Согласие пользователя">
              {selectedSession.UserConsented ? (
                <Tag color="green">Да</Tag>
              ) : (
                <Tag color="red">Нет</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Запрошено">
              {new Date(selectedSession.RequestedAt).toLocaleString('ru-RU')}
            </Descriptions.Item>
            <Descriptions.Item label="Ответ пользователя">
              {selectedSession.UserRespondedAt
                ? new Date(selectedSession.UserRespondedAt).toLocaleString('ru-RU')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Подключение">
              {selectedSession.ConnectedAt
                ? new Date(selectedSession.ConnectedAt).toLocaleString('ru-RU')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Завершение">
              {selectedSession.EndedAt
                ? new Date(selectedSession.EndedAt).toLocaleString('ru-RU')
                : '-'}
            </Descriptions.Item>
            {selectedSession.DurationSeconds && (
              <Descriptions.Item label="Длительность" span={2}>
                {Math.floor(selectedSession.DurationSeconds / 60)} мин{' '}
                {selectedSession.DurationSeconds % 60} сек
              </Descriptions.Item>
            )}
            {selectedSession.ConnectionPassword && selectedSession.Status === 'connecting' && (
              <Descriptions.Item label="Пароль для подключения" span={2}>
                <Space>
                  <Text code>{selectedSession.ConnectionPassword}</Text>
                  <Button
                    icon={<CopyOutlined />}
                    size="small"
                    onClick={() => copyToClipboard(selectedSession.ConnectionPassword!)}
                  >
                    Копировать
                  </Button>
                </Space>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
