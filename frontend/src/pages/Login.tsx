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
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Col xs={22} sm={18} md={12} lg={8} xl={6}>
        <Card
          bordered={false}
          style={{
            borderRadius: 16,
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%', textAlign: 'center' }}>
            <div>
              <SafetyOutlined style={{ fontSize: 64, color: '#667eea' }} />
              <Title level={2} style={{ marginTop: 16, marginBottom: 0 }}>
                SIEM System
              </Title>
              <Text type="secondary">Security Information & Event Management</Text>
            </div>

            {error && (
              <Alert
                message="Ошибка входа"
                description={error}
                type="error"
                showIcon
                closable
                onClose={clearError}
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
                  prefix={<UserOutlined />}
                  placeholder="Имя пользователя"
                  autoComplete="username"
                />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: 'Введите пароль' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Пароль"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={isLoading}>
                  Войти
                </Button>
              </Form.Item>
            </Form>

            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Учётные данные по умолчанию:
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                admin / Admin123!
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                analyst / Admin123!
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                viewer / Admin123!
              </Text>
            </Space>

            <Text type="secondary" style={{ fontSize: 12 }}>
              © 2024 SIEM System. Version 0.9.0
            </Text>
          </Space>
        </Card>
      </Col>
    </Row>
  )
}
