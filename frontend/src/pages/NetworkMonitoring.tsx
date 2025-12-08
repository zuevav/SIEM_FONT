import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Select,
  DatePicker,
  Button,
  Badge,
  Tooltip,
  Typography,
  Alert,
  Descriptions,
  Modal,
} from 'antd'
import {
  ReloadOutlined,
  WifiOutlined,
  DisconnectOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  PrinterOutlined,
  DesktopOutlined,
  CloudServerOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Event, EventFilter } from '@/types'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select

// Device type icons
const DEVICE_TYPE_ICONS: Record<string, React.ReactNode> = {
  printer: <PrinterOutlined />,
  switch: <DesktopOutlined />,
  router: <CloudServerOutlined />,
  firewall: <SafetyOutlined />,
  ups: <ThunderboltOutlined />,
}

// Severity colors
const SEVERITY_COLORS: Record<number, string> = {
  1: 'blue',
  2: 'gold',
  3: 'orange',
  4: 'red',
}

export default function NetworkMonitoring() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Statistics
  const [stats, setStats] = useState({
    total24h: 0,
    online: 0,
    warning: 0,
    offline: 0,
  })

  // Filters
  const [sourceType, setSourceType] = useState<string>('all')
  const [severity, setSeverity] = useState<number | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)

  // Modal
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)

  // Load events
  const loadEvents = async () => {
    setLoading(true)
    try {
      const filter: EventFilter = {
        source_type: sourceType === 'all' ? undefined : sourceType,
        severity: severity ? [severity] : undefined,
        start_time: dateRange ? dateRange[0].toISOString() : dayjs().subtract(24, 'hour').toISOString(),
        end_time: dateRange ? dateRange[1].toISOString() : dayjs().toISOString(),
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }

      const response = await apiService.getEvents(filter)

      // Filter to only show network-related events
      const networkEvents = response.items.filter(
        (e) => ['SNMP', 'Syslog', 'NetFlow', 'SNMP-Trap'].includes(e.SourceType)
      )

      setEvents(networkEvents)
      setTotal(networkEvents.length)

      // Calculate statistics
      calculateStats(networkEvents)
    } catch (error) {
      console.error('Failed to load network events:', error)
    } finally {
      setLoading(false)
    }
  }

  // Calculate statistics
  const calculateStats = (eventsData: Event[]) => {
    const now = dayjs()
    const total24h = eventsData.filter((e) => dayjs(e.EventTime).isAfter(now.subtract(24, 'hour'))).length

    // Group by computer/device
    const deviceMap = new Map<string, { lastSeen: string; severity: number }>()
    eventsData.forEach((e) => {
      const device = e.Computer || e.SourceIP || 'unknown'
      const existing = deviceMap.get(device)
      if (!existing || dayjs(e.EventTime).isAfter(dayjs(existing.lastSeen))) {
        deviceMap.set(device, { lastSeen: e.EventTime, severity: e.Severity })
      }
    })

    let online = 0
    let warning = 0
    let offline = 0

    deviceMap.forEach((info) => {
      const minutesSinceLastSeen = dayjs().diff(dayjs(info.lastSeen), 'minute')
      if (minutesSinceLastSeen < 30) {
        if (info.severity >= 3) {
          warning++
        } else {
          online++
        }
      } else {
        offline++
      }
    })

    setStats({ total24h, online, warning, offline })
  }

  useEffect(() => {
    loadEvents()
  }, [page, pageSize, sourceType, severity, dateRange])

  // Handle view details
  const handleViewDetails = (event: Event) => {
    setSelectedEvent(event)
    setViewModalVisible(true)
  }

  // Get device status badge
  const getDeviceStatusBadge = (lastSeen: string, severity: number) => {
    const minutesSinceLastSeen = dayjs().diff(dayjs(lastSeen), 'minute')
    if (minutesSinceLastSeen >= 30) {
      return <Badge status="error" text="Offline" />
    }
    if (severity >= 3) {
      return <Badge status="warning" text="Warning" />
    }
    return <Badge status="success" text="Online" />
  }

  // Table columns
  const columns: ColumnsType<Event> = [
    {
      title: 'Time',
      dataIndex: 'EventTime',
      key: 'EventTime',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.EventTime).unix() - dayjs(b.EventTime).unix(),
    },
    {
      title: 'Source',
      dataIndex: 'SourceType',
      key: 'SourceType',
      width: 100,
      render: (type: string) => {
        const color = type === 'SNMP' ? 'blue' : type === 'Syslog' ? 'green' : type === 'NetFlow' ? 'purple' : 'cyan'
        return <Tag color={color}>{type}</Tag>
      },
    },
    {
      title: 'Device',
      key: 'device',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.Computer || record.SourceIP || 'Unknown'}</Text>
          {record.SourceIP && record.Computer && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.SourceIP}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => getDeviceStatusBadge(record.EventTime, record.Severity),
    },
    {
      title: 'Event Code',
      dataIndex: 'EventCode',
      key: 'EventCode',
      width: 100,
    },
    {
      title: 'Severity',
      dataIndex: 'Severity',
      key: 'Severity',
      width: 100,
      render: (severity: number) => {
        const labels = ['', 'Low', 'Medium', 'High', 'Critical']
        return <Tag color={SEVERITY_COLORS[severity]}>{labels[severity]}</Tag>
      },
    },
    {
      title: 'Message',
      dataIndex: 'Message',
      key: 'Message',
      ellipsis: true,
      render: (message: string) => (
        <Tooltip title={message}>
          <Text ellipsis style={{ maxWidth: 300 }}>
            {message}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetails(record)} />
      ),
    },
  ]

  return (
    <div>
      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Events (24h)"
              value={stats.total24h}
              prefix={<WifiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Online Devices"
              value={stats.online}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Warning Devices"
              value={stats.warning}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Offline Devices"
              value={stats.offline}
              prefix={<DisconnectOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Info Alert */}
      <Alert
        message="Network Monitoring"
        description="This page displays events from network devices monitored via SNMP, Syslog, and NetFlow. Network Monitor service must be running to collect data."
        type="info"
        showIcon
        icon={<WifiOutlined />}
        style={{ marginBottom: 16 }}
      />

      {/* Events Table */}
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              Network Device Events
            </Title>
            <Badge count={total} showZero style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadEvents}>
            Refresh
          </Button>
        }
      >
        {/* Filters */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="Source Type"
            value={sourceType}
            onChange={setSourceType}
            style={{ width: 150 }}
          >
            <Option value="all">All Sources</Option>
            <Option value="SNMP">SNMP</Option>
            <Option value="Syslog">Syslog</Option>
            <Option value="NetFlow">NetFlow</Option>
            <Option value="SNMP-Trap">SNMP Trap</Option>
          </Select>

          <Select
            placeholder="Severity"
            value={severity}
            onChange={setSeverity}
            style={{ width: 120 }}
            allowClear
          >
            <Option value={1}>Low</Option>
            <Option value={2}>Medium</Option>
            <Option value={3}>High</Option>
            <Option value={4}>Critical</Option>
          </Select>

          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
            showTime
            format="YYYY-MM-DD HH:mm"
            style={{ width: 400 }}
          />
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={events}
          rowKey="EventId"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} events`,
            onChange: (page, pageSize) => {
              setPage(page)
              setPageSize(pageSize)
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* View Details Modal */}
      <Modal
        title="Network Event Details"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false)
          setSelectedEvent(null)
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedEvent && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Event ID">{selectedEvent.EventId}</Descriptions.Item>
            <Descriptions.Item label="Event Time">
              {dayjs(selectedEvent.EventTime).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Source Type">
              <Tag color={selectedEvent.SourceType === 'SNMP' ? 'blue' : 'green'}>
                {selectedEvent.SourceType}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Event Code">{selectedEvent.EventCode}</Descriptions.Item>
            <Descriptions.Item label="Device">
              {selectedEvent.Computer || selectedEvent.SourceIP || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="IP Address">{selectedEvent.SourceIP || '-'}</Descriptions.Item>
            <Descriptions.Item label="Severity">
              <Tag color={SEVERITY_COLORS[selectedEvent.Severity]}>
                {['', 'Low', 'Medium', 'High', 'Critical'][selectedEvent.Severity]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Provider">{selectedEvent.Provider || '-'}</Descriptions.Item>
            <Descriptions.Item label="Message" span={2}>
              {selectedEvent.Message}
            </Descriptions.Item>
            {selectedEvent.ProcessName && (
              <Descriptions.Item label="Process" span={2}>
                {selectedEvent.ProcessName}
                {selectedEvent.ProcessCommandLine && ` - ${selectedEvent.ProcessCommandLine}`}
              </Descriptions.Item>
            )}
            {selectedEvent.SourceIP && selectedEvent.DestinationIP && (
              <>
                <Descriptions.Item label="Source">
                  {selectedEvent.SourceIP}:{selectedEvent.SourcePort || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Destination">
                  {selectedEvent.DestinationIP}:{selectedEvent.DestinationPort || '-'}
                </Descriptions.Item>
              </>
            )}
            {selectedEvent.Protocol && (
              <Descriptions.Item label="Protocol">{selectedEvent.Protocol}</Descriptions.Item>
            )}
            <Descriptions.Item label="Collected At">
              {dayjs(selectedEvent.CollectedAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
