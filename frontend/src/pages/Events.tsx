import { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Space,
  Input,
  Select,
  Button,
  Tag,
  Typography,
  DatePicker,
  Row,
  Col,
  Drawer,
  Descriptions,
  Alert,
  Tooltip,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  EyeOutlined,
  FilterOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { apiService } from '@/services/api'
import { formatDateTime, getSeverityColor, getSeverityText, getEventCodeDescription, truncate } from '@/utils/formatters'
import type { Event, EventFilter } from '@/types'

const { RangePicker } = DatePicker
const { Text, Title } = Typography

export default function Events() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState<EventFilter>({
    limit: 50,
    offset: 0,
  })
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)

  const loadEvents = async () => {
    setLoading(true)
    try {
      const response = await apiService.getEvents(filter)
      setEvents(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load events:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEvents()
  }, [filter])

  const handleTableChange = (pagination: any) => {
    setFilter({
      ...filter,
      limit: pagination.pageSize,
      offset: (pagination.current - 1) * pagination.pageSize,
    })
  }

  const handleSearch = (value: string) => {
    setFilter({ ...filter, search: value, offset: 0 })
  }

  const handleFilterChange = (key: keyof EventFilter, value: any) => {
    setFilter({ ...filter, [key]: value, offset: 0 })
  }

  const handleExport = async () => {
    try {
      const blob = await apiService.exportEvents(filter)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `events_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const showEventDetails = (event: Event) => {
    setSelectedEvent(event)
    setDrawerVisible(true)
  }

  const columns: ColumnsType<Event> = [
    {
      title: 'Время',
      dataIndex: 'EventTime',
      key: 'EventTime',
      width: 160,
      render: (time) => formatDateTime(time),
      sorter: true,
    },
    {
      title: 'Severity',
      dataIndex: 'Severity',
      key: 'Severity',
      width: 100,
      render: (severity) => (
        <Tag color={getSeverityColor(severity)}>{getSeverityText(severity)}</Tag>
      ),
      filters: [
        { text: 'Критический', value: 4 },
        { text: 'Высокий', value: 3 },
        { text: 'Средний', value: 2 },
        { text: 'Низкий', value: 1 },
        { text: 'Инфо', value: 0 },
      ],
    },
    {
      title: 'Компьютер',
      dataIndex: 'Computer',
      key: 'Computer',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Event Code',
      dataIndex: 'EventCode',
      key: 'EventCode',
      width: 120,
      render: (code) => (
        <Tooltip title={getEventCodeDescription(code)}>
          <Tag>{code}</Tag>
        </Tooltip>
      ),
    },
    {
      title: 'Source',
      dataIndex: 'SourceType',
      key: 'SourceType',
      width: 120,
      ellipsis: true,
    },
    {
      title: 'Пользователь',
      dataIndex: 'SubjectUser',
      key: 'SubjectUser',
      width: 150,
      ellipsis: true,
      render: (user) => user || '-',
    },
    {
      title: 'Процесс',
      dataIndex: 'ProcessName',
      key: 'ProcessName',
      width: 200,
      ellipsis: true,
      render: (name) => name || '-',
    },
    {
      title: 'AI',
      key: 'AI',
      width: 80,
      render: (_,record) => {
        if (!record.AIProcessed) return null
        if (record.AIIsAttack) {
          return <Tag color="red">Attack</Tag>
        }
        if (record.AIScore && record.AIScore > 70) {
          return <Tag color="orange">Suspicious</Tag>
        }
        return null
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
          onClick={() => showEventDetails(record)}
        >
          Детали
        </Button>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={4} style={{ margin: 0 }}>
                События безопасности
              </Title>
            </Col>
            <Col>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadEvents}>
                  Обновить
                </Button>
                <Button icon={<DownloadOutlined />} onClick={handleExport}>
                  Экспорт
                </Button>
              </Space>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Input
                placeholder="Поиск..."
                prefix={<SearchOutlined />}
                allowClear
                onPressEnter={(e) => handleSearch(e.currentTarget.value)}
              />
            </Col>
            <Col xs={24} md={6}>
              <Select
                style={{ width: '100%' }}
                placeholder="Event Code"
                allowClear
                showSearch
                onChange={(value) => handleFilterChange('event_code', value ? [value] : undefined)}
                options={[
                  { label: '4624 - Успешный вход', value: 4624 },
                  { label: '4625 - Неудачный вход', value: 4625 },
                  { label: '4688 - Создан процесс', value: 4688 },
                  { label: '4720 - Создан пользователь', value: 4720 },
                  { label: '7045 - Новая служба', value: 7045 },
                ]}
              />
            </Col>
            <Col xs={24} md={6}>
              <Select
                style={{ width: '100%' }}
                placeholder="Source Type"
                allowClear
                onChange={(value) => handleFilterChange('source_type', value)}
                options={[
                  { label: 'Windows Security', value: 'windows_security' },
                  { label: 'Windows System', value: 'windows_system' },
                  { label: 'Sysmon', value: 'sysmon' },
                  { label: 'PowerShell', value: 'powershell' },
                  { label: 'Defender', value: 'defender' },
                ]}
              />
            </Col>
            <Col xs={24} md={4}>
              <Select
                style={{ width: '100%' }}
                placeholder="AI Attack"
                allowClear
                onChange={(value) => handleFilterChange('ai_is_attack', value)}
                options={[
                  { label: 'Атака', value: true },
                  { label: 'Не атака', value: false },
                ]}
              />
            </Col>
          </Row>

          <Alert
            message={`Найдено событий: ${total}`}
            type="info"
            showIcon
            icon={<FilterOutlined />}
          />
        </Space>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={events}
          rowKey="EventId"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            total,
            current: (filter.offset || 0) / (filter.limit || 50) + 1,
            pageSize: filter.limit || 50,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} событий`,
            pageSizeOptions: ['25', '50', '100', '200'],
          }}
          scroll={{ x: 1400 }}
          size="small"
        />
      </Card>

      {/* Event Details Drawer */}
      <Drawer
        title="Детали события"
        placement="right"
        width={720}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedEvent && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Event ID">{selectedEvent.EventId}</Descriptions.Item>
            <Descriptions.Item label="Event GUID">{selectedEvent.EventGuid}</Descriptions.Item>
            <Descriptions.Item label="Время">{formatDateTime(selectedEvent.EventTime)}</Descriptions.Item>
            <Descriptions.Item label="Компьютер">{selectedEvent.Computer}</Descriptions.Item>
            <Descriptions.Item label="Event Code">
              {selectedEvent.EventCode} - {getEventCodeDescription(selectedEvent.EventCode)}
            </Descriptions.Item>
            <Descriptions.Item label="Severity">
              <Tag color={getSeverityColor(selectedEvent.Severity)}>
                {getSeverityText(selectedEvent.Severity)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Source Type">{selectedEvent.SourceType}</Descriptions.Item>
            <Descriptions.Item label="Channel">{selectedEvent.Channel || '-'}</Descriptions.Item>
            <Descriptions.Item label="Provider">{selectedEvent.Provider || '-'}</Descriptions.Item>

            {selectedEvent.SubjectUser && (
              <Descriptions.Item label="Subject User">
                {selectedEvent.SubjectDomain && `${selectedEvent.SubjectDomain}\\`}
                {selectedEvent.SubjectUser}
              </Descriptions.Item>
            )}
            {selectedEvent.TargetUser && (
              <Descriptions.Item label="Target User">
                {selectedEvent.TargetDomain && `${selectedEvent.TargetDomain}\\`}
                {selectedEvent.TargetUser}
              </Descriptions.Item>
            )}

            {selectedEvent.ProcessName && (
              <>
                <Descriptions.Item label="Process Name">{selectedEvent.ProcessName}</Descriptions.Item>
                <Descriptions.Item label="Process Path">{selectedEvent.ProcessPath || '-'}</Descriptions.Item>
                <Descriptions.Item label="Process ID">{selectedEvent.ProcessID || '-'}</Descriptions.Item>
                {selectedEvent.ProcessCommandLine && (
                  <Descriptions.Item label="Command Line">{selectedEvent.ProcessCommandLine}</Descriptions.Item>
                )}
              </>
            )}

            {(selectedEvent.SourceIP || selectedEvent.DestinationIP) && (
              <>
                <Descriptions.Item label="Source IP">{selectedEvent.SourceIP || '-'}</Descriptions.Item>
                <Descriptions.Item label="Source Port">{selectedEvent.SourcePort || '-'}</Descriptions.Item>
                <Descriptions.Item label="Destination IP">{selectedEvent.DestinationIP || '-'}</Descriptions.Item>
                <Descriptions.Item label="Destination Port">{selectedEvent.DestinationPort || '-'}</Descriptions.Item>
                <Descriptions.Item label="Protocol">{selectedEvent.Protocol || '-'}</Descriptions.Item>
              </>
            )}

            {selectedEvent.FilePath && (
              <>
                <Descriptions.Item label="File Path">{selectedEvent.FilePath}</Descriptions.Item>
                <Descriptions.Item label="File Hash">{selectedEvent.FileHash || '-'}</Descriptions.Item>
              </>
            )}

            {selectedEvent.AIProcessed && (
              <>
                <Descriptions.Item label="AI Processed">
                  <Tag color={selectedEvent.AIIsAttack ? 'red' : 'green'}>
                    {selectedEvent.AIIsAttack ? 'Атака' : 'Нормальное'}
                  </Tag>
                </Descriptions.Item>
                {selectedEvent.AIScore && (
                  <Descriptions.Item label="AI Score">{selectedEvent.AIScore.toFixed(2)}</Descriptions.Item>
                )}
                {selectedEvent.AICategory && (
                  <Descriptions.Item label="AI Category">{selectedEvent.AICategory}</Descriptions.Item>
                )}
                {selectedEvent.AIDescription && (
                  <Descriptions.Item label="AI Description">{selectedEvent.AIDescription}</Descriptions.Item>
                )}
              </>
            )}

            {selectedEvent.Message && (
              <Descriptions.Item label="Message">{selectedEvent.Message}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </Space>
  )
}
