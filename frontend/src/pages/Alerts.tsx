import { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Space,
  Button,
  Tag,
  Typography,
  Row,
  Col,
  Select,
  Modal,
  Form,
  Input,
  message,
} from 'antd'
import {
  ReloadOutlined,
  CheckOutlined,
  CloseOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { apiService } from '@/services/api'
import {
  formatDateTime,
  formatRelativeTime,
  getSeverityColor,
  getSeverityText,
  getStatusColor,
  getStatusText,
  getPriorityText,
} from '@/utils/formatters'
import type { Alert, AlertFilter } from '@/types'
import SavedSearchManager from '@/components/SavedSearchManager'

const { Title, Text } = Typography
const { TextArea } = Input

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState<AlertFilter>({
    limit: 50,
    offset: 0,
  })
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [resolveModalVisible, setResolveModalVisible] = useState(false)
  const [resolveForm] = Form.useForm()

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const response = await apiService.getAlerts(filter)
      setAlerts(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load alerts:', error)
      message.error('Не удалось загрузить алерты')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [filter])

  const handleAcknowledge = async (alertId: number) => {
    try {
      await apiService.acknowledgeAlert(alertId)
      message.success('Алерт подтверждён')
      loadAlerts()
    } catch (error) {
      message.error('Ошибка при подтверждении алерта')
    }
  }

  const handleResolve = async (values: { resolution: 'resolved' | 'false_positive'; comment?: string }) => {
    if (!selectedAlert) return

    try {
      // FIX BUG-006: Use snake_case field name (alert_id instead of AlertId)
      await apiService.resolveAlert(selectedAlert.alert_id, values.resolution, values.comment)
      message.success('Алерт решён')
      setResolveModalVisible(false)
      resolveForm.resetFields()
      loadAlerts()
    } catch (error) {
      message.error('Ошибка при решении алерта')
    }
  }

  const showResolveModal = (alert: Alert) => {
    setSelectedAlert(alert)
    setResolveModalVisible(true)
  }

  const handleTableChange = (pagination: any, filters: any) => {
    // FIX BUG-006: Use snake_case field names for filter keys
    setFilter({
      ...filter,
      limit: pagination.pageSize,
      offset: (pagination.current - 1) * pagination.pageSize,
      severity: filters.severity,
      status: filters.status,
    })
  }

  const handleLoadSearch = (savedFilters: Record<string, any>) => {
    setFilter({ ...filter, ...savedFilters, offset: 0 })
  }

  // FIX BUG-006: Use snake_case field names matching Alert type
  const columns: ColumnsType<Alert> = [
    {
      title: 'ID',
      dataIndex: 'alert_id',
      key: 'alert_id',
      width: 80,
    },
    {
      title: 'Время',
      dataIndex: 'first_event_time',
      key: 'first_event_time',
      width: 160,
      render: (time) => formatDateTime(time),
      sorter: true,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 110,
      render: (severity) => (
        <Tag color={getSeverityColor(severity)}>{getSeverityText(severity)}</Tag>
      ),
      filters: [
        { text: 'Критический', value: 4 },
        { text: 'Высокий', value: 3 },
        { text: 'Средний', value: 2 },
        { text: 'Низкий', value: 1 },
      ],
      filteredValue: filter.severity || null,
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority) => <Tag>{getPriorityText(priority)}</Tag>,
    },
    {
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (title, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{title}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.hostname} • {record.event_count} событий
          </Text>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status) => <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>,
      filters: [
        { text: 'Новый', value: 'new' },
        { text: 'Подтверждён', value: 'acknowledged' },
        { text: 'В работе', value: 'in_progress' },
        { text: 'Решён', value: 'resolved' },
        { text: 'Ложный', value: 'false_positive' },
      ],
      filteredValue: filter.status || null,
    },
    {
      title: 'Назначен',
      dataIndex: 'assigned_to_user',
      key: 'assigned_to_user',
      width: 120,
      render: (user) => user || '-',
    },
    {
      title: 'Обновлён',
      dataIndex: 'last_event_time',
      key: 'last_event_time',
      width: 120,
      render: (time) => formatRelativeTime(time),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'new' && (
            <Button
              type="primary"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleAcknowledge(record.alert_id)}
            >
              Подтвердить
            </Button>
          )}
          {['new', 'acknowledged', 'in_progress'].includes(record.status) && (
            <Button
              size="small"
              icon={<CloseOutlined />}
              onClick={() => showResolveModal(record)}
            >
              Решить
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <Title level={4} style={{ margin: 0 }}>
                Алерты
              </Title>
              <Text type="secondary">Всего: {total}</Text>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                style={{ width: 150 }}
                placeholder="Фильтр по severity"
                allowClear
                value={filter.severity}
                onChange={(value) => setFilter({ ...filter, severity: value, offset: 0 })}
                options={[
                  { label: 'Критический', value: [4] },
                  { label: 'Высокий', value: [3] },
                  { label: 'Средний', value: [2] },
                  { label: 'Низкий', value: [1] },
                ]}
              />
              <Select
                style={{ width: 150 }}
                placeholder="Фильтр по статусу"
                allowClear
                value={filter.status}
                onChange={(value) => setFilter({ ...filter, status: value, offset: 0 })}
                options={[
                  { label: 'Новый', value: ['new'] },
                  { label: 'В работе', value: ['acknowledged', 'in_progress'] },
                  { label: 'Решён', value: ['resolved', 'false_positive'] },
                ]}
              />
              <Button icon={<ReloadOutlined />} onClick={loadAlerts}>
                Обновить
              </Button>
            </Space>
          </Col>
        </Row>

        <SavedSearchManager
          searchType="alerts"
          currentFilters={filter}
          onLoadSearch={handleLoadSearch}
        />
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={alerts}
          rowKey="alert_id"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            total,
            current: (filter.offset || 0) / (filter.limit || 50) + 1,
            pageSize: filter.limit || 50,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} алертов`,
            pageSizeOptions: ['25', '50', '100'],
          }}
          scroll={{ x: 1300 }}
          size="small"
        />
      </Card>

      {/* Resolve Alert Modal */}
      <Modal
        title="Решение алерта"
        open={resolveModalVisible}
        onCancel={() => {
          setResolveModalVisible(false)
          resolveForm.resetFields()
        }}
        footer={null}
      >
        <Form form={resolveForm} layout="vertical" onFinish={handleResolve}>
          <Form.Item
            label="Решение"
            name="resolution"
            rules={[{ required: true, message: 'Выберите решение' }]}
          >
            <Select
              options={[
                { label: 'Решён', value: 'resolved' },
                { label: 'Ложное срабатывание', value: 'false_positive' },
              ]}
            />
          </Form.Item>
          <Form.Item label="Комментарий" name="comment">
            <TextArea rows={4} placeholder="Опишите решение..." />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Подтвердить
              </Button>
              <Button
                onClick={() => {
                  setResolveModalVisible(false)
                  resolveForm.resetFields()
                }}
              >
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
