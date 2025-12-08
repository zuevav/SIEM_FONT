import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Button,
  Space,
  Tag,
  DatePicker,
  Select,
  Modal,
  Form,
  Input,
  message,
  Typography,
  Badge,
  Alert,
  Descriptions,
  Divider,
} from 'antd'
import {
  FileTextOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Incident, IncidentFilter } from '@/types'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select
const { TextArea } = Input

// Severity colors
const SEVERITY_COLORS: Record<number, string> = {
  1: 'blue',
  2: 'gold',
  3: 'orange',
  4: 'red',
}

// Status colors
const STATUS_COLORS: Record<string, string> = {
  open: 'red',
  investigating: 'orange',
  contained: 'blue',
  remediated: 'green',
  closed: 'default',
}

export default function Reports() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Statistics
  const [stats, setStats] = useState({
    totalIncidents: 0,
    reportedToCBR: 0,
    pendingReport: 0,
    criticalIncidents: 0,
  })

  // Filters
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ])
  const [severityFilter, setSeverityFilter] = useState<number | undefined>(undefined)
  const [reportedFilter, setReportedFilter] = useState<'all' | 'reported' | 'not_reported'>('all')

  // Modals
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [reportModalVisible, setReportModalVisible] = useState(false)
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)

  // Form
  const [reportForm] = Form.useForm()

  // Load incidents
  const loadIncidents = async () => {
    setLoading(true)
    try {
      const filter: IncidentFilter = {
        start_date: dateRange ? dateRange[0].toISOString() : undefined,
        end_date: dateRange ? dateRange[1].toISOString() : undefined,
        severity: severityFilter ? [severityFilter] : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }

      const response = await apiService.getIncidents(filter)

      let filteredIncidents = response.items
      if (reportedFilter === 'reported') {
        filteredIncidents = filteredIncidents.filter((i) => i.IsReportedToCBR)
      } else if (reportedFilter === 'not_reported') {
        filteredIncidents = filteredIncidents.filter((i) => !i.IsReportedToCBR)
      }

      setIncidents(filteredIncidents)
      setTotal(response.total)

      // Calculate statistics
      calculateStats(response.items)
    } catch (error) {
      message.error('Failed to load incidents')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // Calculate statistics
  const calculateStats = (data: Incident[]) => {
    const totalIncidents = data.length
    const reportedToCBR = data.filter((i) => i.IsReportedToCBR).length
    const pendingReport = data.filter((i) => !i.IsReportedToCBR && i.IsReportable).length
    const criticalIncidents = data.filter((i) => i.Severity === 4).length

    setStats({
      totalIncidents,
      reportedToCBR,
      pendingReport,
      criticalIncidents,
    })
  }

  useEffect(() => {
    loadIncidents()
  }, [page, pageSize, dateRange, severityFilter, reportedFilter])

  // Handle view details
  const handleViewDetails = (incident: Incident) => {
    setSelectedIncident(incident)
    setViewModalVisible(true)
  }

  // Handle report to CBR
  const handleReportToCBR = (incident: Incident) => {
    setSelectedIncident(incident)
    reportForm.resetFields()
    setReportModalVisible(true)
  }

  // Submit CBR report
  const handleSubmitReport = async (values: any) => {
    if (!selectedIncident) return

    try {
      await apiService.client.post(`/incidents/${selectedIncident.IncidentId}/cbr-report`, {
        cbr_incident_number: values.cbr_incident_number,
        report_notes: values.report_notes,
      })
      message.success('Incident reported to CBR successfully')
      setReportModalVisible(false)
      reportForm.resetFields()
      loadIncidents()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to report to CBR')
      console.error(error)
    }
  }

  // Export report
  const handleExport = (format: 'pdf' | 'excel') => {
    message.info(`Exporting report as ${format.toUpperCase()}...`)
    // В реальной реализации здесь будет API call для экспорта
  }

  // Table columns
  const columns: ColumnsType<Incident> = [
    {
      title: 'Incident ID',
      dataIndex: 'IncidentId',
      key: 'IncidentId',
      width: 100,
    },
    {
      title: 'Title',
      dataIndex: 'Title',
      key: 'Title',
      width: 250,
      ellipsis: true,
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
      title: 'Status',
      dataIndex: 'Status',
      key: 'Status',
      width: 120,
      render: (status: string) => <Tag color={STATUS_COLORS[status]}>{status}</Tag>,
    },
    {
      title: 'Detected',
      dataIndex: 'DetectedAt',
      key: 'DetectedAt',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Reportable',
      dataIndex: 'IsReportable',
      key: 'IsReportable',
      width: 100,
      render: (reportable: boolean) =>
        reportable ? <Tag color="orange">Yes</Tag> : <Tag color="default">No</Tag>,
    },
    {
      title: 'CBR Status',
      key: 'cbrStatus',
      width: 150,
      render: (_, record) =>
        record.IsReportedToCBR ? (
          <Space direction="vertical" size={0}>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              Reported
            </Tag>
            {record.CBRIncidentNumber && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                #{record.CBRIncidentNumber}
              </Text>
            )}
          </Space>
        ) : record.IsReportable ? (
          <Tag color="warning" icon={<ClockCircleOutlined />}>
            Pending
          </Tag>
        ) : (
          <Tag color="default">N/A</Tag>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetails(record)} />
          {!record.IsReportedToCBR && record.IsReportable && (
            <Button type="primary" size="small" onClick={() => handleReportToCBR(record)}>
              Report to CBR
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* Info Alert */}
      <Alert
        message="CBR Compliance Reporting"
        description="This page helps track and report security incidents to the Central Bank of Russia (ЦБ РФ) in accordance with regulations 747-П, 716-П, and 683-П."
        type="info"
        showIcon
        icon={<FileTextOutlined />}
        style={{ marginBottom: 16 }}
      />

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Incidents"
              value={stats.totalIncidents}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Reported to CBR"
              value={stats.reportedToCBR}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending Report"
              value={stats.pendingReport}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Critical Incidents"
              value={stats.criticalIncidents}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Incidents Table */}
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              Incident Reports
            </Title>
            <Badge count={total} showZero style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Space>
            <Button icon={<FilePdfOutlined />} onClick={() => handleExport('pdf')}>
              Export PDF
            </Button>
            <Button icon={<FileExcelOutlined />} onClick={() => handleExport('excel')}>
              Export Excel
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadIncidents}>
              Refresh
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <Space style={{ marginBottom: 16 }} wrap>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
            format="YYYY-MM-DD"
            style={{ width: 300 }}
          />

          <Select
            placeholder="Severity"
            value={severityFilter}
            onChange={setSeverityFilter}
            style={{ width: 120 }}
            allowClear
          >
            <Option value={1}>Low</Option>
            <Option value={2}>Medium</Option>
            <Option value={3}>High</Option>
            <Option value={4}>Critical</Option>
          </Select>

          <Select
            placeholder="CBR Status"
            value={reportedFilter}
            onChange={setReportedFilter}
            style={{ width: 150 }}
          >
            <Option value="all">All</Option>
            <Option value="reported">Reported</Option>
            <Option value="not_reported">Not Reported</Option>
          </Select>
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={incidents}
          rowKey="IncidentId"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} incidents`,
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
        title="Incident Details"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false)
          setSelectedIncident(null)
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={900}
      >
        {selectedIncident && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Incident ID">{selectedIncident.IncidentId}</Descriptions.Item>
            <Descriptions.Item label="Severity">
              <Tag color={SEVERITY_COLORS[selectedIncident.Severity]}>
                {['', 'Low', 'Medium', 'High', 'Critical'][selectedIncident.Severity]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Title" span={2}>
              {selectedIncident.Title}
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {selectedIncident.Description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Status">{selectedIncident.Status}</Descriptions.Item>
            <Descriptions.Item label="Priority">{selectedIncident.Priority}</Descriptions.Item>
            <Descriptions.Item label="Detected At">
              {dayjs(selectedIncident.DetectedAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Closed At">
              {selectedIncident.ClosedAt ? dayjs(selectedIncident.ClosedAt).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Alerts">{selectedIncident.AlertCount || 0}</Descriptions.Item>
            <Descriptions.Item label="Events">{selectedIncident.EventCount || 0}</Descriptions.Item>
            <Descriptions.Item label="Affected Assets">{selectedIncident.AffectedAssets || 0}</Descriptions.Item>
            <Descriptions.Item label="Category">{selectedIncident.IncidentCategory || '-'}</Descriptions.Item>

            <Divider>CBR Compliance</Divider>

            <Descriptions.Item label="Reportable">
              {selectedIncident.IsReportable ? (
                <Tag color="orange">Yes</Tag>
              ) : (
                <Tag color="default">No</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Reported to CBR">
              {selectedIncident.IsReportedToCBR ? (
                <Tag color="success">Yes</Tag>
              ) : (
                <Tag color="default">No</Tag>
              )}
            </Descriptions.Item>
            {selectedIncident.CBRReportDate && (
              <Descriptions.Item label="Report Date">
                {dayjs(selectedIncident.CBRReportDate).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
            {selectedIncident.CBRIncidentNumber && (
              <Descriptions.Item label="CBR Incident Number">
                {selectedIncident.CBRIncidentNumber}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="Operational Risk Category" span={2}>
              {selectedIncident.OperationalRiskCategory || '-'}
            </Descriptions.Item>
            {selectedIncident.EstimatedDamage_RUB && (
              <Descriptions.Item label="Estimated Damage">
                {selectedIncident.EstimatedDamage_RUB.toLocaleString()} ₽
              </Descriptions.Item>
            )}
            {selectedIncident.ActualDamage_RUB && (
              <Descriptions.Item label="Actual Damage">
                {selectedIncident.ActualDamage_RUB.toLocaleString()} ₽
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* Report to CBR Modal */}
      <Modal
        title="Report Incident to CBR"
        open={reportModalVisible}
        onCancel={() => {
          setReportModalVisible(false)
          setSelectedIncident(null)
          reportForm.resetFields()
        }}
        onOk={() => reportForm.submit()}
        width={600}
        okText="Submit Report"
      >
        {selectedIncident && (
          <>
            <Alert
              message="CBR Reporting"
              description={`You are about to report incident #${selectedIncident.IncidentId} to the Central Bank of Russia. Please provide the CBR incident number and any additional notes.`}
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form form={reportForm} layout="vertical" onFinish={handleSubmitReport}>
              <Form.Item
                name="cbr_incident_number"
                label="CBR Incident Number"
                rules={[{ required: true, message: 'Please enter CBR incident number' }]}
              >
                <Input placeholder="e.g., CBR-2025-001234" />
              </Form.Item>

              <Form.Item name="report_notes" label="Report Notes">
                <TextArea rows={4} placeholder="Additional notes about this report..." />
              </Form.Item>

              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Incident Title">{selectedIncident.Title}</Descriptions.Item>
                <Descriptions.Item label="Severity">
                  {['', 'Low', 'Medium', 'High', 'Critical'][selectedIncident.Severity]}
                </Descriptions.Item>
                <Descriptions.Item label="Detected At">
                  {dayjs(selectedIncident.DetectedAt).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              </Descriptions>
            </Form>
          </>
        )}
      </Modal>
    </div>
  )
}
