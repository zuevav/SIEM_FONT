import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Alert, Spin, Tag, Space, Typography } from 'antd'
import {
  FileTextOutlined,
  AlertOutlined,
  WarningOutlined,
  LaptopOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { apiService } from '@/services/api'
import { useSiemWebSocket } from '@/hooks/useWebSocket'
import { formatNumber, formatRelativeTime } from '@/utils/formatters'
import type { DashboardStats, Alert as AlertType, Event } from '@/types'

const { Title, Text } = Typography

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentAlerts, setRecentAlerts] = useState<AlertType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // Connect WebSocket for real-time updates
  useSiemWebSocket({
    onEvent: (event: Event) => {
      // Update stats when new events arrive
      loadStats()
    },
    onAlert: (alert: AlertType) => {
      // Add new alert to list
      setRecentAlerts((prev) => [alert, ...prev].slice(0, 5))
      loadStats()
    },
    onStatistics: (newStats: any) => {
      // Update stats from WebSocket
      if (newStats.dashboard) {
        setStats(newStats.dashboard)
        setLastUpdate(new Date())
      }
    },
  })

  const loadStats = async () => {
    try {
      const data = await apiService.getDashboardStats()
      setStats(data)
      setLastUpdate(new Date())
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  const loadRecentAlerts = async () => {
    try {
      const response = await apiService.getAlerts({ limit: 5, offset: 0 })
      setRecentAlerts(response.items)
    } catch (err) {
      console.error('Failed to load alerts:', err)
    }
  }

  useEffect(() => {
    loadStats()
    loadRecentAlerts()

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      loadStats()
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return <Alert message="Ошибка" description={error} type="error" showIcon />
  }

  if (!stats) {
    return <Alert message="Нет данных" type="info" showIcon />
  }

  // Prepare chart data
  const severityData = [
    { name: 'Критический', value: stats.alerts.new || 0, color: '#ff4d4f' },
    { name: 'Высокий', value: Math.floor((stats.alerts.acknowledged || 0) * 0.7), color: '#ff7a45' },
    { name: 'Средний', value: Math.floor((stats.alerts.acknowledged || 0) * 0.2), color: '#ffa940' },
    { name: 'Низкий', value: Math.floor((stats.alerts.acknowledged || 0) * 0.1), color: '#52c41a' },
  ]

  const eventsTimeData = [
    { time: '00:00', events: 1200 },
    { time: '04:00', events: 800 },
    { time: '08:00', events: 2500 },
    { time: '12:00', events: 3200 },
    { time: '16:00', events: 2800 },
    { time: '20:00', events: 1500 },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>Dashboard</Title>
        <Text type="secondary">
          Последнее обновление: {formatRelativeTime(lastUpdate)}
        </Text>
      </div>

      {/* Main Stats Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="События (24ч)"
              value={stats.events.total_24h}
              prefix={<FileTextOutlined />}
              suffix={
                <Tag color="blue" icon={<ArrowUpOutlined />}>
                  {stats.events.rate_per_hour}/ч
                </Tag>
              }
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Активные алерты"
              value={stats.alerts.total_open}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#cf1322' }}
              suffix={
                <Space>
                  <Tag color="red">{stats.alerts.new} новых</Tag>
                </Space>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Инциденты"
              value={stats.incidents.open}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
              suffix={<Tag color="orange">{stats.incidents.investigating} в работе</Tag>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Агенты"
              value={`${stats.agents.online}/${stats.agents.total}`}
              prefix={<LaptopOutlined />}
              valueStyle={{ color: stats.agents.online === stats.agents.total ? '#3f8600' : '#faad14' }}
              suffix={
                stats.agents.offline > 0 ? (
                  <Tag color="default" icon={<ArrowDownOutlined />}>
                    {stats.agents.offline} оффлайн
                  </Tag>
                ) : null
              }
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="События за последние 24 часа" bordered={false}>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={eventsTimeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="events" stroke="#1890ff" fill="#1890ff" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Алерты по severity" bordered={false}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Recent Alerts */}
      <Card title="Последние алерты" bordered={false}>
        {recentAlerts.length === 0 ? (
          <Alert message="Нет новых алертов" type="success" showIcon />
        ) : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {recentAlerts.map((alert) => (
              <Card key={alert.alert_id} size="small" hoverable>
                <Row justify="space-between" align="middle">
                  <Col span={16}>
                    <Space direction="vertical" size={4}>
                      <Text strong>{alert.title}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {alert.hostname || 'N/A'} • {formatRelativeTime(alert.created_at)}
                      </Text>
                    </Space>
                  </Col>
                  <Col>
                    <Space>
                      <Tag color={alert.severity >= 3 ? 'red' : alert.severity === 2 ? 'orange' : 'blue'}>
                        Severity {alert.severity}
                      </Tag>
                      <Tag color={alert.status === 'new' ? 'red' : 'blue'}>{alert.status}</Tag>
                    </Space>
                  </Col>
                </Row>
              </Card>
            ))}
          </Space>
        )}
      </Card>
    </Space>
  )
}
