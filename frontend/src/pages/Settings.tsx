/**
 * Settings Page
 * System configuration: FreeScout, Updates, AI, General
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  Tabs,
  Form,
  Input,
  Switch,
  Button,
  Space,
  message,
  Alert,
  Descriptions,
  Tag,
  Modal,
  Progress,
  Divider,
  Select,
  InputNumber,
} from 'antd'
import {
  SettingOutlined,
  SaveOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  RocketOutlined,
  ApiOutlined,
  BulbOutlined,
  GlobalOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons'
import apiService from '@/services/api'

const { TabPane } = Tabs
const { TextArea } = Input
const { Option } = Select

interface Settings {
  freescout_enabled: boolean
  freescout_url: string
  freescout_api_key: string
  freescout_mailbox_id: number
  freescout_auto_create_on_alert: boolean
  freescout_auto_create_severity_min: number
  freescout_sync_interval_seconds: number

  ai_provider: string
  deepseek_api_key?: string
  yandex_gpt_api_key?: string
  yandex_gpt_folder_id?: string

  smtp_enabled: boolean
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_password: string
  smtp_from_email: string
  smtp_from_name: string
  smtp_use_tls: boolean
  email_alert_recipients: string
  email_alert_min_severity: number

  threat_intel_enabled: boolean
  virustotal_api_key?: string
  abuseipdb_api_key?: string
}

interface SystemInfo {
  version: string
  git_branch: string
  git_commit: string
  docker_compose_version: string
  last_update: string
  update_available: boolean
}

export default function Settings() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [updateModalVisible, setUpdateModalVisible] = useState(false)
  const [updateProgress, setUpdateProgress] = useState(0)
  const [updateLogs, setUpdateLogs] = useState<string[]>([])

  useEffect(() => {
    loadSettings()
    loadSystemInfo()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiService.getSettings()
      setSettings(data)
      form.setFieldsValue(data)
    } catch (error) {
      message.error('Не удалось загрузить настройки')
    }
  }

  const loadSystemInfo = async () => {
    try {
      const data = await apiService.getSystemInfo()
      setSystemInfo(data)
    } catch (error) {
      console.error('Failed to load system info:', error)
    }
  }

  const handleSave = async (values: any) => {
    setLoading(true)
    try {
      await apiService.updateSettings(values)
      message.success('Настройки сохранены')
      loadSettings()
    } catch (error) {
      message.error('Ошибка сохранения настроек')
    } finally {
      setLoading(false)
    }
  }

  const handleTestFreeScout = async () => {
    setTestingConnection(true)
    try {
      const values = form.getFieldsValue(['freescout_url', 'freescout_api_key'])
      const result = await apiService.testFreeScoutConnection(
        values.freescout_url,
        values.freescout_api_key
      )

      if (result.success) {
        message.success(`Подключение успешно! Mailbox: ${result.mailbox_name}`)
      } else {
        message.error(`Ошибка подключения: ${result.error}`)
      }
    } catch (error) {
      message.error('Не удалось подключиться к FreeScout')
    } finally {
      setTestingConnection(false)
    }
  }

  const handleCheckUpdates = async () => {
    try {
      const result = await apiService.checkSystemUpdates()

      if (result.update_available) {
        Modal.confirm({
          title: 'Доступно обновление',
          icon: <ExclamationCircleOutlined />,
          content: (
            <div>
              <p>Текущая версия: <Tag>{result.current_version}</Tag></p>
              <p>Новая версия: <Tag color="green">{result.latest_version}</Tag></p>
              <p>Изменения:</p>
              <ul>
                {result.changelog?.slice(0, 5).map((change: string, idx: number) => (
                  <li key={idx}>{change}</li>
                ))}
              </ul>
              <p>Обновить систему сейчас?</p>
            </div>
          ),
          onOk: () => handleSystemUpdate(),
        })
      } else {
        message.success('Система уже обновлена до последней версии')
      }
    } catch (error) {
      message.error('Ошибка проверки обновлений')
    }
  }

  const handleSystemUpdate = async () => {
    setUpdateModalVisible(true)
    setUpdateProgress(0)
    setUpdateLogs([])

    try {
      // Подключаемся к WebSocket для получения логов обновления
      const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/system/update/stream`)

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.type === 'progress') {
          setUpdateProgress(data.progress)
          setUpdateLogs((prev) => [...prev, data.message])
        } else if (data.type === 'complete') {
          setUpdateProgress(100)
          setUpdateLogs((prev) => [...prev, '✅ Обновление завершено успешно!'])
          message.success('Обновление завершено! Перезагрузка через 5 секунд...')
          setTimeout(() => {
            window.location.reload()
          }, 5000)
        } else if (data.type === 'error') {
          setUpdateLogs((prev) => [...prev, `❌ Ошибка: ${data.message}`])
          message.error('Ошибка обновления')
        }
      }

      // Запускаем обновление
      await apiService.startSystemUpdate()

    } catch (error) {
      message.error('Не удалось запустить обновление')
      setUpdateModalVisible(false)
    }
  }

  const handleTestEmail = async () => {
    try {
      const values = form.getFieldsValue([
        'smtp_host',
        'smtp_port',
        'smtp_username',
        'smtp_password',
        'smtp_from_email',
        'smtp_use_tls',
      ])

      await apiService.testEmailSettings(values)
      message.success('Тестовое письмо отправлено! Проверьте почту.')
    } catch (error) {
      message.error('Ошибка отправки тестового письма')
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>Настройки системы</span>
          </Space>
        }
      >
        <Tabs defaultActiveKey="freescout">
          {/* FreeScout Integration */}
          <TabPane
            tab={
              <span>
                <ApiOutlined />
                FreeScout Integration
              </span>
            }
            key="freescout"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="FreeScout Ticketing Integration"
                description="Автоматическое создание тикетов из алертов и инцидентов с двусторонней синхронизацией статусов."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item
                name="freescout_enabled"
                label="Включить FreeScout интеграцию"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                name="freescout_url"
                label="FreeScout URL"
                rules={[
                  { required: true, message: 'Введите URL FreeScout' },
                  { type: 'url', message: 'Введите корректный URL' },
                ]}
              >
                <Input
                  placeholder="https://helpdesk.example.com"
                  prefix={<GlobalOutlined />}
                />
              </Form.Item>

              <Form.Item
                name="freescout_api_key"
                label="API Key"
                rules={[{ required: true, message: 'Введите API ключ' }]}
                extra="Получите API ключ в FreeScout: Admin → API & Webhooks → Generate Key"
              >
                <Input.Password placeholder="API ключ из FreeScout" />
              </Form.Item>

              <Form.Item
                name="freescout_mailbox_id"
                label="Mailbox ID"
                rules={[{ required: true, message: 'Введите Mailbox ID' }]}
                extra="ID почтового ящика для создания тикетов (обычно 1)"
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>

              <Divider>Автоматическое создание тикетов</Divider>

              <Form.Item
                name="freescout_auto_create_on_alert"
                label="Автоматически создавать тикеты из алертов"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                name="freescout_auto_create_severity_min"
                label="Минимальный уровень severity для авто-создания"
                extra="0=Info, 1=Low, 2=Medium, 3=High, 4=Critical"
              >
                <Select>
                  <Option value={0}>Info (0)</Option>
                  <Option value={1}>Low (1)</Option>
                  <Option value={2}>Medium (2)</Option>
                  <Option value={3}>High (3)</Option>
                  <Option value={4}>Critical (4)</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="freescout_sync_interval_seconds"
                label="Интервал синхронизации (секунды)"
                extra="Как часто проверять обновления статусов тикетов"
              >
                <InputNumber min={30} max={3600} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    icon={<SaveOutlined />}
                  >
                    Сохранить
                  </Button>
                  <Button
                    onClick={handleTestFreeScout}
                    loading={testingConnection}
                    icon={<CheckCircleOutlined />}
                  >
                    Тест подключения
                  </Button>
                </Space>
              </Form.Item>

              <Alert
                message="Webhook Configuration"
                description={
                  <div>
                    <p>После сохранения настроек, настройте Webhook в FreeScout:</p>
                    <ol>
                      <li>Откройте: FreeScout → Admin → API & Webhooks → Webhooks</li>
                      <li>
                        URL: <code>{window.location.origin}/api/v1/integrations/freescout/webhook</code>
                      </li>
                      <li>Secret Key: используйте FREESCOUT_WEBHOOK_SECRET из .env</li>
                      <li>
                        Events: conversation.created, conversation.updated, conversation.status_changed,
                        conversation.note_added
                      </li>
                    </ol>
                  </div>
                }
                type="warning"
                showIcon
              />
            </Form>
          </TabPane>

          {/* System Updates */}
          <TabPane
            tab={
              <span>
                <RocketOutlined />
                Обновление системы
              </span>
            }
            key="updates"
          >
            {systemInfo && (
              <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
                <Descriptions.Item label="Версия">{systemInfo.version}</Descriptions.Item>
                <Descriptions.Item label="Git Branch">{systemInfo.git_branch}</Descriptions.Item>
                <Descriptions.Item label="Git Commit">
                  <code>{systemInfo.git_commit?.substring(0, 8)}</code>
                </Descriptions.Item>
                <Descriptions.Item label="Docker Compose">
                  {systemInfo.docker_compose_version}
                </Descriptions.Item>
                <Descriptions.Item label="Последнее обновление">
                  {systemInfo.last_update || 'Никогда'}
                </Descriptions.Item>
                <Descriptions.Item label="Статус">
                  {systemInfo.update_available ? (
                    <Tag color="orange">Доступно обновление</Tag>
                  ) : (
                    <Tag color="green">Актуальная версия</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            )}

            <Alert
              message="Автоматическое обновление через GitHub"
              description="Система проверяет обновления в GitHub репозитории и может автоматически обновиться до последней версии."
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Button
                type="primary"
                size="large"
                icon={<SyncOutlined />}
                onClick={handleCheckUpdates}
                block
              >
                Проверить обновления
              </Button>

              <Divider>Ручное обновление</Divider>

              <Alert
                message="Команды для обновления"
                description={
                  <div>
                    <p>Linux:</p>
                    <pre style={{ background: '#f5f5f5', padding: 12 }}>
                      {`cd /opt/siem
git pull origin main
docker-compose pull
docker-compose up -d --build`}
                    </pre>
                    <p>Windows:</p>
                    <pre style={{ background: '#f5f5f5', padding: 12 }}>
                      {`cd C:\\SIEM
git pull origin main
docker-compose pull
docker-compose up -d --build`}
                    </pre>
                  </div>
                }
                type="success"
              />
            </Space>
          </TabPane>

          {/* Email Settings */}
          <TabPane
            tab={
              <span>
                <GlobalOutlined />
                Email Notifications
              </span>
            }
            key="email"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Email уведомления"
                description="Настройте SMTP для отправки email уведомлений о критических алертах и инцидентах."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item name="smtp_enabled" label="Включить Email уведомления" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                name="smtp_host"
                label="SMTP Host"
                rules={[{ required: true, message: 'Введите SMTP хост' }]}
              >
                <Input placeholder="smtp.gmail.com" />
              </Form.Item>

              <Form.Item
                name="smtp_port"
                label="SMTP Port"
                rules={[{ required: true, message: 'Введите порт' }]}
              >
                <InputNumber min={1} max={65535} placeholder="587" style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item name="smtp_username" label="SMTP Username">
                <Input placeholder="your-email@example.com" />
              </Form.Item>

              <Form.Item name="smtp_password" label="SMTP Password">
                <Input.Password placeholder="Пароль от почты" />
              </Form.Item>

              <Form.Item
                name="smtp_from_email"
                label="From Email"
                rules={[
                  { required: true, message: 'Введите email отправителя' },
                  { type: 'email', message: 'Введите корректный email' },
                ]}
              >
                <Input placeholder="siem@example.com" />
              </Form.Item>

              <Form.Item name="smtp_from_name" label="From Name">
                <Input placeholder="SIEM System" />
              </Form.Item>

              <Form.Item name="smtp_use_tls" label="Использовать TLS" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Divider>Настройки уведомлений</Divider>

              <Form.Item
                name="email_alert_recipients"
                label="Получатели уведомлений"
                rules={[{ required: true, message: 'Введите email получателей' }]}
                extra="Несколько адресов через запятую: admin@company.com, security@company.com"
              >
                <TextArea
                  rows={2}
                  placeholder="admin@company.com, security@company.com"
                />
              </Form.Item>

              <Form.Item
                name="email_alert_min_severity"
                label="Минимальный уровень severity для email"
                extra="Только алерты с указанным и выше уровнем будут отправляться на email"
              >
                <Select>
                  <Option value={0}>Info (0)</Option>
                  <Option value={1}>Low (1)</Option>
                  <Option value={2}>Medium (2)</Option>
                  <Option value={3}>High (3) - Рекомендуется</Option>
                  <Option value={4}>Critical (4)</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                    Сохранить
                  </Button>
                  <Button onClick={handleTestEmail} icon={<CheckCircleOutlined />}>
                    Отправить тестовое письмо
                  </Button>
                </Space>
              </Form.Item>

              <Alert
                message="Документация"
                description={
                  <div>
                    <p>Подробная инструкция по настройке email:</p>
                    <ul>
                      <li><a href="/docs/PHASE1_SETUP.md#2-email-notifications" target="_blank">Email Notifications Setup Guide</a></li>
                      <li>Gmail: требуется App Password (не обычный пароль!)</li>
                      <li>Yandex Mail: smtp.yandex.ru:587</li>
                      <li>Mail.ru: smtp.mail.ru:587</li>
                    </ul>
                  </div>
                }
                type="warning"
                showIcon
              />
            </Form>
          </TabPane>

          {/* AI Configuration */}
          <TabPane
            tab={
              <span>
                <BulbOutlined />
                AI Configuration
              </span>
            }
            key="ai"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="AI-анализ инцидентов"
                description="Выберите провайдера AI для автоматического анализа событий и инцидентов."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item name="ai_provider" label="AI Provider">
                <Select>
                  <Option value="none">None (отключить AI)</Option>
                  <Option value="deepseek">DeepSeek (бесплатно)</Option>
                  <Option value="yandex_gpt">Yandex GPT</Option>
                </Select>
              </Form.Item>

              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) =>
                  prevValues.ai_provider !== currentValues.ai_provider
                }
              >
                {({ getFieldValue }) =>
                  getFieldValue('ai_provider') === 'deepseek' ? (
                    <Form.Item
                      name="deepseek_api_key"
                      label="DeepSeek API Key"
                      extra={
                        <a href="https://platform.deepseek.com/" target="_blank" rel="noreferrer">
                          Получить API ключ →
                        </a>
                      }
                    >
                      <Input.Password placeholder="DeepSeek API Key" />
                    </Form.Item>
                  ) : null
                }
              </Form.Item>

              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) =>
                  prevValues.ai_provider !== currentValues.ai_provider
                }
              >
                {({ getFieldValue }) =>
                  getFieldValue('ai_provider') === 'yandex_gpt' ? (
                    <>
                      <Form.Item name="yandex_gpt_api_key" label="Yandex GPT API Key">
                        <Input.Password placeholder="Yandex GPT API Key" />
                      </Form.Item>
                      <Form.Item name="yandex_gpt_folder_id" label="Yandex GPT Folder ID">
                        <Input placeholder="Folder ID" />
                      </Form.Item>
                    </>
                  ) : null
                }
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                  Сохранить
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          {/* Threat Intelligence */}
          <TabPane
            tab={
              <span>
                <SecurityScanOutlined />
                Threat Intelligence
              </span>
            }
            key="threat_intel"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Threat Intelligence Integration"
                description="Автоматическое обогащение алертов данными о репутации IP адресов и файлов из VirusTotal и AbuseIPDB."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item
                name="threat_intel_enabled"
                label="Включить Threat Intelligence"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Divider>VirusTotal</Divider>

              <Form.Item
                name="virustotal_api_key"
                label="VirusTotal API Key"
                extra={
                  <a href="https://www.virustotal.com/gui/join-us" target="_blank" rel="noreferrer">
                    Получить API ключ →
                  </a>
                }
              >
                <Input.Password placeholder="VirusTotal API Key" />
              </Form.Item>

              <Divider>AbuseIPDB</Divider>

              <Form.Item
                name="abuseipdb_api_key"
                label="AbuseIPDB API Key"
                extra={
                  <a href="https://www.abuseipdb.com/register" target="_blank" rel="noreferrer">
                    Получить API ключ →
                  </a>
                }
              >
                <Input.Password placeholder="AbuseIPDB API Key" />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                  Сохранить
                </Button>
              </Form.Item>

              <Alert
                message="Документация"
                description={
                  <div>
                    <p>Подробная инструкция по настройке Threat Intelligence:</p>
                    <ul>
                      <li>
                        <a href="/docs/PHASE1_SETUP.md#4-threat-intelligence" target="_blank">
                          Threat Intelligence Setup Guide
                        </a>
                      </li>
                      <li>VirusTotal: 4 requests/minute (500/day) на бесплатном тарифе</li>
                      <li>AbuseIPDB: 1,000 requests/day на бесплатном тарифе</li>
                      <li>Система автоматически кэширует результаты на 24 часа для экономии запросов</li>
                    </ul>
                  </div>
                }
                type="warning"
                showIcon
              />
            </Form>
          </TabPane>
        </Tabs>
      </Card>

      {/* Update Progress Modal */}
      <Modal
        title="Обновление системы"
        open={updateModalVisible}
        footer={null}
        closable={updateProgress === 100}
        onCancel={() => setUpdateModalVisible(false)}
        width={700}
      >
        <Progress percent={updateProgress} status={updateProgress < 100 ? 'active' : 'success'} />

        <div
          style={{
            marginTop: 16,
            maxHeight: 400,
            overflowY: 'auto',
            background: '#000',
            color: '#0f0',
            padding: 12,
            fontFamily: 'monospace',
            fontSize: 12,
          }}
        >
          {updateLogs.map((log, idx) => (
            <div key={idx}>{log}</div>
          ))}
        </div>
      </Modal>
    </div>
  )
}
