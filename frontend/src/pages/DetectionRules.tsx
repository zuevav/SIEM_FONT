import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Switch,
  Input,
  Select,
  Popconfirm,
  message,
  Modal,
  Form,
  InputNumber,
  Divider,
  Descriptions,
  Tooltip,
  Typography,
  Badge,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { DetectionRule, DetectionRuleCreate, DetectionRuleUpdate } from '@/types'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

// Severity colors and labels
const SEVERITY_CONFIG = {
  1: { label: 'Low', color: 'blue', icon: <InfoCircleOutlined /> },
  2: { label: 'Medium', color: 'gold', icon: <WarningOutlined /> },
  3: { label: 'High', color: 'orange', icon: <ExclamationCircleOutlined /> },
  4: { label: 'Critical', color: 'red', icon: <ExclamationCircleOutlined /> },
}

// Rule types
const RULE_TYPES = [
  { value: 'simple', label: 'Simple' },
  { value: 'threshold', label: 'Threshold' },
  { value: 'correlation', label: 'Correlation' },
  { value: 'anomaly', label: 'Anomaly' },
]

export default function DetectionRules() {
  const [rules, setRules] = useState<DetectionRule[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Filters
  const [searchText, setSearchText] = useState('')
  const [enabledFilter, setEnabledFilter] = useState<'all' | 'enabled' | 'disabled'>('all')
  const [ruleTypeFilter, setRuleTypeFilter] = useState<string | undefined>(undefined)

  // Modals
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [selectedRule, setSelectedRule] = useState<DetectionRule | null>(null)

  // Forms
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  // Load rules
  const loadRules = async () => {
    setLoading(true)
    try {
      const response = await apiService.getDetectionRules({
        enabled_only: enabledFilter === 'enabled' ? true : undefined,
        rule_type: ruleTypeFilter,
        search: searchText || undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      })
      setRules(response.rules)
      setTotal(response.total)
    } catch (error) {
      message.error('Failed to load detection rules')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRules()
  }, [page, pageSize, enabledFilter, ruleTypeFilter])

  // Handle search
  const handleSearch = () => {
    setPage(1)
    loadRules()
  }

  // Handle toggle enable/disable
  const handleToggleEnabled = async (ruleId: number, enabled: boolean) => {
    try {
      await apiService.toggleDetectionRule(ruleId, enabled)
      message.success(`Rule ${enabled ? 'enabled' : 'disabled'} successfully`)
      loadRules()
    } catch (error) {
      message.error('Failed to update rule')
      console.error(error)
    }
  }

  // Handle delete
  const handleDelete = async (ruleId: number) => {
    try {
      await apiService.deleteDetectionRule(ruleId)
      message.success('Rule deleted successfully')
      loadRules()
    } catch (error) {
      message.error('Failed to delete rule')
      console.error(error)
    }
  }

  // Handle view details
  const handleView = async (rule: DetectionRule) => {
    setSelectedRule(rule)
    setViewModalVisible(true)
  }

  // Handle create
  const handleCreate = async (values: any) => {
    try {
      const data: DetectionRuleCreate = {
        rule_name: values.rule_name,
        description: values.description,
        is_enabled: values.is_enabled ?? true,
        severity: values.severity,
        priority: values.priority,
        rule_type: values.rule_type,
        rule_logic: values.rule_logic ? JSON.parse(values.rule_logic) : {},
        time_window_minutes: values.time_window_minutes,
        threshold_count: values.threshold_count,
        mitre_attack_tactic: values.mitre_attack_tactic,
        mitre_attack_technique: values.mitre_attack_technique,
        auto_escalate: values.auto_escalate ?? false,
      }
      await apiService.createDetectionRule(data)
      message.success('Rule created successfully')
      setCreateModalVisible(false)
      createForm.resetFields()
      loadRules()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to create rule')
      console.error(error)
    }
  }

  // Handle edit
  const handleEdit = (rule: DetectionRule) => {
    setSelectedRule(rule)
    editForm.setFieldsValue({
      rule_name: rule.RuleName,
      description: rule.Description,
      is_enabled: rule.IsEnabled,
      severity: rule.Severity,
      priority: rule.Priority,
      rule_type: rule.RuleType,
      rule_logic: JSON.stringify(rule.RuleLogic, null, 2),
      time_window_minutes: rule.TimeWindowMinutes,
      threshold_count: rule.ThresholdCount,
      mitre_attack_tactic: rule.MitreAttackTactic,
      mitre_attack_technique: rule.MitreAttackTechnique,
      auto_escalate: rule.AutoEscalate,
    })
    setEditModalVisible(true)
  }

  // Handle update
  const handleUpdate = async (values: any) => {
    if (!selectedRule) return

    try {
      const data: DetectionRuleUpdate = {
        rule_name: values.rule_name,
        description: values.description,
        is_enabled: values.is_enabled,
        severity: values.severity,
        priority: values.priority,
        rule_type: values.rule_type,
        rule_logic: values.rule_logic ? JSON.parse(values.rule_logic) : undefined,
        time_window_minutes: values.time_window_minutes,
        threshold_count: values.threshold_count,
        mitre_attack_tactic: values.mitre_attack_tactic,
        mitre_attack_technique: values.mitre_attack_technique,
        auto_escalate: values.auto_escalate,
      }
      await apiService.updateDetectionRule(selectedRule.RuleId, data)
      message.success('Rule updated successfully')
      setEditModalVisible(false)
      setSelectedRule(null)
      editForm.resetFields()
      loadRules()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to update rule')
      console.error(error)
    }
  }

  // Table columns
  const columns: ColumnsType<DetectionRule> = [
    {
      title: 'Status',
      dataIndex: 'IsEnabled',
      key: 'IsEnabled',
      width: 80,
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleEnabled(record.RuleId, checked)}
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<ExclamationCircleOutlined />}
        />
      ),
    },
    {
      title: 'Rule Name',
      dataIndex: 'RuleName',
      key: 'RuleName',
      width: 300,
      ellipsis: true,
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.Description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.Description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'RuleType',
      key: 'RuleType',
      width: 100,
      render: (type: string) => (
        <Tag color="blue">{type}</Tag>
      ),
    },
    {
      title: 'Severity',
      dataIndex: 'Severity',
      key: 'Severity',
      width: 120,
      render: (severity: number) => {
        const config = SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG]
        return (
          <Tag color={config?.color || 'default'} icon={config?.icon}>
            {config?.label || severity}
          </Tag>
        )
      },
    },
    {
      title: 'Priority',
      dataIndex: 'Priority',
      key: 'Priority',
      width: 80,
      render: (priority: number) => (
        <Badge count={priority} showZero color={priority >= 4 ? 'red' : priority >= 3 ? 'orange' : 'blue'} />
      ),
    },
    {
      title: 'MITRE ATT&CK',
      key: 'mitre',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.MitreAttackTactic && (
            <Tag color="purple" style={{ fontSize: 11 }}>
              {record.MitreAttackTactic}
            </Tag>
          )}
          {record.MitreAttackTechnique && (
            <Tag color="cyan" style={{ fontSize: 11 }}>
              {record.MitreAttackTechnique}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Triggers',
      dataIndex: 'TriggerCount',
      key: 'TriggerCount',
      width: 80,
      render: (count?: number) => count || 0,
    },
    {
      title: 'Last Triggered',
      dataIndex: 'LastTriggered',
      key: 'LastTriggered',
      width: 150,
      render: (date?: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleView(record)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete rule?"
            description="Are you sure you want to delete this detection rule?"
            onConfirm={() => handleDelete(record.RuleId)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              Detection Rules
            </Title>
            <Badge count={total} showZero color="blue" />
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadRules}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
              Create Rule
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            placeholder="Search rules..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 300 }}
            allowClear
          />
          <Select
            placeholder="Status"
            value={enabledFilter}
            onChange={setEnabledFilter}
            style={{ width: 120 }}
          >
            <Option value="all">All</Option>
            <Option value="enabled">Enabled</Option>
            <Option value="disabled">Disabled</Option>
          </Select>
          <Select
            placeholder="Rule Type"
            value={ruleTypeFilter}
            onChange={setRuleTypeFilter}
            style={{ width: 150 }}
            allowClear
          >
            {RULE_TYPES.map((type) => (
              <Option key={type.value} value={type.value}>
                {type.label}
              </Option>
            ))}
          </Select>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            Search
          </Button>
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="RuleId"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} rules`,
            onChange: (page, pageSize) => {
              setPage(page)
              setPageSize(pageSize)
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* View Details Modal */}
      <Modal
        title="Detection Rule Details"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false)
          setSelectedRule(null)
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedRule && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Rule ID">{selectedRule.RuleId}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedRule.IsEnabled ? 'green' : 'red'}>
                {selectedRule.IsEnabled ? 'Enabled' : 'Disabled'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Rule Name" span={2}>
              {selectedRule.RuleName}
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {selectedRule.Description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Rule Type">
              <Tag color="blue">{selectedRule.RuleType}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Severity">
              {SEVERITY_CONFIG[selectedRule.Severity as keyof typeof SEVERITY_CONFIG]?.label}
            </Descriptions.Item>
            <Descriptions.Item label="Priority">{selectedRule.Priority}</Descriptions.Item>
            <Descriptions.Item label="Auto Escalate">
              {selectedRule.AutoEscalate ? 'Yes' : 'No'}
            </Descriptions.Item>
            <Descriptions.Item label="MITRE ATT&CK Tactic" span={2}>
              {selectedRule.MitreAttackTactic || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="MITRE ATT&CK Technique" span={2}>
              {selectedRule.MitreAttackTechnique || '-'}
            </Descriptions.Item>
            {selectedRule.TimeWindowMinutes && (
              <Descriptions.Item label="Time Window">
                {selectedRule.TimeWindowMinutes} minutes
              </Descriptions.Item>
            )}
            {selectedRule.ThresholdCount && (
              <Descriptions.Item label="Threshold Count">
                {selectedRule.ThresholdCount}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="Trigger Count">{selectedRule.TriggerCount || 0}</Descriptions.Item>
            <Descriptions.Item label="Last Triggered">
              {selectedRule.LastTriggered ? dayjs(selectedRule.LastTriggered).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Created At" span={2}>
              {dayjs(selectedRule.CreatedAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Rule Logic" span={2}>
              <pre style={{ maxHeight: 300, overflow: 'auto', background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {JSON.stringify(selectedRule.RuleLogic, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Create Modal */}
      <Modal
        title="Create Detection Rule"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        onOk={() => createForm.submit()}
        width={800}
        okText="Create"
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            is_enabled: true,
            severity: 2,
            priority: 3,
            rule_type: 'simple',
            auto_escalate: false,
          }}
        >
          <Form.Item
            name="rule_name"
            label="Rule Name"
            rules={[{ required: true, message: 'Please enter rule name' }]}
          >
            <Input placeholder="e.g., Brute Force Detection" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Describe what this rule detects" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="rule_type" label="Rule Type" rules={[{ required: true }]}>
              <Select style={{ width: 150 }}>
                {RULE_TYPES.map((type) => (
                  <Option key={type.value} value={type.value}>
                    {type.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="severity" label="Severity" rules={[{ required: true }]}>
              <Select style={{ width: 120 }}>
                <Option value={1}>Low</Option>
                <Option value={2}>Medium</Option>
                <Option value={3}>High</Option>
                <Option value={4}>Critical</Option>
              </Select>
            </Form.Item>

            <Form.Item name="priority" label="Priority" rules={[{ required: true }]}>
              <InputNumber min={1} max={5} style={{ width: 100 }} />
            </Form.Item>
          </Space>

          <Divider />

          <Form.Item
            name="rule_logic"
            label="Rule Logic (JSON)"
            rules={[
              { required: true, message: 'Please enter rule logic' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve()
                  try {
                    JSON.parse(value)
                    return Promise.resolve()
                  } catch (e) {
                    return Promise.reject(new Error('Invalid JSON'))
                  }
                },
              },
            ]}
          >
            <TextArea
              rows={6}
              placeholder='{"provider": "Windows Security", "event_code": 4625}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="time_window_minutes" label="Time Window (minutes)">
              <InputNumber min={1} max={1440} style={{ width: 150 }} />
            </Form.Item>

            <Form.Item name="threshold_count" label="Threshold Count">
              <InputNumber min={1} max={1000} style={{ width: 150 }} />
            </Form.Item>
          </Space>

          <Form.Item name="mitre_attack_tactic" label="MITRE ATT&CK Tactic">
            <Input placeholder="e.g., Initial Access" />
          </Form.Item>

          <Form.Item name="mitre_attack_technique" label="MITRE ATT&CK Technique">
            <Input placeholder="e.g., T1110" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="is_enabled" label="Enabled" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item name="auto_escalate" label="Auto Escalate" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="Edit Detection Rule"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          setSelectedRule(null)
          editForm.resetFields()
        }}
        onOk={() => editForm.submit()}
        width={800}
        okText="Update"
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="rule_name"
            label="Rule Name"
            rules={[{ required: true, message: 'Please enter rule name' }]}
          >
            <Input placeholder="e.g., Brute Force Detection" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Describe what this rule detects" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="rule_type" label="Rule Type" rules={[{ required: true }]}>
              <Select style={{ width: 150 }}>
                {RULE_TYPES.map((type) => (
                  <Option key={type.value} value={type.value}>
                    {type.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="severity" label="Severity" rules={[{ required: true }]}>
              <Select style={{ width: 120 }}>
                <Option value={1}>Low</Option>
                <Option value={2}>Medium</Option>
                <Option value={3}>High</Option>
                <Option value={4}>Critical</Option>
              </Select>
            </Form.Item>

            <Form.Item name="priority" label="Priority" rules={[{ required: true }]}>
              <InputNumber min={1} max={5} style={{ width: 100 }} />
            </Form.Item>
          </Space>

          <Divider />

          <Form.Item
            name="rule_logic"
            label="Rule Logic (JSON)"
            rules={[
              { required: true, message: 'Please enter rule logic' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve()
                  try {
                    JSON.parse(value)
                    return Promise.resolve()
                  } catch (e) {
                    return Promise.reject(new Error('Invalid JSON'))
                  }
                },
              },
            ]}
          >
            <TextArea
              rows={6}
              placeholder='{"provider": "Windows Security", "event_code": 4625}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="time_window_minutes" label="Time Window (minutes)">
              <InputNumber min={1} max={1440} style={{ width: 150 }} />
            </Form.Item>

            <Form.Item name="threshold_count" label="Threshold Count">
              <InputNumber min={1} max={1000} style={{ width: 150 }} />
            </Form.Item>
          </Space>

          <Form.Item name="mitre_attack_tactic" label="MITRE ATT&CK Tactic">
            <Input placeholder="e.g., Initial Access" />
          </Form.Item>

          <Form.Item name="mitre_attack_technique" label="MITRE ATT&CK Technique">
            <Input placeholder="e.g., T1110" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="is_enabled" label="Enabled" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item name="auto_escalate" label="Auto Escalate" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  )
}
