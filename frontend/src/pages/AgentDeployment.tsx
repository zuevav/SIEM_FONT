import { useState, useEffect, useCallback } from 'react'
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
  Upload,
  message,
  Tabs,
  Progress,
  Descriptions,
  Typography,
  Tooltip,
  Popconfirm,
  Switch,
  Steps,
  Alert,
  Divider,
  Row,
  Col,
  Statistic,
} from 'antd'
import {
  UploadOutlined,
  CloudUploadOutlined,
  RocketOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  PlusOutlined,
  DesktopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Option } = Select

interface AgentPackage {
  package_id: number
  version: string
  file_name: string
  file_size: number
  file_hash: string
  platform: string
  architecture: string
  description: string
  release_notes: string
  is_active: boolean
  is_latest: boolean
  uploaded_by: string
  uploaded_at: string
  download_url: string
}

interface DeploymentTarget {
  target_id: number
  computer_name: string
  computer_dn: string
  ip_address: string
  status: string
  deployed_at: string
  deployed_version: string
  error_message: string
}

interface Deployment {
  deployment_id: number
  name: string
  description: string
  package_id: number
  package_version: string
  deployment_mode: string
  target_ou: string
  server_url: string
  network_path: string
  enable_protection: boolean
  install_watchdog: boolean
  status: string
  created_by: string
  created_at: string
  activated_at: string
  total_targets: number
  deployed_count: number
  failed_count: number
  targets?: DeploymentTarget[]
}

interface ADComputer {
  name: string
  dn: string
  ip?: string
}

export default function AgentDeployment() {
  const [activeTab, setActiveTab] = useState('packages')
  const [packages, setPackages] = useState<AgentPackage[]>([])
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [deploymentModalOpen, setDeploymentModalOpen] = useState(false)
  const [scriptModalOpen, setScriptModalOpen] = useState(false)
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null)
  const [deploymentScript, setDeploymentScript] = useState('')
  const [adComputers, setAdComputers] = useState<ADComputer[]>([])
  const [selectedComputers, setSelectedComputers] = useState<string[]>([])
  const [uploadForm] = Form.useForm()
  const [deploymentForm] = Form.useForm()
  const [currentStep, setCurrentStep] = useState(0)

  const fetchPackages = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/deployment/packages')
      if (response.ok) {
        const data = await response.json()
        setPackages(data)
      }
    } catch (error) {
      console.error('Error fetching packages:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchDeployments = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/deployment/deployments')
      if (response.ok) {
        const data = await response.json()
        setDeployments(data)
      }
    } catch (error) {
      console.error('Error fetching deployments:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchADComputers = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/ad/computers')
      if (response.ok) {
        const data = await response.json()
        setAdComputers(data.computers || [])
      }
    } catch (error) {
      console.error('Error fetching AD computers:', error)
    }
  }, [])

  useEffect(() => {
    fetchPackages()
    fetchDeployments()
    fetchADComputers()
  }, [fetchPackages, fetchDeployments, fetchADComputers])

  const handleUploadPackage = async (values: any) => {
    const formData = new FormData()
    formData.append('file', values.file.file)
    formData.append('version', values.version)
    formData.append('platform', values.platform || 'windows')
    formData.append('architecture', values.architecture || 'x64')
    formData.append('description', values.description || '')
    formData.append('release_notes', values.release_notes || '')
    formData.append('set_as_latest', values.set_as_latest ? 'true' : 'false')

    try {
      const response = await fetch('/api/v1/deployment/packages/upload', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        message.success('Пакет успешно загружен')
        setUploadModalOpen(false)
        uploadForm.resetFields()
        fetchPackages()
      } else {
        const data = await response.json()
        message.error(data.detail || 'Ошибка загрузки')
      }
    } catch (error) {
      message.error('Ошибка загрузки пакета')
    }
  }

  const handleCreateDeployment = async () => {
    try {
      const values = await deploymentForm.validateFields()

      const deploymentData = {
        name: values.name,
        description: values.description,
        package_id: values.package_id,
        deployment_mode: values.deployment_mode,
        target_ou: values.target_ou,
        server_url: values.server_url,
        network_path: values.network_path,
        enable_protection: values.enable_protection !== false,
        install_watchdog: values.install_watchdog !== false,
        target_computers: selectedComputers.map(name => ({ name })),
      }

      const response = await fetch('/api/v1/deployment/deployments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deploymentData),
      })

      if (response.ok) {
        message.success('Развертывание создано')
        setDeploymentModalOpen(false)
        deploymentForm.resetFields()
        setSelectedComputers([])
        setCurrentStep(0)
        fetchDeployments()
      } else {
        const data = await response.json()
        message.error(data.detail || 'Ошибка создания')
      }
    } catch (error) {
      console.error(error)
    }
  }

  const handleActivateDeployment = async (deploymentId: number) => {
    try {
      const response = await fetch(`/api/v1/deployment/deployments/${deploymentId}/activate`, {
        method: 'POST',
      })

      if (response.ok) {
        const data = await response.json()
        message.success('Развертывание активировано')
        setDeploymentScript(data.script)
        setScriptModalOpen(true)
        fetchDeployments()
      } else {
        const data = await response.json()
        message.error(data.detail || 'Ошибка активации')
      }
    } catch (error) {
      message.error('Ошибка активации развертывания')
    }
  }

  const handlePauseDeployment = async (deploymentId: number) => {
    try {
      const response = await fetch(`/api/v1/deployment/deployments/${deploymentId}/pause`, {
        method: 'POST',
      })

      if (response.ok) {
        message.success('Развертывание приостановлено')
        fetchDeployments()
      }
    } catch (error) {
      message.error('Ошибка')
    }
  }

  const handleDeleteDeployment = async (deploymentId: number) => {
    try {
      const response = await fetch(`/api/v1/deployment/deployments/${deploymentId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        message.success('Развертывание удалено')
        fetchDeployments()
      }
    } catch (error) {
      message.error('Ошибка удаления')
    }
  }

  const handleViewScript = async (deploymentId: number) => {
    try {
      const response = await fetch(`/api/v1/deployment/deployments/${deploymentId}/script`)
      if (response.ok) {
        const data = await response.json()
        setDeploymentScript(data.script)
        setScriptModalOpen(true)
      }
    } catch (error) {
      message.error('Ошибка получения скрипта')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    message.success('Скопировано в буфер обмена')
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
      draft: { color: 'default', icon: <ClockCircleOutlined /> },
      active: { color: 'success', icon: <PlayCircleOutlined /> },
      paused: { color: 'warning', icon: <PauseCircleOutlined /> },
      completed: { color: 'blue', icon: <CheckCircleOutlined /> },
    }
    const config = statusConfig[status] || { color: 'default', icon: null }
    return <Tag color={config.color} icon={config.icon}>{status}</Tag>
  }

  const packagesColumns = [
    {
      title: 'Версия',
      dataIndex: 'version',
      key: 'version',
      render: (version: string, record: AgentPackage) => (
        <Space>
          <Text strong>{version}</Text>
          {record.is_latest && <Tag color="green">Последняя</Tag>}
        </Space>
      ),
    },
    {
      title: 'Платформа',
      key: 'platform',
      render: (_: any, record: AgentPackage) => (
        <Tag>{record.platform} / {record.architecture}</Tag>
      ),
    },
    {
      title: 'Файл',
      dataIndex: 'file_name',
      key: 'file_name',
    },
    {
      title: 'Размер',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => `${(size / 1024 / 1024).toFixed(2)} MB`,
    },
    {
      title: 'Загружен',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (date: string) => date ? new Date(date).toLocaleString('ru') : '-',
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: any, record: AgentPackage) => (
        <Space>
          <Tooltip title="Скачать">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              href={record.download_url}
            />
          </Tooltip>
          <Popconfirm
            title="Удалить пакет?"
            onConfirm={() => {/* handle delete */}}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const deploymentsColumns = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Deployment) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            v{record.package_version} • {record.deployment_mode}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag,
    },
    {
      title: 'Прогресс',
      key: 'progress',
      render: (_: any, record: Deployment) => {
        if (record.total_targets === 0) return <Text type="secondary">-</Text>
        const percent = Math.round((record.deployed_count / record.total_targets) * 100)
        return (
          <Space direction="vertical" size={0} style={{ width: 120 }}>
            <Progress percent={percent} size="small" />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {record.deployed_count}/{record.total_targets} ПК
              {record.failed_count > 0 && (
                <Text type="danger"> ({record.failed_count} ошибок)</Text>
              )}
            </Text>
          </Space>
        )
      },
    },
    {
      title: 'Режим',
      key: 'mode',
      render: (_: any, record: Deployment) => (
        <Space>
          {record.deployment_mode === 'all' ? (
            <Tag color="blue">Все компьютеры</Tag>
          ) : (
            <Tag color="orange">Выбранные ({record.total_targets})</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Защита',
      key: 'protection',
      render: (_: any, record: Deployment) => (
        <Space>
          {record.enable_protection && <Tag color="green">ACL</Tag>}
          {record.install_watchdog && <Tag color="green">Watchdog</Tag>}
        </Space>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: any, record: Deployment) => (
        <Space>
          {record.status === 'draft' && (
            <Tooltip title="Активировать">
              <Button
                type="primary"
                size="small"
                icon={<RocketOutlined />}
                onClick={() => handleActivateDeployment(record.deployment_id)}
              >
                Запустить
              </Button>
            </Tooltip>
          )}
          {record.status === 'active' && (
            <Tooltip title="Приостановить">
              <Button
                size="small"
                icon={<PauseCircleOutlined />}
                onClick={() => handlePauseDeployment(record.deployment_id)}
              />
            </Tooltip>
          )}
          <Tooltip title="Скрипт GPO">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleViewScript(record.deployment_id)}
            />
          </Tooltip>
          <Popconfirm
            title="Удалить развертывание?"
            onConfirm={() => handleDeleteDeployment(record.deployment_id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const deploymentModeValue = Form.useWatch('deployment_mode', deploymentForm)

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <RocketOutlined /> Развертывание агента
        </Title>
        <Text type="secondary">
          Управление пакетами агента и автоматическое развертывание через GPO
        </Text>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Пакетов"
              value={packages.length}
              prefix={<CloudUploadOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Активных развертываний"
              value={deployments.filter(d => d.status === 'active').length}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Развернуто агентов"
              value={deployments.reduce((sum, d) => sum + d.deployed_count, 0)}
              prefix={<DesktopOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Ошибок"
              value={deployments.reduce((sum, d) => sum + d.failed_count, 0)}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: deployments.reduce((sum, d) => sum + d.failed_count, 0) > 0 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabBarExtraContent={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => { fetchPackages(); fetchDeployments(); }}>
                Обновить
              </Button>
              {activeTab === 'packages' && (
                <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadModalOpen(true)}>
                  Загрузить пакет
                </Button>
              )}
              {activeTab === 'deployments' && (
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setDeploymentModalOpen(true)}>
                  Создать развертывание
                </Button>
              )}
            </Space>
          }
          items={[
            {
              key: 'packages',
              label: 'Пакеты агента',
              children: (
                <Table
                  columns={packagesColumns}
                  dataSource={packages}
                  rowKey="package_id"
                  loading={loading}
                  pagination={false}
                />
              ),
            },
            {
              key: 'deployments',
              label: 'Развертывания',
              children: (
                <Table
                  columns={deploymentsColumns}
                  dataSource={deployments}
                  rowKey="deployment_id"
                  loading={loading}
                  pagination={false}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Upload Package Modal */}
      <Modal
        title="Загрузка пакета агента"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        onOk={() => uploadForm.submit()}
        width={600}
      >
        <Form form={uploadForm} layout="vertical" onFinish={handleUploadPackage}>
          <Form.Item
            name="file"
            label="Файл пакета"
            rules={[{ required: true, message: 'Выберите файл' }]}
          >
            <Upload.Dragger
              maxCount={1}
              beforeUpload={() => false}
              accept=".zip,.exe,.msi"
            >
              <p className="ant-upload-drag-icon">
                <CloudUploadOutlined />
              </p>
              <p className="ant-upload-text">Перетащите файл или нажмите для выбора</p>
              <p className="ant-upload-hint">ZIP архив с агентом или установщик</p>
            </Upload.Dragger>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="version"
                label="Версия"
                rules={[{ required: true, message: 'Укажите версию' }]}
              >
                <Input placeholder="1.0.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="platform" label="Платформа" initialValue="windows">
                <Select>
                  <Option value="windows">Windows</Option>
                  <Option value="linux">Linux</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="architecture" label="Архитектура" initialValue="x64">
                <Select>
                  <Option value="x64">x64</Option>
                  <Option value="x86">x86</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Описание">
            <TextArea rows={2} placeholder="Описание версии..." />
          </Form.Item>

          <Form.Item name="release_notes" label="Изменения">
            <TextArea rows={3} placeholder="Что нового в этой версии..." />
          </Form.Item>

          <Form.Item name="set_as_latest" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="Последняя версия" unCheckedChildren="Не последняя" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Deployment Modal */}
      <Modal
        title="Создание развертывания"
        open={deploymentModalOpen}
        onCancel={() => { setDeploymentModalOpen(false); setCurrentStep(0); }}
        onOk={handleCreateDeployment}
        width={800}
        okText="Создать"
      >
        <Steps
          current={currentStep}
          size="small"
          style={{ marginBottom: 24 }}
          items={[
            { title: 'Настройки' },
            { title: 'Целевые ПК' },
            { title: 'Защита' },
          ]}
        />

        <Form form={deploymentForm} layout="vertical">
          {currentStep === 0 && (
            <>
              <Form.Item
                name="name"
                label="Название"
                rules={[{ required: true }]}
              >
                <Input placeholder="Развертывание агента v1.0" />
              </Form.Item>

              <Form.Item name="description" label="Описание">
                <TextArea rows={2} placeholder="Описание развертывания..." />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="package_id"
                    label="Пакет агента"
                    rules={[{ required: true }]}
                  >
                    <Select placeholder="Выберите пакет">
                      {packages.map(p => (
                        <Option key={p.package_id} value={p.package_id}>
                          v{p.version} ({p.platform}/{p.architecture})
                          {p.is_latest && ' - Последняя'}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="server_url"
                    label="URL SIEM сервера"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="https://siem.company.local" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="network_path"
                label="Сетевой путь (NETLOGON)"
                rules={[{ required: true }]}
              >
                <Input placeholder="\\domain.local\NETLOGON\SIEMAgent" />
              </Form.Item>
            </>
          )}

          {currentStep === 1 && (
            <>
              <Form.Item
                name="deployment_mode"
                label="Режим развертывания"
                initialValue="selected"
              >
                <Select>
                  <Option value="all">Все компьютеры домена</Option>
                  <Option value="selected">Выбранные компьютеры</Option>
                  <Option value="ou">По OU (Organizational Unit)</Option>
                </Select>
              </Form.Item>

              {deploymentModeValue === 'ou' && (
                <Form.Item name="target_ou" label="OU путь">
                  <Input placeholder="OU=Computers,DC=domain,DC=local" />
                </Form.Item>
              )}

              {deploymentModeValue === 'selected' && (
                <Form.Item label="Выберите компьютеры">
                  <Select
                    mode="multiple"
                    placeholder="Выберите компьютеры из AD"
                    value={selectedComputers}
                    onChange={setSelectedComputers}
                    style={{ width: '100%' }}
                    optionFilterProp="children"
                    showSearch
                  >
                    {adComputers.map(c => (
                      <Option key={c.name} value={c.name}>
                        {c.name} {c.ip && `(${c.ip})`}
                      </Option>
                    ))}
                  </Select>
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      Выбрано: {selectedComputers.length} компьютеров
                    </Text>
                  </div>
                </Form.Item>
              )}

              {deploymentModeValue === 'all' && (
                <Alert
                  type="warning"
                  message="Внимание"
                  description="Агент будет установлен на ВСЕ компьютеры домена. Рекомендуется сначала протестировать на выбранных компьютерах."
                  showIcon
                />
              )}
            </>
          )}

          {currentStep === 2 && (
            <>
              <Alert
                type="info"
                message="Защита агента"
                description="Защита предотвращает отключение агента пользователями и вредоносным ПО"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                name="enable_protection"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch
                  checkedChildren="Защита файлов и службы"
                  unCheckedChildren="Без защиты"
                />
              </Form.Item>

              <Form.Item
                name="install_watchdog"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch
                  checkedChildren="Watchdog служба"
                  unCheckedChildren="Без Watchdog"
                />
              </Form.Item>

              <Descriptions column={1} size="small" style={{ marginTop: 16 }}>
                <Descriptions.Item label="Защита файлов">
                  ACL только для SYSTEM и Администраторов
                </Descriptions.Item>
                <Descriptions.Item label="Защита службы">
                  SDDL запрет остановки пользователями
                </Descriptions.Item>
                <Descriptions.Item label="Watchdog">
                  Автоматический перезапуск при остановке
                </Descriptions.Item>
              </Descriptions>
            </>
          )}
        </Form>

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          {currentStep > 0 && (
            <Button style={{ marginRight: 8 }} onClick={() => setCurrentStep(currentStep - 1)}>
              Назад
            </Button>
          )}
          {currentStep < 2 && (
            <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
              Далее
            </Button>
          )}
        </div>
      </Modal>

      {/* Script Modal */}
      <Modal
        title="Скрипт развертывания GPO"
        open={scriptModalOpen}
        onCancel={() => setScriptModalOpen(false)}
        width={900}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} onClick={() => copyToClipboard(deploymentScript)}>
            Копировать
          </Button>,
          <Button key="close" onClick={() => setScriptModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
      >
        <Alert
          type="info"
          message="Инструкция"
          description={
            <ol style={{ marginBottom: 0, paddingLeft: 20 }}>
              <li>Скопируйте файлы агента в указанную сетевую папку NETLOGON</li>
              <li>Сохраните этот скрипт как .ps1 файл</li>
              <li>Создайте GPO и добавьте скрипт как Computer Startup Script</li>
              <li>Привяжите GPO к нужным OU</li>
            </ol>
          }
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Input.TextArea
          value={deploymentScript}
          rows={20}
          style={{ fontFamily: 'monospace', fontSize: 12 }}
          readOnly
        />
      </Modal>
    </div>
  )
}
