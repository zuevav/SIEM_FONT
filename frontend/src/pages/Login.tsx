import { useEffect } from 'react'
import { Form, Input, Button, Card, Typography, Space, Alert, Row, Col } from 'antd'
import { UserOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store'

const { Title, Text } = Typography

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading, error, clearError, isAuthenticated } = useAuthStore()
  const [form] = Form.useForm()

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/')
    }
  }, [isAuthenticated, navigate])

  useEffect(() => {
    return () => clearError()
  }, [clearError])

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      await login(values.username, values.password)
      navigate('/')
    } catch (error) {
      // Error handled by store
    }
  }

  return (
    <Row
      justify="center"
      align="middle"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
      }}
    >
      <Col xs={22} sm={18} md={12} lg={8} xl={6}>
        <Card
          bordered={false}
          style={{
            borderRadius: 20,
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            backdropFilter: 'blur(20px)',
            background: 'rgba(255, 255, 255, 0.95)',
          }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%', textAlign: 'center' }}>
            <div>
              <SafetyOutlined style={{ fontSize: 64, color: '#007AFF' }} />
              <Title level={2} style={{ marginTop: 16, marginBottom: 0, fontWeight: 600 }}>
                SIEM System
              </Title>
              <Text type="secondary">Система мониторинга безопасности</Text>
            </div>

            {error && (
              <Alert
                message="Ошибка входа"
                description={error}
                type="error"
                showIcon
                closable
                onClose={clearError}
                style={{ borderRadius: 12, textAlign: 'left' }}
              />
            )}

            <Form
              form={form}
              name="login"
              onFinish={handleSubmit}
              layout="vertical"
              size="large"
              requiredMark={false}
            >
              <Form.Item
                name="username"
                rules={[{ required: true, message: 'Введите имя пользователя' }]}
              >
                <Input
                  prefix={<UserOutlined style={{ color: '#86868B' }} />}
                  placeholder="Имя пользователя"
                  autoComplete="username"
                  style={{ height: 48, borderRadius: 12 }}
                />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: 'Введите пароль' }]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#86868B' }} />}
                  placeholder="Пароль"
                  autoComplete="current-password"
                  style={{ height: 48, borderRadius: 12 }}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  loading={isLoading}
                  style={{
                    height: 48,
                    borderRadius: 12,
                    fontWeight: 500,
                    fontSize: 16,
                  }}
                >
                  Войти в систему
                </Button>
              </Form.Item>
            </Form>

            <Text type="secondary" style={{ fontSize: 12 }}>
              Обратитесь к администратору для получения учётных данных
            </Text>

            <Text type="secondary" style={{ fontSize: 12 }}>
              © 2025 SIEM System. Version 1.0.0
            </Text>
          </Space>
        </Card>
      </Col>
    </Row>
  )
}
