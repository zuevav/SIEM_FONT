import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  Card,
  Button,
  Input,
  List,
  Tag,
  Typography,
  Space,
  Spin,
  Result,
  Modal,
  Form,
  message,
  Tabs,
  Badge,
  Empty,
  Tooltip,
  Row,
  Col,
} from 'antd'
import {
  AppstoreOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  InfoCircleOutlined,
  DesktopOutlined,
  UserOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

interface StoreApp {
  app_id: number
  app_guid: string
  name: string
  display_name: string
  description: string
  publisher: string
  version: string
  category: string
  app_type: string
  icon_url: string
  is_featured: boolean
  requires_reboot: boolean
  can_install: boolean
  request_status: string | null
  request_id: number | null
}

interface UserInfo {
  user_name: string
  display_name: string
  department: string
}

export default function UserAppStore() {
  const { agentId } = useParams<{ agentId: string }>()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [apps, setApps] = useState<StoreApp[]>([])
  const [filteredApps, setFilteredApps] = useState<StoreApp[]>([])
  const [error, setError] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedApp, setSelectedApp] = useState<StoreApp | null>(null)
  const [requestModalOpen, setRequestModalOpen] = useState(false)
  const [installModalOpen, setInstallModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [userInfo, setUserInfo] = useState<UserInfo>({
    user_name: searchParams.get('user') || '',
    display_name: searchParams.get('name') || '',
    department: searchParams.get('dept') || '',
  })
  const [form] = Form.useForm()

  const categories = [
    { key: 'all', label: 'Все приложения' },
    { key: 'Офис', label: 'Офис' },
    { key: 'Разработка', label: 'Разработка' },
    { key: 'Утилиты', label: 'Утилиты' },
    { key: 'Мультимедиа', label: 'Мультимедиа' },
    { key: 'Безопасность', label: 'Безопасность' },
    { key: 'Коммуникации', label: 'Коммуникации' },
  ]

  const fetchApps = async () => {
    if (!agentId) return

    try {
      setLoading(true)
      const response = await fetch(`/api/v1/ad/appstore/apps/client?agent_id=${agentId}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Ошибка загрузки приложений')
      }
      const data = await response.json()
      setApps(data)
      setFilteredApps(data)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchApps()
  }, [agentId])

  useEffect(() => {
    let filtered = apps

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(app => app.category === selectedCategory)
    }

    // Filter by search text
    if (searchText) {
      const lower = searchText.toLowerCase()
      filtered = filtered.filter(
        app =>
          app.display_name.toLowerCase().includes(lower) ||
          app.description.toLowerCase().includes(lower) ||
          app.publisher.toLowerCase().includes(lower)
      )
    }

    setFilteredApps(filtered)
  }, [apps, selectedCategory, searchText])

  const getStatusTag = (app: StoreApp) => {
    if (app.can_install) {
      return <Tag color="success" icon={<CheckCircleOutlined />}>Доступно</Tag>
    }
    switch (app.request_status) {
      case 'pending':
        return <Tag color="warning" icon={<ClockCircleOutlined />}>Ожидает одобрения</Tag>
      case 'approved':
        return <Tag color="success" icon={<CheckCircleOutlined />}>Одобрено</Tag>
      case 'denied':
        return <Tag color="error" icon={<CloseCircleOutlined />}>Отклонено</Tag>
      default:
        return <Tag color="blue" icon={<InfoCircleOutlined />}>По запросу</Tag>
    }
  }

  const handleRequestSubmit = async (values: { reason: string; display_name: string; department: string }) => {
    if (!selectedApp || !agentId) return

    setSubmitting(true)
    try {
      const response = await fetch('/api/v1/ad/appstore/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_id: selectedApp.app_id,
          agent_id: agentId,
          computer_name: searchParams.get('computer') || 'Unknown',
          user_name: userInfo.user_name || 'unknown',
          user_display_name: values.display_name,
          user_department: values.department,
          request_reason: values.reason,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Ошибка отправки запроса')
      }

      const data = await response.json()
      message.success(`Запрос #${data.request_id} успешно отправлен!`)
      setRequestModalOpen(false)
      form.resetFields()
      fetchApps()
    } catch (err: any) {
      message.error(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleInstall = async () => {
    if (!selectedApp || !agentId) return

    setSubmitting(true)
    try {
      // First create an install request
      const response = await fetch('/api/v1/ad/appstore/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_id: selectedApp.app_id,
          agent_id: agentId,
          computer_name: searchParams.get('computer') || 'Unknown',
          user_name: userInfo.user_name || 'unknown',
          user_display_name: userInfo.display_name || userInfo.user_name,
          user_department: userInfo.department || '',
          request_reason: 'Прямая установка из веб-магазина',
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Ошибка запроса установки')
      }

      const data = await response.json()

      if (data.can_install && data.install_info) {
        message.info('Установка инициирована. Приложение будет установлено агентом на вашем компьютере.')
        setInstallModalOpen(false)
      } else {
        message.success(`Запрос #${data.request_id} отправлен на одобрение`)
        setInstallModalOpen(false)
      }

      fetchApps()
    } catch (err: any) {
      message.error(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const openAppDetails = (app: StoreApp) => {
    setSelectedApp(app)
    if (app.can_install || app.request_status === 'approved') {
      setInstallModalOpen(true)
    } else {
      setRequestModalOpen(true)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
          padding: 20,
        }}
      >
        <Card style={{ maxWidth: 500, width: '100%', borderRadius: 16 }}>
          <Result
            status="error"
            title="Ошибка загрузки"
            subTitle={error}
            extra={
              <Button type="primary" onClick={fetchApps}>
                Повторить
              </Button>
            }
          />
        </Card>
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
        padding: '20px',
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        {/* Header */}
        <Card
          style={{
            borderRadius: 20,
            marginBottom: 20,
            boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          }}
        >
          <Row align="middle" gutter={16}>
            <Col>
              <AppstoreOutlined style={{ fontSize: 48, color: '#007AFF' }} />
            </Col>
            <Col flex="auto">
              <Title level={2} style={{ margin: 0 }}>
                Магазин приложений
              </Title>
              <Text type="secondary">
                Выберите приложение для установки на ваш компьютер
              </Text>
            </Col>
            <Col>
              <Space>
                <DesktopOutlined />
                <Text>{searchParams.get('computer') || agentId}</Text>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* Search and Filters */}
        <Card style={{ borderRadius: 16, marginBottom: 20 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Input
              size="large"
              placeholder="Поиск приложений..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{ borderRadius: 12 }}
            />
            <Tabs
              activeKey={selectedCategory}
              onChange={setSelectedCategory}
              items={categories.map(cat => ({
                key: cat.key,
                label: (
                  <span>
                    {cat.label}
                    {cat.key !== 'all' && (
                      <Badge
                        count={apps.filter(a => a.category === cat.key).length}
                        style={{ marginLeft: 8 }}
                        showZero={false}
                      />
                    )}
                  </span>
                ),
              }))}
            />
          </Space>
        </Card>

        {/* Apps Grid */}
        {filteredApps.length === 0 ? (
          <Card style={{ borderRadius: 16 }}>
            <Empty description="Приложения не найдены" />
          </Card>
        ) : (
          <List
            grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3, xl: 4, xxl: 4 }}
            dataSource={filteredApps}
            renderItem={app => (
              <List.Item>
                <Card
                  hoverable
                  style={{
                    borderRadius: 16,
                    overflow: 'hidden',
                    height: '100%',
                  }}
                  onClick={() => openAppDetails(app)}
                  cover={
                    <div
                      style={{
                        height: 100,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%)',
                      }}
                    >
                      {app.icon_url ? (
                        <img
                          src={app.icon_url}
                          alt={app.display_name}
                          style={{ maxHeight: 64, maxWidth: 64 }}
                        />
                      ) : (
                        <AppstoreOutlined style={{ fontSize: 48, color: '#999' }} />
                      )}
                    </div>
                  }
                >
                  <Card.Meta
                    title={
                      <Space>
                        <Text strong ellipsis style={{ maxWidth: 150 }}>
                          {app.display_name}
                        </Text>
                        {app.is_featured && <Tag color="gold">Featured</Tag>}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {app.publisher} • v{app.version}
                        </Text>
                        <Paragraph
                          ellipsis={{ rows: 2 }}
                          style={{ marginBottom: 8, fontSize: 12 }}
                        >
                          {app.description}
                        </Paragraph>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Tag>{app.category}</Tag>
                          {getStatusTag(app)}
                        </div>
                      </Space>
                    }
                  />
                </Card>
              </List.Item>
            )}
          />
        )}

        {/* Request Modal */}
        <Modal
          title={
            <Space>
              <AppstoreOutlined />
              <span>Запрос на установку</span>
            </Space>
          }
          open={requestModalOpen}
          onCancel={() => setRequestModalOpen(false)}
          footer={null}
          width={500}
        >
          {selectedApp && (
            <Form
              form={form}
              layout="vertical"
              onFinish={handleRequestSubmit}
              initialValues={{
                display_name: userInfo.display_name,
                department: userInfo.department,
              }}
            >
              <Card size="small" style={{ marginBottom: 16, background: '#f5f5f5' }}>
                <Space direction="vertical">
                  <Text strong style={{ fontSize: 16 }}>{selectedApp.display_name}</Text>
                  <Text type="secondary">{selectedApp.publisher} • v{selectedApp.version}</Text>
                  <Paragraph style={{ marginBottom: 0 }}>{selectedApp.description}</Paragraph>
                </Space>
              </Card>

              {selectedApp.request_status === 'denied' && (
                <Card size="small" style={{ marginBottom: 16, background: '#fff2f0', borderColor: '#ffccc7' }}>
                  <Text type="danger">
                    Предыдущий запрос был отклонён. Вы можете отправить новый запрос с более подробным обоснованием.
                  </Text>
                </Card>
              )}

              <Form.Item
                name="display_name"
                label="Ваше имя"
                rules={[{ required: true, message: 'Введите ваше имя' }]}
              >
                <Input prefix={<UserOutlined />} placeholder="Иван Иванов" />
              </Form.Item>

              <Form.Item name="department" label="Отдел">
                <Input placeholder="IT отдел" />
              </Form.Item>

              <Form.Item
                name="reason"
                label="Причина запроса"
                rules={[{ required: true, message: 'Укажите причину запроса' }]}
              >
                <TextArea
                  rows={4}
                  placeholder="Опишите, для чего вам нужно это приложение..."
                />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setRequestModalOpen(false)}>Отмена</Button>
                  <Button type="primary" htmlType="submit" loading={submitting}>
                    Отправить запрос
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          )}
        </Modal>

        {/* Install Modal */}
        <Modal
          title={
            <Space>
              <DownloadOutlined />
              <span>Установка приложения</span>
            </Space>
          }
          open={installModalOpen}
          onCancel={() => setInstallModalOpen(false)}
          footer={[
            <Button key="cancel" onClick={() => setInstallModalOpen(false)}>
              Отмена
            </Button>,
            <Button
              key="install"
              type="primary"
              icon={<DownloadOutlined />}
              loading={submitting}
              onClick={handleInstall}
            >
              Установить
            </Button>,
          ]}
          width={500}
        >
          {selectedApp && (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Card size="small" style={{ background: '#f5f5f5' }}>
                <Space direction="vertical">
                  <Text strong style={{ fontSize: 16 }}>{selectedApp.display_name}</Text>
                  <Text type="secondary">{selectedApp.publisher} • v{selectedApp.version}</Text>
                  <Paragraph style={{ marginBottom: 0 }}>{selectedApp.description}</Paragraph>
                </Space>
              </Card>

              <div>
                <Text>
                  Приложение будет установлено автоматически на ваш компьютер.
                </Text>
                {selectedApp.requires_reboot && (
                  <div style={{ marginTop: 8 }}>
                    <Tag color="warning">Требуется перезагрузка</Tag>
                  </div>
                )}
              </div>
            </Space>
          )}
        </Modal>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: 40, marginBottom: 20 }}>
          <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>
            SIEM App Store • Безопасная установка корпоративного ПО
          </Text>
        </div>
      </div>
    </div>
  )
}
