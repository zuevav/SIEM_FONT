import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Button,
  Input,
  Form,
  message,
  Typography,
  Space,
  Spin,
  Result,
  Steps,
  Alert,
  Descriptions,
  Divider,
} from 'antd'
import {
  UserOutlined,
  DesktopOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  CopyOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

interface SessionInfo {
  session_id: number
  token: string
  requester_name: string
  requester_computer: string
  description: string
  status: string
  expires_at: string
}

interface SessionStatus {
  status: string
  helper_name: string | null
  helper_joined_at: string | null
  connection_password: string | null
  port: number | null
  can_connect: boolean
}

export default function PeerHelp() {
  const { token } = useParams<{ token: string }>()
  const [loading, setLoading] = useState(true)
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [helperName, setHelperName] = useState('')
  const [joined, setJoined] = useState(false)
  const [form] = Form.useForm()

  // Fetch session info
  const fetchSession = async () => {
    if (!token) return

    try {
      const response = await fetch(`/api/v1/ad/peer-help/${token}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Сессия не найдена')
      }
      const data = await response.json()
      setSession(data)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fetch session status (for polling after joining)
  const fetchStatus = async () => {
    if (!token) return

    try {
      const response = await fetch(`/api/v1/ad/peer-help/${token}/status`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (err) {
      console.error('Error fetching status:', err)
    }
  }

  useEffect(() => {
    fetchSession()
  }, [token])

  // Poll for status updates after joining
  useEffect(() => {
    if (!joined) return

    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [joined, token])

  const handleJoin = async (values: { name: string }) => {
    if (!token) return

    try {
      const response = await fetch(`/api/v1/ad/peer-help/${token}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          helper_name: values.name,
          helper_ip: null, // Will be detected server-side
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Ошибка подключения')
      }

      setHelperName(values.name)
      setJoined(true)
      message.success('Запрос отправлен! Ожидайте подтверждения...')
      fetchStatus()
    } catch (err: any) {
      message.error(err.message)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    message.success('Скопировано в буфер обмена')
  }

  // Loading state
  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: 20,
        }}
      >
        <Card style={{ maxWidth: 500, width: '100%', borderRadius: 16 }}>
          <Result
            status="error"
            title="Ссылка недействительна"
            subTitle={error}
            extra={
              <Button type="primary" onClick={() => window.close()}>
                Закрыть
              </Button>
            }
          />
        </Card>
      </div>
    )
  }

  // Calculate step
  let currentStep = 0
  if (joined) currentStep = 1
  if (status?.status === 'active') currentStep = 2
  if (status?.status === 'completed') currentStep = 3
  if (status?.status === 'declined') currentStep = -1

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 20,
      }}
    >
      <Card
        style={{
          maxWidth: 600,
          width: '100%',
          borderRadius: 20,
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Header */}
          <div style={{ textAlign: 'center' }}>
            <DesktopOutlined style={{ fontSize: 48, color: '#667eea' }} />
            <Title level={3} style={{ margin: '16px 0 0' }}>
              Удаленная помощь
            </Title>
            <Text type="secondary">Помогите коллеге с проблемой на компьютере</Text>
          </div>

          {/* Session Info */}
          {session && (
            <Card size="small" style={{ background: '#f5f5f5', borderRadius: 12 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label={<><UserOutlined /> Пользователь</>}>
                  <Text strong>{session.requester_name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label={<><DesktopOutlined /> Компьютер</>}>
                  {session.requester_computer}
                </Descriptions.Item>
                {session.description && (
                  <Descriptions.Item label="Проблема">
                    {session.description}
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Card>
          )}

          {/* Steps */}
          <Steps
            size="small"
            current={currentStep}
            items={[
              { title: 'Присоединиться', icon: <LinkOutlined /> },
              { title: 'Ожидание', icon: <ClockCircleOutlined /> },
              { title: 'Подключение', icon: <DesktopOutlined /> },
            ]}
          />

          <Divider style={{ margin: '12px 0' }} />

          {/* Status: Declined */}
          {status?.status === 'declined' && (
            <Result
              status="warning"
              title="Подключение отклонено"
              subTitle="Пользователь отклонил запрос на подключение"
              extra={
                <Button onClick={() => window.close()}>Закрыть</Button>
              }
            />
          )}

          {/* Status: Not joined yet */}
          {!joined && status?.status !== 'declined' && (
            <Form form={form} layout="vertical" onFinish={handleJoin}>
              <Form.Item
                name="name"
                label="Ваше имя"
                rules={[{ required: true, message: 'Введите ваше имя' }]}
              >
                <Input
                  size="large"
                  prefix={<UserOutlined />}
                  placeholder="Как вас зовут?"
                  autoFocus
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  size="large"
                  htmlType="submit"
                  block
                  style={{ height: 50, fontSize: 16 }}
                >
                  Присоединиться для помощи
                </Button>
              </Form.Item>

              <Text type="secondary" style={{ display: 'block', textAlign: 'center' }}>
                После нажатия кнопки, пользователь получит запрос на подтверждение
              </Text>
            </Form>
          )}

          {/* Status: Waiting for consent */}
          {joined && status?.status === 'helper_joined' && (
            <div style={{ textAlign: 'center', padding: 20 }}>
              <Spin
                indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
              />
              <Title level={4} style={{ marginTop: 24 }}>
                Ожидание подтверждения
              </Title>
              <Paragraph type="secondary">
                {session?.requester_name} должен подтвердить ваше подключение.
                <br />
                Пожалуйста, подождите...
              </Paragraph>
            </div>
          )}

          {/* Status: Active - Can connect */}
          {status?.status === 'active' && (
            <div>
              <Alert
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
                message="Подключение разрешено!"
                description={`${session?.requester_name} разрешил подключение к компьютеру`}
                style={{ marginBottom: 16 }}
              />

              {status.connection_password && (
                <Card size="small" style={{ background: '#f6ffed', borderColor: '#b7eb8f' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>Данные для подключения:</Text>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Text>Компьютер:</Text>
                      <Text code>{session?.requester_computer}</Text>
                      <Button
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(session?.requester_computer || '')}
                      />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Text>Пароль:</Text>
                      <Text code style={{ fontSize: 18, fontWeight: 'bold' }}>
                        {status.connection_password}
                      </Text>
                      <Button
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(status.connection_password || '')}
                      />
                    </div>

                    <Divider style={{ margin: '12px 0' }} />

                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      <strong>Как подключиться:</strong>
                      <ol style={{ paddingLeft: 20, marginTop: 8 }}>
                        <li>Откройте "Удаленный помощник Windows" (msra.exe)</li>
                        <li>Выберите "Помочь пригласившему вас пользователю"</li>
                        <li>Введите имя компьютера: <Text code>{session?.requester_computer}</Text></li>
                        <li>Введите пароль: <Text code>{status.connection_password}</Text></li>
                      </ol>
                    </Paragraph>

                    <Button
                      type="primary"
                      size="large"
                      block
                      onClick={() => {
                        // Try to open msra.exe (works only on Windows)
                        window.open(`msra://${session?.requester_computer}`, '_blank')
                        message.info('Запуск Remote Assistance...')
                      }}
                    >
                      Открыть Remote Assistance
                    </Button>
                  </Space>
                </Card>
              )}
            </div>
          )}

          {/* Status: Completed */}
          {status?.status === 'completed' && (
            <Result
              status="success"
              title="Сессия завершена"
              subTitle="Спасибо за помощь!"
              extra={
                <Button type="primary" onClick={() => window.close()}>
                  Закрыть
                </Button>
              }
            />
          )}

          {/* Footer */}
          <div style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Powered by SIEM • Безопасное удаленное подключение
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}
