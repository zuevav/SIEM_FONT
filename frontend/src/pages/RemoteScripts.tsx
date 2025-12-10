import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tooltip,
  Badge,
  Typography,
  Row,
  Col,
  Statistic,
  Tabs,
  Popconfirm,
  Spin,
  Drawer,
  List,
  Progress,
} from 'antd'
import {
  CodeOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  HistoryOutlined,
  DesktopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CopyOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import Editor from '@monaco-editor/react'

const { Text, Title } = Typography
const { TextArea } = Input
const { TabPane } = Tabs

interface RemoteScript {
  ScriptId: number
  ScriptGUID: string
  Name: string
  Description: string
  Category: string
  ScriptType: string
  ScriptContent: string
  Parameters: string | null
  RequiresAdmin: boolean
  Timeout: number
  CreatedByName: string
  CreatedAt: string
  IsActive: boolean
}

interface ScriptExecution {
  ExecutionId: number
  ExecutionGUID: string
  ScriptId: number
  ScriptName: string
  AgentId: string
  ComputerName: string
  ExecutedByName: string
  ExecutedAt: string
  ExecutionParameters: string | null
  Status: string
  StartedAt: string | null
  CompletedAt: string | null
  ExitCode: number | null
  Output: string | null
  ErrorOutput: string | null
  DurationMs: number | null
}

interface Agent {
  AgentId: string
  Hostname: string
  IPAddress: string
  Status: string
}

const scriptCategories = [
  { value: 'network', label: 'Сеть' },
  { value: 'security', label: 'Безопасность' },
  { value: 'maintenance', label: 'Обслуживание' },
  { value: 'diagnostics', label: 'Диагностика' },
  { value: 'configuration', label: 'Настройка' },
  { value: 'other', label: 'Другое' },
]

const scriptTypes = [
  { value: 'powershell', label: 'PowerShell' },
  { value: 'batch', label: 'Batch (CMD)' },
  { value: 'python', label: 'Python' },
]

export default function RemoteScripts() {
  const [scripts, setScripts] = useState<RemoteScript[]>([])
  const [executions, setExecutions] = useState<ScriptExecution[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [executeModalVisible, setExecuteModalVisible] = useState(false)
  const [historyDrawerVisible, setHistoryDrawerVisible] = useState(false)
  const [selectedScript, setSelectedScript] = useState<RemoteScript | null>(null)
  const [selectedExecution, setSelectedExecution] = useState<ScriptExecution | null>(null)
  const [form] = Form.useForm()
  const [executeForm] = Form.useForm()
  const [activeTab, setActiveTab] = useState('scripts')
  const [scriptContent, setScriptContent] = useState('')

  const fetchScripts = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/scripts?page_size=100', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setScripts(data.items || [])
    } catch (error) {
      message.error('Ошибка загрузки скриптов')
    } finally {
      setLoading(false)
    }
  }

  const fetchExecutions = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/scripts/executions?page_size=100', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setExecutions(data.items || [])
    } catch (error) {
      message.error('Ошибка загрузки истории')
    }
  }

  const fetchAgents = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/agents?status=online&page_size=200', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setAgents(data.items || [])
    } catch (error) {
      console.error('Error fetching agents:', error)
    }
  }

  useEffect(() => {
    fetchScripts()
    fetchExecutions()
    fetchAgents()
  }, [])

  const handleCreateScript = async (values: any) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/scripts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: values.name,
          description: values.description,
          category: values.category,
          script_type: values.script_type,
          script_content: scriptContent,
          requires_admin: values.requires_admin,
          timeout: values.timeout || 300,
        }),
      })

      if (response.ok) {
        message.success('Скрипт создан')
        setCreateModalVisible(false)
        form.resetFields()
        setScriptContent('')
        fetchScripts()
      } else {
        throw new Error('Failed to create script')
      }
    } catch (error) {
      message.error('Ошибка создания скрипта')
    }
  }

  const handleUpdateScript = async (values: any) => {
    if (!selectedScript) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/scripts/${selectedScript.ScriptId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: values.name,
          description: values.description,
          category: values.category,
          script_content: scriptContent,
          requires_admin: values.requires_admin,
          timeout: values.timeout,
        }),
      })

      if (response.ok) {
        message.success('Скрипт обновлен')
        setEditModalVisible(false)
        fetchScripts()
      } else {
        throw new Error('Failed to update script')
      }
    } catch (error) {
      message.error('Ошибка обновления скрипта')
    }
  }

  const handleDeleteScript = async (scriptId: number) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/ad/scripts/${scriptId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        message.success('Скрипт удален')
        fetchScripts()
      } else {
        throw new Error('Failed to delete script')
      }
    } catch (error) {
      message.error('Ошибка удаления скрипта')
    }
  }

  const handleExecuteScript = async (values: any) => {
    if (!selectedScript) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/ad/scripts/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          script_id: selectedScript.ScriptId,
          agent_ids: values.agent_ids,
          parameters: values.parameters ? JSON.parse(values.parameters) : null,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        message.success(`Скрипт запущен на ${data.executions.length} агентах`)
        setExecuteModalVisible(false)
        executeForm.resetFields()
        fetchExecutions()
      } else {
        throw new Error('Failed to execute script')
      }
    } catch (error) {
      message.error('Ошибка запуска скрипта')
    }
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined /> },
      sent: { color: 'processing', icon: <SyncOutlined spin /> },
      running: { color: 'processing', icon: <SyncOutlined spin /> },
      completed: { color: 'success', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', icon: <CloseCircleOutlined /> },
      timeout: { color: 'warning', icon: <ClockCircleOutlined /> },
    }

    const config = statusConfig[status] || { color: 'default', icon: null }

    return (
      <Tag color={config.color} icon={config.icon}>
        {status.toUpperCase()}
      </Tag>
    )
  }

  const scriptColumns: ColumnsType<RemoteScript> = [
    {
      title: 'Название',
      dataIndex: 'Name',
      key: 'Name',
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.Description?.substring(0, 50)}...
          </Text>
        </Space>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'ScriptType',
      key: 'ScriptType',
      width: 120,
      render: (type) => {
        const colors: Record<string, string> = {
          powershell: 'blue',
          batch: 'orange',
          python: 'green',
        }
        return <Tag color={colors[type] || 'default'}>{type.toUpperCase()}</Tag>
      },
    },
    {
      title: 'Категория',
      dataIndex: 'Category',
      key: 'Category',
      width: 120,
      render: (cat) => cat || '-',
    },
    {
      title: 'Требует Admin',
      dataIndex: 'RequiresAdmin',
      key: 'RequiresAdmin',
      width: 100,
      render: (val) => (val ? <Tag color="red">Да</Tag> : <Tag color="green">Нет</Tag>),
    },
    {
      title: 'Timeout',
      dataIndex: 'Timeout',
      key: 'Timeout',
      width: 100,
      render: (val) => `${val} сек`,
    },
    {
      title: 'Создан',
      dataIndex: 'CreatedAt',
      key: 'CreatedAt',
      width: 150,
      render: (date, record) => (
        <Space direction="vertical" size={0}>
          <Text>{new Date(date).toLocaleDateString('ru-RU')}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.CreatedByName}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title="Выполнить">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              size="small"
              onClick={() => {
                setSelectedScript(record)
                setExecuteModalVisible(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button
              icon={<EditOutlined />}
              size="small"
              onClick={() => {
                setSelectedScript(record)
                setScriptContent(record.ScriptContent)
                form.setFieldsValue({
                  name: record.Name,
                  description: record.Description,
                  category: record.Category,
                  script_type: record.ScriptType,
                  requires_admin: record.RequiresAdmin,
                  timeout: record.Timeout,
                })
                setEditModalVisible(true)
              }}
            />
          </Tooltip>
          <Tooltip title="История">
            <Button
              icon={<HistoryOutlined />}
              size="small"
              onClick={() => {
                setSelectedScript(record)
                setHistoryDrawerVisible(true)
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Удалить скрипт?"
            onConfirm={() => handleDeleteScript(record.ScriptId)}
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const executionColumns: ColumnsType<ScriptExecution> = [
    {
      title: 'Скрипт',
      dataIndex: 'ScriptName',
      key: 'ScriptName',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Компьютер',
      dataIndex: 'ComputerName',
      key: 'ComputerName',
      render: (text) => (
        <Space>
          <DesktopOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Запустил',
      dataIndex: 'ExecutedByName',
      key: 'ExecutedByName',
    },
    {
      title: 'Дата',
      dataIndex: 'ExecutedAt',
      key: 'ExecutedAt',
      render: (date) => new Date(date).toLocaleString('ru-RU'),
    },
    {
      title: 'Статус',
      dataIndex: 'Status',
      key: 'Status',
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Код выхода',
      dataIndex: 'ExitCode',
      key: 'ExitCode',
      render: (code) =>
        code !== null ? (
          <Tag color={code === 0 ? 'success' : 'error'}>{code}</Tag>
        ) : (
          '-'
        ),
    },
    {
      title: 'Длительность',
      dataIndex: 'DurationMs',
      key: 'DurationMs',
      render: (ms) => (ms ? `${(ms / 1000).toFixed(2)} сек` : '-'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Button
          icon={<EyeOutlined />}
          size="small"
          onClick={() => setSelectedExecution(record)}
        >
          Вывод
        </Button>
      ),
    },
  ]

  const scriptHistoryExecutions = executions.filter(
    (e) => selectedScript && e.ScriptId === selectedScript.ScriptId
  )

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Всего скриптов"
              value={scripts.length}
              prefix={<CodeOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Выполнений сегодня"
              value={
                executions.filter((e) => {
                  const today = new Date()
                  const execDate = new Date(e.ExecutedAt)
                  return execDate.toDateString() === today.toDateString()
                }).length
              }
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Успешных"
              value={executions.filter((e) => e.Status === 'completed').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Неудачных"
              value={executions.filter((e) => e.Status === 'failed').length}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <CodeOutlined />
            <span>Удаленные скрипты</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => { fetchScripts(); fetchExecutions(); }}>
              Обновить
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                form.resetFields()
                setScriptContent('')
                setCreateModalVisible(true)
              }}
            >
              Новый скрипт
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="Скрипты" key="scripts">
            <Table
              columns={scriptColumns}
              dataSource={scripts}
              rowKey="ScriptId"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
          <TabPane tab="История выполнения" key="history">
            <Table
              columns={executionColumns}
              dataSource={executions}
              rowKey="ExecutionId"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Create Script Modal */}
      <Modal
        title="Создать скрипт"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={900}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateScript}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Название"
                rules={[{ required: true, message: 'Введите название' }]}
              >
                <Input placeholder="Название скрипта" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="script_type"
                label="Тип"
                rules={[{ required: true }]}
                initialValue="powershell"
              >
                <Select options={scriptTypes} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="category" label="Категория">
                <Select options={scriptCategories} allowClear />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Описание">
            <TextArea rows={2} placeholder="Описание скрипта" />
          </Form.Item>

          <Form.Item label="Код скрипта" required>
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
              <Editor
                height="300px"
                defaultLanguage="powershell"
                value={scriptContent}
                onChange={(value) => setScriptContent(value || '')}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                }}
              />
            </div>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="requires_admin"
                label="Требует Admin"
                initialValue={true}
              >
                <Select>
                  <Select.Option value={true}>Да</Select.Option>
                  <Select.Option value={false}>Нет</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="timeout"
                label="Timeout (сек)"
                initialValue={300}
              >
                <Input type="number" min={30} max={3600} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Создать
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Script Modal */}
      <Modal
        title="Редактировать скрипт"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={900}
      >
        <Form form={form} layout="vertical" onFinish={handleUpdateScript}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Название"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="script_type" label="Тип">
                <Select options={scriptTypes} disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="category" label="Категория">
                <Select options={scriptCategories} allowClear />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Описание">
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item label="Код скрипта" required>
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
              <Editor
                height="300px"
                defaultLanguage="powershell"
                value={scriptContent}
                onChange={(value) => setScriptContent(value || '')}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                }}
              />
            </div>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="requires_admin" label="Требует Admin">
                <Select>
                  <Select.Option value={true}>Да</Select.Option>
                  <Select.Option value={false}>Нет</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="timeout" label="Timeout (сек)">
                <Input type="number" min={30} max={3600} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Сохранить
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Execute Script Modal */}
      <Modal
        title={`Выполнить: ${selectedScript?.Name}`}
        open={executeModalVisible}
        onCancel={() => setExecuteModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={executeForm} layout="vertical" onFinish={handleExecuteScript}>
          <Form.Item
            name="agent_ids"
            label="Выберите компьютеры"
            rules={[{ required: true, message: 'Выберите хотя бы один компьютер' }]}
          >
            <Select
              mode="multiple"
              placeholder="Выберите компьютеры для выполнения"
              optionFilterProp="children"
              showSearch
            >
              {agents
                .filter((a) => a.Status === 'online')
                .map((agent) => (
                  <Select.Option key={agent.AgentId} value={agent.AgentId}>
                    {agent.Hostname} ({agent.IPAddress})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="parameters"
            label="Параметры (JSON)"
            extra={'Например: {"param1": "value1"}'}
          >
            <TextArea rows={3} placeholder={'{"param1": "value1"}'} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />}>
                Выполнить
              </Button>
              <Button onClick={() => setExecuteModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Script History Drawer */}
      <Drawer
        title={`История: ${selectedScript?.Name}`}
        open={historyDrawerVisible}
        onClose={() => setHistoryDrawerVisible(false)}
        width={600}
      >
        <List
          dataSource={scriptHistoryExecutions}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  size="small"
                  onClick={() => setSelectedExecution(item)}
                >
                  Вывод
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <DesktopOutlined />
                    {item.ComputerName}
                    {getStatusTag(item.Status)}
                  </Space>
                }
                description={
                  <>
                    <div>{new Date(item.ExecutedAt).toLocaleString('ru-RU')}</div>
                    <div>Запустил: {item.ExecutedByName}</div>
                  </>
                }
              />
            </List.Item>
          )}
        />
      </Drawer>

      {/* Execution Output Modal */}
      <Modal
        title={`Вывод: ${selectedExecution?.ScriptName}`}
        open={!!selectedExecution}
        onCancel={() => setSelectedExecution(null)}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} onClick={() => {
            navigator.clipboard.writeText(selectedExecution?.Output || '')
            message.success('Скопировано')
          }}>
            Копировать
          </Button>,
          <Button key="close" onClick={() => setSelectedExecution(null)}>
            Закрыть
          </Button>,
        ]}
        width={800}
      >
        {selectedExecution && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Text type="secondary">Компьютер:</Text>
                <div><Text strong>{selectedExecution.ComputerName}</Text></div>
              </Col>
              <Col span={8}>
                <Text type="secondary">Статус:</Text>
                <div>{getStatusTag(selectedExecution.Status)}</div>
              </Col>
              <Col span={8}>
                <Text type="secondary">Код выхода:</Text>
                <div>
                  <Tag color={selectedExecution.ExitCode === 0 ? 'success' : 'error'}>
                    {selectedExecution.ExitCode ?? '-'}
                  </Tag>
                </div>
              </Col>
            </Row>

            {selectedExecution.Output && (
              <>
                <Text strong>Стандартный вывод:</Text>
                <pre style={{
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  padding: 12,
                  borderRadius: 6,
                  maxHeight: 300,
                  overflow: 'auto',
                  fontSize: 12,
                }}>
                  {selectedExecution.Output}
                </pre>
              </>
            )}

            {selectedExecution.ErrorOutput && (
              <>
                <Text strong type="danger">Ошибки:</Text>
                <pre style={{
                  background: '#2d1f1f',
                  color: '#ff6b6b',
                  padding: 12,
                  borderRadius: 6,
                  maxHeight: 200,
                  overflow: 'auto',
                  fontSize: 12,
                }}>
                  {selectedExecution.ErrorOutput}
                </pre>
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  )
}
