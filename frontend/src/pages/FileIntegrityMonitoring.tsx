import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Modal,
  Descriptions,
  Typography,
  message,
  Spin,
  Tooltip,
} from 'antd'
import {
  FileTextOutlined,
  DeleteOutlined,
  EditOutlined,
  FolderOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import apiService from '@/services/api'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker
const { Option } = Select

interface FIMEvent {
  event_id: number
  event_time: string
  event_code: number
  event_type: string
  hostname: string
  agent_id: string
  file_path?: string
  process_name?: string
  target_user?: string
  message: string
  severity: number
  category?: string
  file_hash?: string
  registry_key?: string
  registry_value?: string
  event_type_detail?: string
  details?: string
  new_name?: string
}

const FileIntegrityMonitoring: React.FC = () => {
  const [events, setEvents] = useState<FIMEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [selectedEvent, setSelectedEvent] = useState<any>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  // Statistics
  const [stats, setStats] = useState<any>(null)
  const [statsLoading, setStatsLoading] = useState(false)

  // Filters
  const [filters, setFilters] = useState({
    last_hours: 24,
    event_type: undefined as string | undefined,
    file_path: undefined as string | undefined,
    registry_key: undefined as string | undefined,
    process_name: undefined as string | undefined,
    hostname: undefined as string | undefined,
  })

  useEffect(() => {
    loadEvents()
    loadStatistics()
  }, [currentPage, pageSize, filters])

  const loadEvents = async () => {
    try {
      setLoading(true)
      const offset = (currentPage - 1) * pageSize
      const response = await apiService.listFIMEvents({
        ...filters,
        limit: pageSize,
        offset,
      })
      setEvents(response.events)
      setTotal(response.total)
    } catch (error: any) {
      console.error('Failed to load FIM events:', error)
      message.error('Не удалось загрузить события FIM')
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      setStatsLoading(true)
      const response = await apiService.getFIMStatistics(filters.last_hours || 24)
      setStats(response)
    } catch (error: any) {
      console.error('Failed to load FIM statistics:', error)
    } finally {
      setStatsLoading(false)
    }
  }

  const viewEventDetails = async (eventId: number) => {
    try {
      const event = await apiService.getFIMEvent(eventId)
      setSelectedEvent(event)
      setDetailModalVisible(true)
    } catch (error: any) {
      console.error('Failed to load event details:', error)
      message.error('Не удалось загрузить детали события')
    }
  }

  const getSeverityTag = (severity: number) => {
    const severityMap: Record<number, { color: string; text: string }> = {
      0: { color: 'default', text: 'Инфо' },
      1: { color: 'blue', text: 'Низкая' },
      2: { color: 'orange', text: 'Средняя' },
      3: { color: 'red', text: 'Высокая' },
      4: { color: 'purple', text: 'Критичная' },
    }
    const { color, text } = severityMap[severity] || { color: 'default', text: 'Неизвестно' }
    return <Tag color={color}>{text}</Tag>
  }

  const getEventTypeIcon = (eventCode: number) => {
    const iconMap: Record<number, any> = {
      11: <FileTextOutlined style={{ color: '#52c41a' }} />,
      23: <DeleteOutlined style={{ color: '#ff4d4f' }} />,
      26: <DeleteOutlined style={{ color: '#ff7a45' }} />,
      12: <FolderOutlined style={{ color: '#1890ff' }} />,
      13: <EditOutlined style={{ color: '#faad14' }} />,
      14: <EditOutlined style={{ color: '#722ed1' }} />,
    }
    return iconMap[eventCode] || <InfoCircleOutlined />
  }

  const columns: ColumnsType<FIMEvent> = [
    {
      title: 'Время',
      dataIndex: 'event_time',
      key: 'event_time',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
    },
    {
      title: 'Тип',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 200,
      render: (type: string, record: FIMEvent) => (
        <Space>
          {getEventTypeIcon(record.event_code)}
          <Text>{type}</Text>
        </Space>
      ),
    },
    {
      title: 'Хост',
      dataIndex: 'hostname',
      key: 'hostname',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Путь',
      key: 'path',
      ellipsis: true,
      render: (record: FIMEvent) => {
        const path = record.file_path || record.registry_key
        return path ? (
          <Tooltip title={path}>
            <Text code style={{ fontSize: '12px' }}>
              {path}
            </Text>
          </Tooltip>
        ) : (
          '-'
        )
      },
    },
    {
      title: 'Процесс',
      dataIndex: 'process_name',
      key: 'process_name',
      width: 180,
      ellipsis: true,
      render: (name: string) =>
        name ? (
          <Tooltip title={name}>
            <Text code style={{ fontSize: '12px' }}>
              {name.split('\\').pop()}
            </Text>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: 'Пользователь',
      dataIndex: 'target_user',
      key: 'target_user',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: number) => getSeverityTag(severity),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      render: (record: FIMEvent) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => viewEventDetails(record.event_id)}
        >
          Детали
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <FolderOutlined /> File Integrity Monitoring (FIM)
      </Title>
      <Paragraph>
        Мониторинг изменений файлов и реестра Windows через Sysmon
      </Paragraph>

      {/* Statistics Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="Всего событий"
              value={stats?.total_fim_events || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="Критичных изменений"
              value={stats?.critical_changes || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="Файлов создано"
              value={stats?.events_by_type?.['File Created'] || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="Файлов удалено"
              value={
                (stats?.events_by_type?.['File Deleted'] || 0) +
                (stats?.events_by_type?.['File Delete Detected'] || 0)
              }
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<DeleteOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            style={{ width: 180 }}
            placeholder="Период"
            value={filters.last_hours}
            onChange={(value) => setFilters({ ...filters, last_hours: value })}
          >
            <Option value={1}>Последний час</Option>
            <Option value={6}>Последние 6 часов</Option>
            <Option value={24}>Последние 24 часа</Option>
            <Option value={72}>Последние 3 дня</Option>
            <Option value={168}>Последняя неделя</Option>
          </Select>

          <Select
            style={{ width: 200 }}
            placeholder="Тип события"
            allowClear
            value={filters.event_type}
            onChange={(value) => setFilters({ ...filters, event_type: value })}
          >
            <Option value="file_created">Файл создан</Option>
            <Option value="file_deleted">Файл удален</Option>
            <Option value="registry_create">Ключ реестра создан/удален</Option>
            <Option value="registry_set">Значение реестра установлено</Option>
            <Option value="registry_rename">Ключ реестра переименован</Option>
          </Select>

          <Input
            style={{ width: 250 }}
            placeholder="Путь файла или реестра"
            allowClear
            value={filters.file_path}
            onChange={(e) => setFilters({ ...filters, file_path: e.target.value })}
            prefix={<FolderOutlined />}
          />

          <Input
            style={{ width: 200 }}
            placeholder="Процесс"
            allowClear
            value={filters.process_name}
            onChange={(e) => setFilters({ ...filters, process_name: e.target.value })}
          />

          <Input
            style={{ width: 180 }}
            placeholder="Хост"
            allowClear
            value={filters.hostname}
            onChange={(e) => setFilters({ ...filters, hostname: e.target.value })}
          />

          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => {
              setCurrentPage(1)
              loadEvents()
              loadStatistics()
            }}
          >
            Обновить
          </Button>
        </Space>
      </Card>

      {/* Events Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={events}
          loading={loading}
          rowKey="event_id"
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
            pageSizeOptions: ['20', '50', '100', '200'],
            onChange: (page, size) => {
              setCurrentPage(page)
              setPageSize(size)
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* Event Detail Modal */}
      <Modal
        title={
          <Space>
            {selectedEvent && getEventTypeIcon(selectedEvent.event_code)}
            <span>Детали FIM события</span>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Закрыть
          </Button>,
        ]}
        width={800}
      >
        {selectedEvent && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="ID события" span={1}>
              {selectedEvent.event_id}
            </Descriptions.Item>
            <Descriptions.Item label="Время" span={1}>
              {dayjs(selectedEvent.event_time).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>

            <Descriptions.Item label="Тип события" span={1}>
              {selectedEvent.event_type}
            </Descriptions.Item>
            <Descriptions.Item label="Event Code" span={1}>
              {selectedEvent.event_code}
            </Descriptions.Item>

            <Descriptions.Item label="Хост" span={1}>
              {selectedEvent.hostname}
            </Descriptions.Item>
            <Descriptions.Item label="Agent ID" span={1}>
              <Text code>{selectedEvent.agent_id}</Text>
            </Descriptions.Item>

            <Descriptions.Item label="Severity" span={2}>
              {getSeverityTag(selectedEvent.severity)}
            </Descriptions.Item>

            {selectedEvent.file_path && (
              <Descriptions.Item label="Путь файла" span={2}>
                <Text code copyable>
                  {selectedEvent.file_path}
                </Text>
              </Descriptions.Item>
            )}

            {selectedEvent.file_hash && (
              <Descriptions.Item label="Хеш файла" span={2}>
                <Text code copyable style={{ fontSize: '11px' }}>
                  {selectedEvent.file_hash}
                </Text>
              </Descriptions.Item>
            )}

            {selectedEvent.registry_key && (
              <Descriptions.Item label="Ключ реестра" span={2}>
                <Text code copyable>
                  {selectedEvent.registry_key}
                </Text>
              </Descriptions.Item>
            )}

            {selectedEvent.target_object && (
              <Descriptions.Item label="Target Object" span={2}>
                <Text code copyable>
                  {selectedEvent.target_object}
                </Text>
              </Descriptions.Item>
            )}

            {selectedEvent.registry_value && (
              <Descriptions.Item label="Значение реестра" span={2}>
                <Text code>{selectedEvent.registry_value}</Text>
              </Descriptions.Item>
            )}

            {selectedEvent.registry_details && (
              <Descriptions.Item label="Детали" span={2}>
                <Text code>{selectedEvent.registry_details}</Text>
              </Descriptions.Item>
            )}

            {selectedEvent.event_type_detail && (
              <Descriptions.Item label="Операция" span={2}>
                <Tag>{selectedEvent.event_type_detail}</Tag>
              </Descriptions.Item>
            )}

            {selectedEvent.new_name && (
              <Descriptions.Item label="Новое имя" span={2}>
                <Text code>{selectedEvent.new_name}</Text>
              </Descriptions.Item>
            )}

            {selectedEvent.process_name && (
              <Descriptions.Item label="Процесс" span={2}>
                <Text code copyable>
                  {selectedEvent.process_name}
                </Text>
              </Descriptions.Item>
            )}

            {selectedEvent.process_id && (
              <Descriptions.Item label="Process ID" span={1}>
                {selectedEvent.process_id}
              </Descriptions.Item>
            )}

            {selectedEvent.target_user && (
              <Descriptions.Item label="Пользователь" span={1}>
                {selectedEvent.target_user}
              </Descriptions.Item>
            )}

            {selectedEvent.process_command_line && (
              <Descriptions.Item label="Command Line" span={2}>
                <Text code style={{ fontSize: '11px', wordBreak: 'break-all' }}>
                  {selectedEvent.process_command_line}
                </Text>
              </Descriptions.Item>
            )}

            <Descriptions.Item label="Сообщение" span={2}>
              {selectedEvent.message}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default FileIntegrityMonitoring
