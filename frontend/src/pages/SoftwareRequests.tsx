/**
 * Software Installation Requests Page
 * Admin interface to approve/deny software installation requests from users
 */

import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Space,
  Input,
  Select,
  Button,
  Badge,
  Typography,
  Modal,
  Descriptions,
  Form,
  message,
  Alert,
  Divider,
  Row,
  Col,
  Statistic,
  InputNumber,
  Timeline,
} from 'antd'
import {
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  DownloadOutlined,
  UserOutlined,
  DesktopOutlined,
  FileProtectOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text, Paragraph } = Typography
const { Option } = Select
const { TextArea } = Input

interface SoftwareRequest {
  RequestId: number
  AgentId: string
  ComputerName: string
  UserName: string
  UserDisplayName: string
  UserDepartment: string
  UserEmail: string
  SoftwareName: string
  SoftwareVersion: string
  SoftwarePublisher: string
  InstallerPath: string
  InstallerHash: string
  VirusTotalDetections: number
  ThreatIntelScore: number
  UserComment: string
  BusinessJustification: string
  RequestedAt: string
  Status: string
  ReviewedAt: string
  AdminComment: string
  ApprovedUntil: string
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'orange',
  approved: 'green',
  denied: 'red',
  expired: 'default',
  cancelled: 'default',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  approved: 'Одобрено',
  denied: 'Отклонено',
  expired: 'Истекло',
  cancelled: 'Отменено',
}

export default function SoftwareRequests() {
  const [requests, setRequests] = useState<SoftwareRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pendingCount, setPendingCount] = useState(0)
  const pageSize = 20

  // Filters
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>('pending')

  // Review modal
  const [reviewModalVisible, setReviewModalVisible] = useState(false)
  const [selectedRequest, setSelectedRequest] = useState<SoftwareRequest | null>(null)
  const [reviewAction, setReviewAction] = useState<'approve' | 'deny'>('approve')
  const [reviewForm] = Form.useForm()

  // Detail modal
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  // Load requests
  const loadRequests = async () => {
    setLoading(true)
    try {
      const params = {
        page,
        page_size: pageSize,
        search: searchText || undefined,
        status_filter: statusFilter || undefined,
      }
      const response = await apiService.client.get('/ad/software-requests', { params })
      setRequests(response.data.items)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Failed to load requests:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load pending count
  const loadPendingCount = async () => {
    try {
      const response = await apiService.client.get('/ad/software-requests/pending/count')
      setPendingCount(response.data.pending_count)
    } catch (error) {
      console.error('Failed to load pending count:', error)
    }
  }

  useEffect(() => {
    loadRequests()
    loadPendingCount()
  }, [page, searchText, statusFilter])

  // Handle review
  const handleReview = async (values: any) => {
    if (!selectedRequest) return

    try {
      await apiService.client.post(`/ad/software-requests/${selectedRequest.RequestId}/review`, {
        action: reviewAction,
        admin_comment: values.admin_comment,
        approval_hours: values.approval_hours || 24,
      })

      message.success(reviewAction === 'approve' ? 'Запрос одобрен' : 'Запрос отклонён')
      setReviewModalVisible(false)
      reviewForm.resetFields()
      loadRequests()
      loadPendingCount()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка обработки запроса')
    }
  }

  // Open review modal
  const openReviewModal = (request: SoftwareRequest, action: 'approve' | 'deny') => {
    setSelectedRequest(request)
    setReviewAction(action)
    reviewForm.resetFields()
    setReviewModalVisible(true)
  }

  // Open detail modal
  const openDetailModal = (request: SoftwareRequest) => {
    setSelectedRequest(request)
    setDetailModalVisible(true)
  }

  // Table columns
  const columns: ColumnsType<SoftwareRequest> = [
    {
      title: 'Запрос',
      key: 'request',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.SoftwareName}</Text>
          {record.SoftwareVersion && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              Версия: {record.SoftwareVersion}
            </Text>
          )}
          {record.SoftwarePublisher && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.SoftwarePublisher}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Пользователь',
      key: 'user',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <UserOutlined />
            <Text>{record.UserDisplayName || record.UserName}</Text>
          </Space>
          {record.UserDepartment && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.UserDepartment}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Компьютер',
      key: 'computer',
      render: (_, record) => (
        <Space>
          <DesktopOutlined />
          <Text>{record.ComputerName}</Text>
        </Space>
      ),
    },
    {
      title: 'Безопасность',
      key: 'security',
      width: 130,
      render: (_, record) => {
        const hasDetections = record.VirusTotalDetections > 0
        const highRisk = record.ThreatIntelScore >= 50
        return (
          <Space direction="vertical" size={0}>
            <Tag color={hasDetections ? 'red' : 'green'} icon={hasDetections ? <WarningOutlined /> : <SafetyCertificateOutlined />}>
              VT: {record.VirusTotalDetections} обнаружений
            </Tag>
            <Tag color={highRisk ? 'orange' : 'default'}>
              Риск: {record.ThreatIntelScore}/100
            </Tag>
          </Space>
        )
      },
    },
    {
      title: 'Комментарий',
      dataIndex: 'UserComment',
      key: 'UserComment',
      ellipsis: true,
      width: 200,
      render: (comment: string) => (
        <Text ellipsis={{ tooltip: comment }}>
          {comment || <Text type="secondary">Нет комментария</Text>}
        </Text>
      ),
    },
    {
      title: 'Дата запроса',
      dataIndex: 'RequestedAt',
      key: 'RequestedAt',
      width: 150,
      render: (date: string) => dayjs(date).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'Status',
      width: 110,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status]} icon={
          status === 'pending' ? <ClockCircleOutlined /> :
          status === 'approved' ? <CheckCircleOutlined /> :
          status === 'denied' ? <CloseCircleOutlined /> :
          <ExclamationCircleOutlined />
        }>
          {STATUS_LABELS[status] || status}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openDetailModal(record)}>
            Детали
          </Button>
          {record.Status === 'pending' && (
            <>
              <Button
                type="primary"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => openReviewModal(record, 'approve')}
              >
                Одобрить
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseCircleOutlined />}
                onClick={() => openReviewModal(record, 'deny')}
              >
                Отклонить
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Title level={3} style={{ margin: 0 }}>Запросы на установку ПО</Title>
            {pendingCount > 0 && (
              <Badge count={pendingCount} style={{ marginLeft: 8 }}>
                <Tag color="orange" icon={<ClockCircleOutlined />}>Ожидают решения</Tag>
              </Badge>
            )}
          </Space>
          <Button icon={<ReloadOutlined />} onClick={loadRequests}>
            Обновить
          </Button>
        </div>

        {/* Info Alert */}
        <Alert
          message="Контроль установки ПО"
          description="Здесь отображаются запросы от пользователей на установку программного обеспечения.
          Вы можете одобрить или отклонить каждый запрос. После одобрения пользователь сможет установить ПО самостоятельно."
          type="info"
          showIcon
          icon={<FileProtectOutlined />}
        />

        {/* Filters */}
        <Card>
          <Space wrap>
            <Input
              placeholder="Поиск по ПО, пользователю, компьютеру..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 300 }}
              allowClear
            />
            <Select
              placeholder="Статус"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 150 }}
              allowClear
            >
              <Option value="pending">Ожидающие</Option>
              <Option value="approved">Одобренные</Option>
              <Option value="denied">Отклонённые</Option>
              <Option value="expired">Истекшие</Option>
            </Select>
          </Space>
        </Card>

        {/* Table */}
        <Card>
          <Table
            columns={columns}
            dataSource={requests}
            rowKey="RequestId"
            loading={loading}
            pagination={{
              current: page,
              total,
              pageSize,
              onChange: setPage,
              showTotal: (total) => `Всего ${total} запросов`,
            }}
            scroll={{ x: 1400 }}
            rowClassName={(record) => record.Status === 'pending' ? 'pending-row' : ''}
          />
        </Card>
      </Space>

      {/* Review Modal */}
      <Modal
        title={
          <Space>
            {reviewAction === 'approve' ? (
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            )}
            {reviewAction === 'approve' ? 'Одобрить запрос' : 'Отклонить запрос'}
          </Space>
        }
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedRequest && (
          <>
            <Alert
              message={`ПО: ${selectedRequest.SoftwareName}`}
              description={
                <Space direction="vertical">
                  <Text>Пользователь: {selectedRequest.UserDisplayName || selectedRequest.UserName}</Text>
                  <Text>Компьютер: {selectedRequest.ComputerName}</Text>
                  {selectedRequest.UserComment && (
                    <Text>Комментарий: {selectedRequest.UserComment}</Text>
                  )}
                </Space>
              }
              type={reviewAction === 'approve' ? 'success' : 'error'}
              style={{ marginBottom: 16 }}
            />

            <Form
              form={reviewForm}
              layout="vertical"
              onFinish={handleReview}
            >
              {reviewAction === 'approve' && (
                <Form.Item
                  name="approval_hours"
                  label="Срок действия разрешения (часы)"
                  initialValue={24}
                  extra="После истечения срока пользователь не сможет установить ПО"
                >
                  <InputNumber min={1} max={168} style={{ width: '100%' }} />
                </Form.Item>
              )}

              <Form.Item
                name="admin_comment"
                label="Комментарий администратора"
                extra="Этот комментарий увидит пользователь"
              >
                <TextArea
                  rows={3}
                  placeholder={
                    reviewAction === 'approve'
                      ? 'Одобрено. Установите в течение указанного срока.'
                      : 'Укажите причину отказа...'
                  }
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button onClick={() => setReviewModalVisible(false)}>
                    Отмена
                  </Button>
                  <Button
                    type="primary"
                    htmlType="submit"
                    danger={reviewAction === 'deny'}
                  >
                    {reviewAction === 'approve' ? 'Одобрить' : 'Отклонить'}
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="Детали запроса"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Закрыть
          </Button>,
          selectedRequest?.Status === 'pending' && (
            <Button
              key="approve"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                setDetailModalVisible(false)
                openReviewModal(selectedRequest!, 'approve')
              }}
            >
              Одобрить
            </Button>
          ),
          selectedRequest?.Status === 'pending' && (
            <Button
              key="deny"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => {
                setDetailModalVisible(false)
                openReviewModal(selectedRequest!, 'deny')
              }}
            >
              Отклонить
            </Button>
          ),
        ].filter(Boolean)}
        width={800}
      >
        {selectedRequest && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Статус"
                  value={STATUS_LABELS[selectedRequest.Status]}
                  prefix={
                    <Tag color={STATUS_COLORS[selectedRequest.Status]}>
                      {selectedRequest.Status === 'pending' ? <ClockCircleOutlined /> :
                       selectedRequest.Status === 'approved' ? <CheckCircleOutlined /> :
                       <CloseCircleOutlined />}
                    </Tag>
                  }
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Оценка безопасности"
                  value={selectedRequest.ThreatIntelScore}
                  suffix="/ 100"
                  valueStyle={{
                    color: selectedRequest.ThreatIntelScore >= 50 ? '#cf1322' :
                           selectedRequest.ThreatIntelScore >= 20 ? '#faad14' : '#3f8600'
                  }}
                />
              </Col>
            </Row>

            <Divider>Информация о ПО</Divider>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Название" span={2}>
                <Text strong>{selectedRequest.SoftwareName}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Версия">
                {selectedRequest.SoftwareVersion || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Издатель">
                {selectedRequest.SoftwarePublisher || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Путь к установщику" span={2}>
                <Text code style={{ fontSize: 12 }}>{selectedRequest.InstallerPath || '-'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="SHA256 хэш" span={2}>
                <Text code style={{ fontSize: 11 }}>{selectedRequest.InstallerHash || '-'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="VirusTotal">
                <Tag color={selectedRequest.VirusTotalDetections > 0 ? 'red' : 'green'}>
                  {selectedRequest.VirusTotalDetections} обнаружений
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Threat Intel Score">
                <Tag color={selectedRequest.ThreatIntelScore >= 50 ? 'red' : selectedRequest.ThreatIntelScore >= 20 ? 'orange' : 'green'}>
                  {selectedRequest.ThreatIntelScore}/100
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider>Информация о запросе</Divider>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Пользователь">
                {selectedRequest.UserDisplayName || selectedRequest.UserName}
              </Descriptions.Item>
              <Descriptions.Item label="Email">
                {selectedRequest.UserEmail || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Отдел">
                {selectedRequest.UserDepartment || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Компьютер">
                {selectedRequest.ComputerName}
              </Descriptions.Item>
              <Descriptions.Item label="Дата запроса" span={2}>
                {dayjs(selectedRequest.RequestedAt).format('DD.MM.YYYY HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {(selectedRequest.UserComment || selectedRequest.BusinessJustification) && (
              <>
                <Divider>Обоснование от пользователя</Divider>
                {selectedRequest.UserComment && (
                  <Alert
                    message="Комментарий пользователя"
                    description={selectedRequest.UserComment}
                    type="info"
                    style={{ marginBottom: 16 }}
                  />
                )}
                {selectedRequest.BusinessJustification && (
                  <Alert
                    message="Бизнес-обоснование"
                    description={selectedRequest.BusinessJustification}
                    type="info"
                  />
                )}
              </>
            )}

            {selectedRequest.Status !== 'pending' && (
              <>
                <Divider>Решение администратора</Divider>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Решение">
                    <Tag color={STATUS_COLORS[selectedRequest.Status]}>
                      {STATUS_LABELS[selectedRequest.Status]}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Дата решения">
                    {selectedRequest.ReviewedAt
                      ? dayjs(selectedRequest.ReviewedAt).format('DD.MM.YYYY HH:mm:ss')
                      : '-'}
                  </Descriptions.Item>
                  {selectedRequest.ApprovedUntil && (
                    <Descriptions.Item label="Действует до" span={2}>
                      {dayjs(selectedRequest.ApprovedUntil).format('DD.MM.YYYY HH:mm:ss')}
                    </Descriptions.Item>
                  )}
                  {selectedRequest.AdminComment && (
                    <Descriptions.Item label="Комментарий администратора" span={2}>
                      {selectedRequest.AdminComment}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
