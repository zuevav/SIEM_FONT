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
  Statistic,
  Progress,
  Tooltip,
} from 'antd'
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  LaptopOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { apiService } from '@/services/api'
import {
  formatDateTime,
  formatRelativeTime,
  formatBytes,
  getStatusColor,
  getStatusText,
} from '@/utils/formatters'
import type { Agent, AgentStatistics } from '@/types'

const { Title, Text } = Typography

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [stats, setStats] = useState<AgentStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const loadAgents = async () => {
    setLoading(true)
    try {
      const response = await apiService.getAgents({
        limit: pageSize,
        offset: (page - 1) * pageSize,
      })
      setAgents(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load agents:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const data = await apiService.getAgentStatistics()
      setStats(data)
    } catch (error) {
      console.error('Failed to load agent stats:', error)
    }
  }

  useEffect(() => {
    loadAgents()
    loadStats()

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      loadAgents()
      loadStats()
    }, 30000)

    return () => clearInterval(interval)
  }, [page, pageSize])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'offline':
        return <CloseCircleOutlined style={{ color: '#d9d9d9' }} />
      case 'error':
        return <WarningOutlined style={{ color: '#ff4d4f' }} />
      default:
        return null
    }
  }

  const columns: ColumnsType<Agent> = [
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'Status',
      width: 100,
      render: (status) => (
        <Tooltip title={getStatusText(status)}>
          <Tag icon={getStatusIcon(status)} color={getStatusColor(status)}>
            {getStatusText(status)}
          </Tag>
        </Tooltip>
      ),
      filters: [
        { text: 'Онлайн', value: 'online' },
        { text: 'Оффлайн', value: 'offline' },
        { text: 'Ошибка', value: 'error' },
      ],
      onFilter: (value, record) => record.Status === value,
    },
    {
      title: 'Hostname',
      dataIndex: 'Hostname',
      key: 'Hostname',
      width: 200,
      ellipsis: true,
      sorter: (a, b) => a.Hostname.localeCompare(b.Hostname),
      render: (hostname, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{hostname}</Text>
          {record.IPAddress && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.IPAddress}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'ОС',
      dataIndex: 'OSVersion',
      key: 'OSVersion',
      width: 200,
      ellipsis: true,
      render: (os, record) => (
        <Space direction="vertical" size={0}>
          <Text>{os || '-'}</Text>
          {record.OSBuild && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              Build {record.OSBuild}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Домен',
      dataIndex: 'Domain',
      key: 'Domain',
      width: 150,
      ellipsis: true,
      render: (domain) => domain || '-',
    },
    {
      title: 'Версия агента',
      dataIndex: 'AgentVersion',
      key: 'AgentVersion',
      width: 120,
      render: (version) => version || '-',
    },
    {
      title: 'Последний контакт',
      dataIndex: 'LastSeen',
      key: 'LastSeen',
      width: 150,
      render: (time) => (
        <Tooltip title={formatDateTime(time)}>
          {formatRelativeTime(time)}
        </Tooltip>
      ),
      sorter: (a, b) => new Date(a.LastSeen || 0).getTime() - new Date(b.LastSeen || 0).getTime(),
    },
    {
      title: 'События',
      dataIndex: 'EventsCollected',
      key: 'EventsCollected',
      width: 100,
      render: (events) => events?.toLocaleString() || '-',
      sorter: (a, b) => (a.EventsCollected || 0) - (b.EventsCollected || 0),
    },
    {
      title: 'Ресурсы',
      key: 'Resources',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {record.CPUCores && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                CPU: {record.CPUCores} cores
              </Text>
            </div>
          )}
          {record.TotalRAM_MB && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                RAM: {formatBytes(record.TotalRAM_MB * 1024 * 1024)}
              </Text>
            </div>
          )}
          {record.TotalDisk_GB && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Disk: {record.TotalDisk_GB} GB
              </Text>
            </div>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>Windows Агенты</Title>
        <Text type="secondary">Мониторинг агентов сбора событий</Text>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Всего агентов"
                value={stats.total}
                prefix={<LaptopOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Онлайн"
                value={stats.online}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
                suffix={
                  <Text type="secondary">
                    / {stats.total}
                  </Text>
                }
              />
              <Progress
                percent={Math.round((stats.online / stats.total) * 100)}
                strokeColor="#52c41a"
                showInfo={false}
                style={{ marginTop: 8 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Оффлайн"
                value={stats.offline}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: stats.offline > 0 ? '#faad14' : '#d9d9d9' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Ошибки"
                value={stats.error}
                prefix={<WarningOutlined />}
                valueStyle={{ color: stats.error > 0 ? '#ff4d4f' : '#d9d9d9' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Text>Всего агентов: {total}</Text>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => { loadAgents(); loadStats(); }}>
              Обновить
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={agents}
          rowKey="AgentId"
          loading={loading}
          onChange={(pagination) => {
            setPage(pagination.current || 1)
            setPageSize(pagination.pageSize || 50)
          }}
          pagination={{
            total,
            current: page,
            pageSize,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} агентов`,
            pageSizeOptions: ['25', '50', '100'],
          }}
          scroll={{ x: 1200 }}
          size="small"
          rowClassName={(record) => {
            if (record.Status === 'error') return 'row-error'
            if (record.Status === 'offline') return 'row-warning'
            return ''
          }}
        />
      </Card>
    </Space>
  )
}
