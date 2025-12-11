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
  Drawer,
  Descriptions,
  Timeline,
  Tabs,
  Form,
  Input,
  Select,
  Modal,
  Steps,
  Alert,
  Badge,
  Divider,
  message,
  Tooltip,
} from 'antd'
import {
  ReloadOutlined,
  PlusOutlined,
  EyeOutlined,
  EditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  SafetyOutlined,
  TeamOutlined,
  WarningOutlined,
  LockOutlined,
  UnlockOutlined,
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
  formatCurrency,
  getMitreTacticName,
} from '@/utils/formatters'
import type { Incident, IncidentFilter } from '@/types'
import SavedSearchManager from '@/components/SavedSearchManager'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { TabPane } = Tabs

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState<IncidentFilter>({
    limit: 50,
    offset: 0,
  })
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [workLogModalVisible, setWorkLogModalVisible] = useState(false)
  const [actionModalVisible, setActionModalVisible] = useState(false)
  const [actionType, setActionType] = useState<'contain' | 'remediate' | 'close'>('contain')
  const [createForm] = Form.useForm()
  const [workLogForm] = Form.useForm()
  const [actionForm] = Form.useForm()

  const loadIncidents = async () => {
    setLoading(true)
    try {
      const response = await apiService.getIncidents(filter)
      setIncidents(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load incidents:', error)
      message.error('Не удалось загрузить инциденты')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadIncidents()
  }, [filter])

  const handleTableChange = (pagination: any, filters: any) => {
    setFilter({
      ...filter,
      limit: pagination.pageSize,
      offset: (pagination.current - 1) * pagination.pageSize,
      severity: filters.Severity,
      status: filters.Status,
    })
  }

  const handleLoadSearch = (savedFilters: Record<string, any>) => {
    setFilter({ ...filter, ...savedFilters, offset: 0 })
  }

  const showIncidentDetails = async (incident: Incident) => {
    try {
      const fullIncident = await apiService.getIncident(incident.IncidentId)
      setSelectedIncident(fullIncident)
      setDrawerVisible(true)
    } catch (error) {
      message.error('Не удалось загрузить детали инцидента')
    }
  }

  const handleCreateIncident = async (values: any) => {
    try {
      await apiService.createIncident(values)
      message.success('Инцидент создан')
      setCreateModalVisible(false)
      createForm.resetFields()
      loadIncidents()
    } catch (error) {
      message.error('Ошибка при создании инцидента')
    }
  }

  const handleAddWorkLog = async (values: { entry: string }) => {
    if (!selectedIncident) return
    try {
      const updated = await apiService.addIncidentWorkLog(selectedIncident.IncidentId, values.entry)
      setSelectedIncident(updated)
      message.success('Запись добавлена')
      setWorkLogModalVisible(false)
      workLogForm.resetFields()
    } catch (error) {
      message.error('Ошибка при добавлении записи')
    }
  }

  const handleAction = async (values: any) => {
    if (!selectedIncident) return
    try {
      let updated: Incident
      if (actionType === 'contain') {
        updated = await apiService.containIncident(selectedIncident.IncidentId, values.actions)
      } else if (actionType === 'remediate') {
        updated = await apiService.remediateIncident(selectedIncident.IncidentId, values.actions)
      } else {
        updated = await apiService.closeIncident(selectedIncident.IncidentId, values.lessons_learned)
      }
      setSelectedIncident(updated)
      message.success('Действие выполнено')
      setActionModalVisible(false)
      actionForm.resetFields()
      loadIncidents()
    } catch (error) {
      message.error('Ошибка при выполнении действия')
    }
  }

  const getStatusStep = (status: string): number => {
    const steps = ['open', 'investigating', 'contained', 'remediated', 'closed']
    return steps.indexOf(status)
  }

  const columns: ColumnsType<Incident> = [
    {
      title: 'ID',
      dataIndex: 'IncidentId',
      key: 'IncidentId',
      width: 80,
      render: (id) => `#${id}`,
    },
    {
      title: 'Обнаружен',
      dataIndex: 'DetectedAt',
      key: 'DetectedAt',
      width: 160,
      render: (time) => formatDateTime(time),
      sorter: true,
    },
    {
      title: 'Severity',
      dataIndex: 'Severity',
      key: 'Severity',
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
      title: 'Название',
      dataIndex: 'Title',
      key: 'Title',
      width: 350,
      ellipsis: true,
      render: (title, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{title}</Text>
          <Space size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.AlertCount} алертов • {record.EventCount} событий
            </Text>
            {record.AffectedAssets && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                • {record.AffectedAssets} хостов
              </Text>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'Status',
      width: 130,
      render: (status) => <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>,
      filters: [
        { text: 'Открыт', value: 'open' },
        { text: 'Расследуется', value: 'investigating' },
        { text: 'Локализован', value: 'contained' },
        { text: 'Устранён', value: 'remediated' },
        { text: 'Закрыт', value: 'closed' },
      ],
      filteredValue: filter.status || null,
    },
    {
      title: 'Назначен',
      dataIndex: 'AssignedToUser',
      key: 'AssignedToUser',
      width: 120,
      render: (user) => user || '-',
    },
    {
      // FIX BUG-007: Use IncidentCategory instead of Category
      title: 'Категория',
      dataIndex: 'IncidentCategory',
      key: 'IncidentCategory',
      width: 120,
      ellipsis: true,
      render: (category) => category || '-',
    },
    {
      title: 'Ущерб',
      dataIndex: 'EstimatedDamage_RUB',
      key: 'EstimatedDamage_RUB',
      width: 120,
      render: (damage) => (damage ? formatCurrency(damage) : '-'),
    },
    {
      title: 'ЦБ РФ',
      dataIndex: 'IsReportedToCBR',
      key: 'IsReportedToCBR',
      width: 80,
      render: (reported, record) => {
        if (!record.IsReportable) return <Text type="secondary">-</Text>
        return reported ? (
          <Tooltip title={`Отчёт отправлен ${formatDateTime(record.CBRReportDate!)}`}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
          </Tooltip>
        ) : (
          <Tooltip title="Требуется отчёт">
            <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 18 }} />
          </Tooltip>
        )
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showIncidentDetails(record)}
        >
          Детали
        </Button>
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
                Инциденты безопасности
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
                  { label: 'Открыт', value: ['open'] },
                  { label: 'В работе', value: ['investigating', 'contained', 'remediated'] },
                  { label: 'Закрыт', value: ['closed'] },
                ]}
              />
              <Button icon={<ReloadOutlined />} onClick={loadIncidents}>
                Обновить
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                Создать инцидент
              </Button>
            </Space>
          </Col>
        </Row>

        <SavedSearchManager
          searchType="incidents"
          currentFilters={filter}
          onLoadSearch={handleLoadSearch}
        />
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={incidents}
          rowKey="IncidentId"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            total,
            current: (filter.offset || 0) / (filter.limit || 50) + 1,
            pageSize: filter.limit || 50,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} инцидентов`,
            pageSizeOptions: ['25', '50', '100'],
          }}
          scroll={{ x: 1600 }}
          size="small"
        />
      </Card>

      {/* Incident Details Drawer */}
      <Drawer
        title={
          <Space>
            <WarningOutlined style={{ color: '#ff4d4f' }} />
            <span>Инцидент #{selectedIncident?.IncidentId}</span>
          </Space>
        }
        placement="right"
        width="80%"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        extra={
          <Space>
            <Button icon={<FileTextOutlined />} onClick={() => setWorkLogModalVisible(true)}>
              Work Log
            </Button>
            {selectedIncident?.Status === 'open' && (
              <Button
                type="primary"
                icon={<LockOutlined />}
                onClick={() => {
                  setActionType('contain')
                  setActionModalVisible(true)
                }}
              >
                Локализовать
              </Button>
            )}
            {selectedIncident?.Status === 'contained' && (
              <Button
                type="primary"
                icon={<SafetyOutlined />}
                onClick={() => {
                  setActionType('remediate')
                  setActionModalVisible(true)
                }}
              >
                Устранить
              </Button>
            )}
            {['contained', 'remediated'].includes(selectedIncident?.Status || '') && (
              <Button
                icon={<CheckCircleOutlined />}
                onClick={() => {
                  setActionType('close')
                  setActionModalVisible(true)
                }}
              >
                Закрыть
              </Button>
            )}
          </Space>
        }
      >
        {selectedIncident && (
          <Tabs defaultActiveKey="overview">
            <TabPane tab="Обзор" key="overview">
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                {/* Status Progress */}
                <Card title="Статус инцидента" size="small">
                  <Steps
                    current={getStatusStep(selectedIncident.Status)}
                    items={[
                      { title: 'Открыт', icon: <ExclamationCircleOutlined /> },
                      { title: 'Расследуется', icon: <ClockCircleOutlined /> },
                      { title: 'Локализован', icon: <LockOutlined /> },
                      { title: 'Устранён', icon: <SafetyOutlined /> },
                      { title: 'Закрыт', icon: <CheckCircleOutlined /> },
                    ]}
                  />
                </Card>

                {/* Main Info */}
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="Название" span={2}>
                    <Text strong>{selectedIncident.Title}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Описание" span={2}>
                    {selectedIncident.Description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Severity">
                    <Tag color={getSeverityColor(selectedIncident.Severity)}>
                      {getSeverityText(selectedIncident.Severity)}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Priority">
                    <Tag>{getPriorityText(selectedIncident.Priority)}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Категория">
                    {/* FIX BUG-007: Use IncidentCategory */}
                    {selectedIncident.IncidentCategory || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Назначен">
                    {selectedIncident.AssignedToUser || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Обнаружен">
                    {formatDateTime(selectedIncident.DetectedAt)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Начало атаки">
                    {/* FIX BUG-007: Use StartedAt instead of StartTime */}
                    {selectedIncident.StartedAt ? formatDateTime(selectedIncident.StartedAt) : '-'}
                  </Descriptions.Item>
                </Descriptions>

                {/* Statistics */}
                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Stat title="Алерты" value={selectedIncident.AlertCount || 0} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="События" value={selectedIncident.EventCount || 0} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Затронуто хостов" value={selectedIncident.AffectedAssets || 0} />
                    </Card>
                  </Col>
                </Row>

                {/* MITRE ATT&CK */}
                {/* FIX BUG-007: Use MitreAttackChain instead of MitreAttackTactics/MitreAttackTechniques */}
                {selectedIncident.MitreAttackChain && (
                  <Card title="MITRE ATT&CK" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text strong>Kill Chain:</Text>
                        <div style={{ marginTop: 8 }}>
                          <Text>{selectedIncident.MitreAttackChain}</Text>
                        </div>
                      </div>
                    </Space>
                  </Card>
                )}

                {/* AI Analysis */}
                {/* FIX BUG-007: Use existing AI fields instead of non-existent AISummary */}
                {(selectedIncident.AIRootCause || selectedIncident.AIImpactAssessment || selectedIncident.AIRecommendations) && (
                  <Card title="AI Анализ" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {selectedIncident.AIRootCause && (
                        <div>
                          <Text strong>Причина:</Text>
                          <Paragraph>{selectedIncident.AIRootCause}</Paragraph>
                        </div>
                      )}
                      {selectedIncident.AIImpactAssessment && (
                        <div>
                          <Text strong>Оценка воздействия:</Text>
                          <Paragraph>{selectedIncident.AIImpactAssessment}</Paragraph>
                        </div>
                      )}
                      {selectedIncident.AIRecommendations && (
                        <div>
                          <Text strong>Рекомендации:</Text>
                          <Paragraph>{selectedIncident.AIRecommendations}</Paragraph>
                        </div>
                      )}
                    </Space>
                  </Card>
                )}
              </Space>
            </TabPane>

            <TabPane tab="Timeline" key="timeline">
              <Timeline
                items={[
                  {
                    color: 'red',
                    children: (
                      <>
                        <Text strong>Инцидент обнаружен</Text>
                        <br />
                        <Text type="secondary">{formatDateTime(selectedIncident.DetectedAt)}</Text>
                      </>
                    ),
                  },
                  ...(selectedIncident.WorkLog
                    ? JSON.parse(selectedIncident.WorkLog).map((entry: any) => ({
                        color: entry.type === 'milestone' ? 'blue' : 'gray',
                        children: (
                          <>
                            <Text>{entry.entry}</Text>
                            <br />
                            <Text type="secondary">
                              {entry.user} • {formatDateTime(entry.timestamp)}
                            </Text>
                          </>
                        ),
                      }))
                    : []),
                ]}
              />
            </TabPane>

            <TabPane tab="Действия" key="actions">
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                {selectedIncident.ContainmentActions && (
                  <Card title="Локализация" size="small">
                    <Paragraph>{selectedIncident.ContainmentActions}</Paragraph>
                  </Card>
                )}
                {selectedIncident.RemediationActions && (
                  <Card title="Устранение" size="small">
                    <Paragraph>{selectedIncident.RemediationActions}</Paragraph>
                  </Card>
                )}
                {selectedIncident.LessonsLearned && (
                  <Card title="Выводы" size="small">
                    <Paragraph>{selectedIncident.LessonsLearned}</Paragraph>
                  </Card>
                )}
              </Space>
            </TabPane>

            <TabPane tab="ЦБ РФ" key="cbr">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Требует отчёт">
                  {selectedIncident.IsReportable ? 'Да' : 'Нет'}
                </Descriptions.Item>
                <Descriptions.Item label="Отчёт отправлен">
                  {selectedIncident.IsReportedToCBR ? 'Да' : 'Нет'}
                </Descriptions.Item>
                {selectedIncident.CBRReportDate && (
                  <Descriptions.Item label="Дата отчёта">
                    {formatDateTime(selectedIncident.CBRReportDate)}
                  </Descriptions.Item>
                )}
                {selectedIncident.CBRIncidentNumber && (
                  <Descriptions.Item label="Номер инцидента">
                    {selectedIncident.CBRIncidentNumber}
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="Категория риска">
                  {selectedIncident.OperationalRiskCategory || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Оценка ущерба">
                  {selectedIncident.EstimatedDamage_RUB
                    ? formatCurrency(selectedIncident.EstimatedDamage_RUB)
                    : '-'}
                </Descriptions.Item>
                {selectedIncident.ActualDamage_RUB && (
                  <Descriptions.Item label="Фактический ущерб">
                    {formatCurrency(selectedIncident.ActualDamage_RUB)}
                  </Descriptions.Item>
                )}
              </Descriptions>
            </TabPane>
          </Tabs>
        )}
      </Drawer>

      {/* Create Incident Modal */}
      <Modal
        title="Создать инцидент"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateIncident}>
          <Form.Item
            label="Название"
            name="title"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="Описание" name="description">
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item
            label="Severity"
            name="severity"
            rules={[{ required: true, message: 'Выберите severity' }]}
          >
            <Select
              options={[
                { label: 'Критический', value: 4 },
                { label: 'Высокий', value: 3 },
                { label: 'Средний', value: 2 },
                { label: 'Низкий', value: 1 },
              ]}
            />
          </Form.Item>
          <Form.Item
            label="Priority"
            name="priority"
            rules={[{ required: true, message: 'Выберите priority' }]}
          >
            <Select
              options={[
                { label: 'Критический', value: 4 },
                { label: 'Высокий', value: 3 },
                { label: 'Средний', value: 2 },
                { label: 'Низкий', value: 1 },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Создать
              </Button>
              <Button
                onClick={() => {
                  setCreateModalVisible(false)
                  createForm.resetFields()
                }}
              >
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Work Log Modal */}
      <Modal
        title="Добавить запись в Work Log"
        open={workLogModalVisible}
        onCancel={() => {
          setWorkLogModalVisible(false)
          workLogForm.resetFields()
        }}
        footer={null}
      >
        <Form form={workLogForm} layout="vertical" onFinish={handleAddWorkLog}>
          <Form.Item
            label="Запись"
            name="entry"
            rules={[{ required: true, message: 'Введите запись' }]}
          >
            <TextArea rows={4} placeholder="Опишите выполненные действия..." />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Добавить
              </Button>
              <Button onClick={() => setWorkLogModalVisible(false)}>Отмена</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Action Modal (Contain/Remediate/Close) */}
      <Modal
        title={
          actionType === 'contain'
            ? 'Локализация инцидента'
            : actionType === 'remediate'
            ? 'Устранение инцидента'
            : 'Закрытие инцидента'
        }
        open={actionModalVisible}
        onCancel={() => {
          setActionModalVisible(false)
          actionForm.resetFields()
        }}
        footer={null}
      >
        <Form form={actionForm} layout="vertical" onFinish={handleAction}>
          <Form.Item
            label={
              actionType === 'contain'
                ? 'Действия по локализации'
                : actionType === 'remediate'
                ? 'Действия по устранению'
                : 'Выводы (lessons learned)'
            }
            name={actionType === 'close' ? 'lessons_learned' : 'actions'}
            rules={[{ required: true, message: 'Введите описание' }]}
          >
            <TextArea rows={6} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Подтвердить
              </Button>
              <Button onClick={() => setActionModalVisible(false)}>Отмена</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}

const Statistic = ({ title, value }: { title: string; value: number }) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>{value}</div>
    <div style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{title}</div>
  </div>
)

const Stat = Statistic
