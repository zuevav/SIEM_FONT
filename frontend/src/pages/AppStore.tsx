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
  Tabs,
  Popconfirm,
  Avatar,
  List,
  Descriptions,
  Switch,
} from 'antd'
import {
  AppstoreOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  StarOutlined,
  StarFilled,
  SafetyCertificateOutlined,
  WarningOutlined,
  UserOutlined,
  DesktopOutlined,
  FileZipOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

const { Text, Title, Paragraph } = Typography
const { TextArea } = Input
const { TabPane } = Tabs

interface AppStoreApp {
  AppId: number
  AppGUID: string
  Name: string
  DisplayName: string
  Description: string
  Publisher: string
  Version: string
  Category: string
  AppType: string
  InstallerType: string
  InstallerUrl: string
  InstallerPath: string
  SilentInstallArgs: string
  RequiresReboot: boolean
  IconUrl: string
  AddedByName: string
  AddedAt: string
  IsActive: boolean
  IsFeatured: boolean
  TotalInstalls: number
  PendingRequests: number
}

interface AppInstallRequest {
  RequestId: number
  RequestGUID: string
  AppId: number
  AppName: string
  AgentId: string
  ComputerName: string
  UserName: string
  UserDisplayName: string
  UserDepartment: string
  RequestReason: string
  RequestedAt: string
  Status: string
  ReviewedByName: string | null
  ReviewedAt: string | null
  AdminComment: string | null
  InstalledAt: string | null
}

const appCategories = [
  { value: 'productivity', label: 'Продуктивность' },
  { value: 'development', label: 'Разработка' },
  { value: 'utilities', label: 'Утилиты' },
  { value: 'communication', label: 'Коммуникации' },
  { value: 'graphics', label: 'Графика' },
  { value: 'office', label: 'Офис' },
  { value: 'security', label: 'Безопасность' },
  { value: 'other', label: 'Другое' },
]

const installerTypes = [
  { value: 'exe', label: 'EXE' },
  { value: 'msi', label: 'MSI' },
  { value: 'msix', label: 'MSIX' },
  { value: 'script', label: 'Скрипт' },
]

export default function AppStore() {
  const [apps, setApps] = useState<AppStoreApp[]>([])
  const [requests, setRequests] = useState<AppInstallRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [reviewModalVisible, setReviewModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedApp, setSelectedApp] = useState<AppStoreApp | null>(null)
  const [selectedRequest, setSelectedRequest] = useState<AppInstallRequest | null>(null)
  const [form] = Form.useForm()
  const [reviewForm] = Form.useForm()
  const [activeTab, setActiveTab] = useState('apps')
  const [pendingCount, setPendingCount] = useState(0)

  const fetchApps = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/appstore/apps?page_size=100&active_only=false', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setApps(data.items || [])
    } catch (error) {
      message.error('Ошибка загрузки приложений')
    } finally {
      setLoading(false)
    }
  }

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/appstore/requests?page_size=100', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setRequests(data.items || [])
    } catch (error) {
      message.error('Ошибка загрузки запросов')
    }
  }

  const fetchPendingCount = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/appstore/requests/pending/count', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setPendingCount(data.pending_count)
    } catch (error) {
      console.error('Error fetching pending count:', error)
    }
  }

  useEffect(() => {
    fetchApps()
    fetchRequests()
    fetchPendingCount()
  }, [])

  const handleCreateApp = async (values: any) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/appstore/apps', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: values.name,
          display_name: values.display_name,
          description: values.description,
          publisher: values.publisher,
          version: values.version,
          category: values.category,
          app_type: values.app_type,
          installer_type: values.installer_type,
          installer_url: values.installer_url,
          installer_path: values.installer_path,
          silent_install_args: values.silent_install_args,
          requires_reboot: values.requires_reboot || false,
          icon_url: values.icon_url,
          is_featured: values.is_featured || false,
        }),
      })

      if (response.ok) {
        message.success('Приложение добавлено в магазин')
        setCreateModalVisible(false)
        form.resetFields()
        fetchApps()
      } else {
        throw new Error('Failed to create app')
      }
    } catch (error) {
      message.error('Ошибка добавления приложения')
    }
  }

  const handleUpdateApp = async (values: any) => {
    if (!selectedApp) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/appstore/apps/${selectedApp.AppId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(values),
      })

      if (response.ok) {
        message.success('Приложение обновлено')
        setEditModalVisible(false)
        fetchApps()
      } else {
        throw new Error('Failed to update app')
      }
    } catch (error) {
      message.error('Ошибка обновления приложения')
    }
  }

  const handleDeleteApp = async (appId: number) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/appstore/apps/${appId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        message.success('Приложение удалено из магазина')
        fetchApps()
      } else {
        throw new Error('Failed to delete app')
      }
    } catch (error) {
      message.error('Ошибка удаления приложения')
    }
  }

  const handleReviewRequest = async (action: 'approve' | 'deny') => {
    if (!selectedRequest) return

    const values = reviewForm.getFieldsValue()

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/appstore/requests/${selectedRequest.RequestId}/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action,
          admin_comment: values.admin_comment,
        }),
      })

      if (response.ok) {
        message.success(action === 'approve' ? 'Запрос одобрен' : 'Запрос отклонен')
        setReviewModalVisible(false)
        reviewForm.resetFields()
        fetchRequests()
        fetchPendingCount()
      } else {
        throw new Error('Failed to review request')
      }
    } catch (error) {
      message.error('Ошибка обработки запроса')
    }
  }

  const getAppTypeTag = (type: string) => {
    if (type === 'always_allowed') {
      return (
        <Tag color="success" icon={<CheckCircleOutlined />}>
          Всегда разрешено
        </Tag>
      )
    }
    return (
      <Tag color="warning" icon={<ClockCircleOutlined />}>
        По запросу
      </Tag>
    )
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'processing', icon: <ClockCircleOutlined />, text: 'Ожидает' },
      approved: { color: 'success', icon: <CheckCircleOutlined />, text: 'Одобрено' },
      denied: { color: 'error', icon: <CloseCircleOutlined />, text: 'Отклонено' },
      installing: { color: 'processing', icon: <DownloadOutlined />, text: 'Установка' },
      installed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Установлено' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Ошибка' },
    }

    const config = statusConfig[status] || { color: 'default', icon: null, text: status }

    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    )
  }

  const appColumns: ColumnsType<AppStoreApp> = [
    {
      title: 'Приложение',
      key: 'app',
      render: (_, record) => (
        <Space>
          <Avatar
            src={record.IconUrl}
            icon={<AppstoreOutlined />}
            size={40}
            shape="square"
          />
          <Space direction="vertical" size={0}>
            <Space>
              <Text strong>{record.DisplayName || record.Name}</Text>
              {record.IsFeatured && <StarFilled style={{ color: '#faad14' }} />}
            </Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.Publisher} | v{record.Version}
            </Text>
          </Space>
        </Space>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'Category',
      key: 'Category',
      width: 120,
      render: (cat) => cat || '-',
    },
    {
      title: 'Тип',
      dataIndex: 'AppType',
      key: 'AppType',
      width: 150,
      render: (type) => getAppTypeTag(type),
    },
    {
      title: 'Формат',
      dataIndex: 'InstallerType',
      key: 'InstallerType',
      width: 80,
      render: (type) => <Tag>{type?.toUpperCase()}</Tag>,
    },
    {
      title: 'Установок',
      dataIndex: 'TotalInstalls',
      key: 'TotalInstalls',
      width: 100,
      render: (count) => (
        <Space>
          <DownloadOutlined />
          {count || 0}
        </Space>
      ),
    },
    {
      title: 'Ожидает',
      dataIndex: 'PendingRequests',
      key: 'PendingRequests',
      width: 80,
      render: (count) =>
        count > 0 ? (
          <Badge count={count} style={{ backgroundColor: '#1890ff' }} />
        ) : (
          '-'
        ),
    },
    {
      title: 'Статус',
      dataIndex: 'IsActive',
      key: 'IsActive',
      width: 100,
      render: (active) =>
        active ? (
          <Tag color="success">Активно</Tag>
        ) : (
          <Tag color="default">Неактивно</Tag>
        ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="Подробнее">
            <Button
              icon={<FileZipOutlined />}
              size="small"
              onClick={() => {
                setSelectedApp(record)
                setDetailModalVisible(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button
              icon={<EditOutlined />}
              size="small"
              onClick={() => {
                setSelectedApp(record)
                form.setFieldsValue({
                  name: record.Name,
                  display_name: record.DisplayName,
                  description: record.Description,
                  publisher: record.Publisher,
                  version: record.Version,
                  category: record.Category,
                  app_type: record.AppType,
                  installer_type: record.InstallerType,
                  installer_url: record.InstallerUrl,
                  installer_path: record.InstallerPath,
                  silent_install_args: record.SilentInstallArgs,
                  requires_reboot: record.RequiresReboot,
                  icon_url: record.IconUrl,
                  is_featured: record.IsFeatured,
                  is_active: record.IsActive,
                })
                setEditModalVisible(true)
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Удалить приложение из магазина?"
            onConfirm={() => handleDeleteApp(record.AppId)}
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const requestColumns: ColumnsType<AppInstallRequest> = [
    {
      title: 'Приложение',
      dataIndex: 'AppName',
      key: 'AppName',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Пользователь',
      key: 'user',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <UserOutlined />
            {record.UserDisplayName || record.UserName}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.UserDepartment}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Компьютер',
      dataIndex: 'ComputerName',
      key: 'ComputerName',
      render: (text) => (
        <Space>
          <DesktopOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Причина',
      dataIndex: 'RequestReason',
      key: 'RequestReason',
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: 'Дата запроса',
      dataIndex: 'RequestedAt',
      key: 'RequestedAt',
      width: 150,
      render: (date) => new Date(date).toLocaleString('ru-RU'),
    },
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'Status',
      width: 120,
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          {record.Status === 'pending' && (
            <Button
              type="primary"
              size="small"
              onClick={() => {
                setSelectedRequest(record)
                setReviewModalVisible(true)
              }}
            >
              Рассмотреть
            </Button>
          )}
          {record.Status !== 'pending' && (
            <Text type="secondary">
              {record.ReviewedByName}
            </Text>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Приложений в магазине"
              value={apps.filter((a) => a.IsActive).length}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Всегда разрешенных"
              value={apps.filter((a) => a.AppType === 'always_allowed').length}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="По запросу"
              value={apps.filter((a) => a.AppType === 'by_request').length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Ожидают рассмотрения"
              value={pendingCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: pendingCount > 0 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <AppstoreOutlined />
            <span>Магазин приложений</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                fetchApps()
                fetchRequests()
                fetchPendingCount()
              }}
            >
              Обновить
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                form.resetFields()
                setCreateModalVisible(true)
              }}
            >
              Добавить приложение
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="Приложения" key="apps">
            <Table
              columns={appColumns}
              dataSource={apps}
              rowKey="AppId"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
          <TabPane
            tab={
              <Badge count={pendingCount} offset={[10, 0]}>
                Запросы на установку
              </Badge>
            }
            key="requests"
          >
            <Table
              columns={requestColumns}
              dataSource={requests}
              rowKey="RequestId"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Create App Modal */}
      <Modal
        title="Добавить приложение"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateApp}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Название (ID)"
                rules={[{ required: true, message: 'Введите название' }]}
              >
                <Input placeholder="notepad-plus-plus" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="display_name"
                label="Отображаемое название"
              >
                <Input placeholder="Notepad++" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="publisher" label="Издатель">
                <Input placeholder="Microsoft" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="version" label="Версия">
                <Input placeholder="1.0.0" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Описание">
            <TextArea rows={3} placeholder="Описание приложения" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="category" label="Категория">
                <Select options={appCategories} allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="app_type"
                label="Тип разрешения"
                rules={[{ required: true }]}
                initialValue="by_request"
              >
                <Select>
                  <Select.Option value="always_allowed">
                    <Space>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      Всегда разрешено
                    </Space>
                  </Select.Option>
                  <Select.Option value="by_request">
                    <Space>
                      <ClockCircleOutlined style={{ color: '#faad14' }} />
                      По запросу
                    </Space>
                  </Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="installer_type"
                label="Тип установщика"
                initialValue="exe"
              >
                <Select options={installerTypes} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="installer_url" label="URL установщика">
                <Input placeholder="https://..." />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="installer_path" label="UNC путь">
                <Input placeholder="\\server\share\app.exe" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="silent_install_args" label="Аргументы тихой установки">
            <Input placeholder="/S /silent /quiet" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="icon_url" label="URL иконки">
                <Input placeholder="https://..." />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="requires_reboot"
                label="Требует перезагрузку"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="is_featured"
                label="Рекомендованное"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Добавить
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit App Modal */}
      <Modal
        title="Редактировать приложение"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleUpdateApp}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="display_name" label="Отображаемое название">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="version" label="Версия">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Описание">
            <TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="category" label="Категория">
                <Select options={appCategories} allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="app_type" label="Тип разрешения">
                <Select>
                  <Select.Option value="always_allowed">Всегда разрешено</Select.Option>
                  <Select.Option value="by_request">По запросу</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_active" label="Статус" valuePropName="checked">
                <Switch checkedChildren="Активно" unCheckedChildren="Неактивно" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="installer_url" label="URL установщика">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="installer_path" label="UNC путь">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="silent_install_args" label="Аргументы тихой установки">
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="icon_url" label="URL иконки">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_featured" label="Рекомендованное" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Сохранить
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Review Request Modal */}
      <Modal
        title="Рассмотрение запроса"
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={null}
        width={500}
      >
        {selectedRequest && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Приложение">
                <Text strong>{selectedRequest.AppName}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Пользователь">
                {selectedRequest.UserDisplayName || selectedRequest.UserName}
              </Descriptions.Item>
              <Descriptions.Item label="Отдел">
                {selectedRequest.UserDepartment || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Компьютер">
                {selectedRequest.ComputerName}
              </Descriptions.Item>
              <Descriptions.Item label="Причина запроса">
                {selectedRequest.RequestReason || 'Не указана'}
              </Descriptions.Item>
              <Descriptions.Item label="Дата запроса">
                {new Date(selectedRequest.RequestedAt).toLocaleString('ru-RU')}
              </Descriptions.Item>
            </Descriptions>

            <Form form={reviewForm} layout="vertical">
              <Form.Item name="admin_comment" label="Комментарий администратора">
                <TextArea rows={3} placeholder="Причина решения (опционально)" />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setReviewModalVisible(false)}>
                    Отмена
                  </Button>
                  <Button danger onClick={() => handleReviewRequest('deny')}>
                    Отклонить
                  </Button>
                  <Button type="primary" onClick={() => handleReviewRequest('approve')}>
                    Одобрить
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* App Detail Modal */}
      <Modal
        title={selectedApp?.DisplayName || selectedApp?.Name}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Закрыть
          </Button>,
        ]}
        width={600}
      >
        {selectedApp && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={4}>
                <Avatar
                  src={selectedApp.IconUrl}
                  icon={<AppstoreOutlined />}
                  size={64}
                  shape="square"
                />
              </Col>
              <Col span={20}>
                <Title level={5} style={{ margin: 0 }}>
                  {selectedApp.DisplayName || selectedApp.Name}
                  {selectedApp.IsFeatured && (
                    <StarFilled style={{ color: '#faad14', marginLeft: 8 }} />
                  )}
                </Title>
                <Text type="secondary">
                  {selectedApp.Publisher} | v{selectedApp.Version}
                </Text>
                <div style={{ marginTop: 8 }}>
                  {getAppTypeTag(selectedApp.AppType)}
                  <Tag>{selectedApp.Category}</Tag>
                </div>
              </Col>
            </Row>

            <Paragraph>{selectedApp.Description}</Paragraph>

            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="Тип установщика">
                {selectedApp.InstallerType?.toUpperCase()}
              </Descriptions.Item>
              <Descriptions.Item label="Требует перезагрузку">
                {selectedApp.RequiresReboot ? 'Да' : 'Нет'}
              </Descriptions.Item>
              <Descriptions.Item label="Всего установок" span={2}>
                {selectedApp.TotalInstalls || 0}
              </Descriptions.Item>
              <Descriptions.Item label="URL установщика" span={2}>
                <Text copyable ellipsis style={{ maxWidth: 300 }}>
                  {selectedApp.InstallerUrl || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="UNC путь" span={2}>
                <Text copyable ellipsis style={{ maxWidth: 300 }}>
                  {selectedApp.InstallerPath || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Аргументы установки" span={2}>
                <Text code>{selectedApp.SilentInstallArgs || '-'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Добавлено">
                {selectedApp.AddedByName}
              </Descriptions.Item>
              <Descriptions.Item label="Дата">
                {new Date(selectedApp.AddedAt).toLocaleDateString('ru-RU')}
              </Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Modal>
    </div>
  )
}
