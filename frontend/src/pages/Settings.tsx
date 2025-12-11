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
  SendOutlined,
  TeamOutlined,
  BankOutlined,
  DatabaseOutlined,
  LockOutlined,
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

  // Active Directory
  ad_enabled: boolean
  ad_server: string
  ad_base_dn: string
  ad_bind_user: string
  ad_bind_password: string
  ad_sync_enabled: boolean
  ad_sync_interval_hours: number
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
  const [testingAD, setTestingAD] = useState(false)
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

  const handleTestAD = async () => {
    setTestingAD(true)
    try {
      const values = form.getFieldsValue(['ad_server', 'ad_base_dn', 'ad_bind_user', 'ad_bind_password'])

      if (!values.ad_server || !values.ad_base_dn || !values.ad_bind_user || !values.ad_bind_password) {
        message.error('Заполните все поля для подключения к AD')
        setTestingAD(false)
        return
      }

      const result = await apiService.testADConnection(
        values.ad_server,
        values.ad_base_dn,
        values.ad_bind_user,
        values.ad_bind_password
      )

      if (result.success) {
        let successMsg = `Подключение успешно! Сервер: ${result.server_type || 'LDAP'}`
        if (result.user_count !== undefined) {
          successMsg += `, найдено пользователей: ${result.user_count}`
        }
        message.success(successMsg)
      } else {
        message.error(`Ошибка подключения: ${result.error || result.message}`)
      }
    } catch (error: any) {
      message.error(`Не удалось подключиться к AD: ${error.response?.data?.detail || error.message}`)
    } finally {
      setTestingAD(false)
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

          {/* Telegram */}
          <TabPane
            tab={
              <span>
                <SendOutlined />
                Telegram
              </span>
            }
            key="telegram"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Telegram уведомления"
                description="Мгновенные уведомления о критических событиях в Telegram-канал или чат."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item name="telegram_enabled" label="Включить Telegram уведомления" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                name="telegram_bot_token"
                label="Bot Token"
                extra="Получите токен у @BotFather в Telegram"
              >
                <Input.Password placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz" />
              </Form.Item>

              <Form.Item
                name="telegram_chat_id"
                label="Chat ID"
                extra="ID канала или чата для отправки уведомлений (используйте @getidsbot)"
              >
                <Input placeholder="-1001234567890" />
              </Form.Item>

              <Form.Item
                name="telegram_min_severity"
                label="Минимальный уровень severity"
                extra="Только алерты с указанным и выше уровнем будут отправляться"
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
                  <Button icon={<CheckCircleOutlined />}>
                    Отправить тест
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </TabPane>

          {/* Active Directory */}
          <TabPane
            tab={
              <span>
                <TeamOutlined />
                Active Directory
              </span>
            }
            key="ad"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Интеграция с Active Directory"
                description="Аутентификация пользователей через корпоративный AD/LDAP и синхронизация групп."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item name="ad_enabled" label="Включить AD аутентификацию" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                name="ad_server"
                label="LDAP Server URL"
                extra="Например: ldap://dc.company.local:389 или ldaps://dc.company.local:636"
              >
                <Input placeholder="ldap://dc.company.local:389" />
              </Form.Item>

              <Form.Item
                name="ad_base_dn"
                label="Base DN"
                extra="Корневой DN для поиска пользователей"
              >
                <Input placeholder="DC=company,DC=local" />
              </Form.Item>

              <Form.Item
                name="ad_bind_user"
                label="Bind User DN"
                extra="Учётная запись для подключения к AD"
              >
                <Input placeholder="CN=siem-service,OU=ServiceAccounts,DC=company,DC=local" />
              </Form.Item>

              <Form.Item name="ad_bind_password" label="Bind Password">
                <Input.Password placeholder="Пароль сервисной учётной записи" />
              </Form.Item>

              <Divider>Синхронизация</Divider>

              <Form.Item name="ad_sync_enabled" label="Автоматическая синхронизация пользователей" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                name="ad_sync_interval_hours"
                label="Интервал синхронизации (часы)"
              >
                <InputNumber min={1} max={168} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                    Сохранить
                  </Button>
                  <Button onClick={handleTestAD} loading={testingAD} icon={<CheckCircleOutlined />}>
                    Тест подключения
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </TabPane>

          {/* CBR Organization Settings */}
          <TabPane
            tab={
              <span>
                <BankOutlined />
                ЦБ РФ (Организация)
              </span>
            }
            key="cbr"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Реквизиты организации для отчётности ЦБ РФ"
                description="Информация об организации для формирования отчётов в соответствии с 683-П, 716-П, 747-П."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Divider>Реквизиты организации</Divider>

              <Form.Item name="cbr_org_name" label="Наименование организации">
                <Input placeholder="ООО «Компания»" />
              </Form.Item>

              <Form.Item name="cbr_org_inn" label="ИНН">
                <Input placeholder="7712345678" maxLength={12} />
              </Form.Item>

              <Form.Item name="cbr_org_ogrn" label="ОГРН">
                <Input placeholder="1027700000000" maxLength={15} />
              </Form.Item>

              <Form.Item name="cbr_org_kpp" label="КПП">
                <Input placeholder="771201001" maxLength={9} />
              </Form.Item>

              <Form.Item name="cbr_org_address" label="Юридический адрес">
                <TextArea rows={2} placeholder="123456, г. Москва, ул. Примерная, д. 1" />
              </Form.Item>

              <Form.Item name="cbr_org_phone" label="Телефон">
                <Input placeholder="+7 (495) 123-45-67" />
              </Form.Item>

              <Form.Item name="cbr_org_email" label="Email организации">
                <Input placeholder="security@company.ru" />
              </Form.Item>

              <Divider>Контактное лицо</Divider>

              <Form.Item name="cbr_contact_person" label="ФИО">
                <Input placeholder="Иванов Иван Иванович" />
              </Form.Item>

              <Form.Item name="cbr_contact_position" label="Должность">
                <Input placeholder="Руководитель отдела информационной безопасности" />
              </Form.Item>

              <Form.Item name="cbr_contact_email" label="Email">
                <Input placeholder="ivanov@company.ru" />
              </Form.Item>

              <Form.Item name="cbr_contact_phone" label="Телефон">
                <Input placeholder="+7 (495) 123-45-68" />
              </Form.Item>

              <Divider>FinCERT интеграция</Divider>

              <Form.Item name="cbr_fincert_enabled" label="Включить FinCERT" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item name="cbr_fincert_api_key" label="FinCERT API Key">
                <Input.Password placeholder="API ключ для FinCERT" />
              </Form.Item>

              <Form.Item name="cbr_fincert_org_id" label="Organization ID в FinCERT">
                <Input placeholder="ID организации" />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                  Сохранить
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          {/* Data Retention */}
          <TabPane
            tab={
              <span>
                <DatabaseOutlined />
                Хранение данных
              </span>
            }
            key="retention"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Политика хранения данных"
                description="Настройте сроки хранения различных типов данных в соответствии с требованиями регуляторов."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form.Item
                name="retention_days"
                label="Хранение событий (дней)"
                extra="Рекомендуется: 1825 дней (5 лет) для соответствия ЦБ РФ"
              >
                <InputNumber min={30} max={3650} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="retention_alerts_days"
                label="Хранение алертов (дней)"
              >
                <InputNumber min={30} max={3650} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="retention_incidents_days"
                label="Хранение инцидентов (дней)"
                extra="Рекомендуется: 2555 дней (7 лет) для критических инцидентов"
              >
                <InputNumber min={30} max={3650} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="retention_audit_days"
                label="Хранение журнала аудита (дней)"
              >
                <InputNumber min={30} max={3650} style={{ width: '100%' }} />
              </Form.Item>

              <Divider>Автоматическая очистка</Divider>

              <Form.Item name="auto_purge_enabled" label="Включить автоматическую очистку" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item
                name="auto_purge_batch_size"
                label="Размер пакета очистки"
                extra="Количество записей за одну операцию очистки"
              >
                <InputNumber min={1000} max={100000} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                  Сохранить
                </Button>
              </Form.Item>

              <Alert
                message="Внимание"
                description="Изменение сроков хранения не повлияет на уже удалённые данные. Данные, превышающие новый срок хранения, будут удалены при следующей очистке."
                type="warning"
                showIcon
              />
            </Form>
          </TabPane>

          {/* Security Settings */}
          <TabPane
            tab={
              <span>
                <LockOutlined />
                Безопасность
              </span>
            }
            key="security"
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={settings || {}}
            >
              <Alert
                message="Настройки безопасности"
                description="Политики паролей, блокировка учётных записей и другие параметры безопасности."
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Divider>Политика паролей</Divider>

              <Form.Item
                name="password_min_length"
                label="Минимальная длина пароля"
                extra="Рекомендуется: 12 символов"
              >
                <InputNumber min={8} max={128} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item name="password_require_uppercase" label="Требовать заглавные буквы" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item name="password_require_lowercase" label="Требовать строчные буквы" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item name="password_require_digits" label="Требовать цифры" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item name="password_require_special" label="Требовать спецсимволы (!@#$%^&*)" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Divider>Блокировка учётных записей</Divider>

              <Form.Item
                name="failed_login_attempts"
                label="Попыток до блокировки"
                extra="Количество неудачных попыток входа до блокировки учётной записи"
              >
                <InputNumber min={3} max={10} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="account_lockout_minutes"
                label="Время блокировки (минуты)"
                extra="Время, на которое блокируется учётная запись"
              >
                <InputNumber min={5} max={1440} style={{ width: '100%' }} />
              </Form.Item>

              <Divider>Сессии</Divider>

              <Form.Item
                name="session_timeout_minutes"
                label="Таймаут сессии (минуты)"
                extra="Время бездействия до автоматического выхода"
              >
                <InputNumber min={15} max={1440} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="jwt_access_token_expire_minutes"
                label="Время жизни токена (минуты)"
              >
                <InputNumber min={15} max={1440} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                  Сохранить
                </Button>
              </Form.Item>
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
