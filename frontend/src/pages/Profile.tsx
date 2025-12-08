import { useState } from 'react'
import {
  Card,
  Row,
  Col,
  Descriptions,
  Form,
  Input,
  Button,
  message,
  Typography,
  Space,
  Tag,
  Divider,
  Alert,
} from 'antd'
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  CrownOutlined,
  SafetyOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/store'
import { apiService } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography

// Role colors and labels
const ROLE_CONFIG = {
  admin: { label: 'Administrator', color: 'red', icon: <CrownOutlined /> },
  analyst: { label: 'Analyst', color: 'blue', icon: <SafetyOutlined /> },
  viewer: { label: 'Viewer', color: 'green', icon: <EyeOutlined /> },
}

export default function Profile() {
  const user = useAuthStore((state) => state.user)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  // Handle password change
  const handleChangePassword = async (values: any) => {
    setLoading(true)
    try {
      await apiService.changePassword(values.old_password, values.new_password)
      message.success('Password changed successfully')
      form.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to change password')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return (
      <Card>
        <Alert message="Not logged in" description="Please log in to view your profile." type="warning" showIcon />
      </Card>
    )
  }

  const roleConfig = ROLE_CONFIG[user.Role as keyof typeof ROLE_CONFIG]

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* Profile Information */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <Title level={4} style={{ margin: 0 }}>
                  Profile Information
                </Title>
              </Space>
            }
          >
            <Descriptions bordered column={1} size="middle">
              <Descriptions.Item label="Username">
                <Space>
                  <UserOutlined />
                  <Text strong>{user.Username}</Text>
                </Space>
              </Descriptions.Item>

              <Descriptions.Item label="Full Name">
                <Text>{user.FullName}</Text>
              </Descriptions.Item>

              <Descriptions.Item label="Email">
                <Space>
                  {user.Email && <MailOutlined />}
                  <Text>{user.Email || '-'}</Text>
                </Space>
              </Descriptions.Item>

              <Descriptions.Item label="Role">
                <Tag color={roleConfig?.color || 'default'} icon={roleConfig?.icon} style={{ fontSize: 14 }}>
                  {roleConfig?.label || user.Role}
                </Tag>
              </Descriptions.Item>

              <Descriptions.Item label="Status">
                {user.IsActive ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    Active
                  </Tag>
                ) : (
                  <Tag color="error">Inactive</Tag>
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Account Created">
                <Space>
                  <ClockCircleOutlined />
                  <Text>{dayjs(user.CreatedAt).format('YYYY-MM-DD HH:mm:ss')}</Text>
                </Space>
              </Descriptions.Item>

              <Descriptions.Item label="Last Login">
                <Space>
                  <ClockCircleOutlined />
                  <Text>{user.LastLogin ? dayjs(user.LastLogin).format('YYYY-MM-DD HH:mm:ss') : 'Never'}</Text>
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            {/* Role Permissions */}
            <div>
              <Title level={5}>Role Permissions</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                {user.Role === 'admin' && (
                  <>
                    <Alert
                      message="Administrator"
                      description="Full system access: manage users, configure settings, view all data, manage detection rules, create/modify playbooks."
                      type="error"
                      showIcon
                      icon={<CrownOutlined />}
                    />
                  </>
                )}
                {user.Role === 'analyst' && (
                  <>
                    <Alert
                      message="Analyst"
                      description="Manage security operations: view events, manage alerts and incidents, execute playbooks, create detection rules."
                      type="info"
                      showIcon
                      icon={<SafetyOutlined />}
                    />
                  </>
                )}
                {user.Role === 'viewer' && (
                  <>
                    <Alert
                      message="Viewer"
                      description="Read-only access: view events, alerts, incidents, and dashboards. Cannot modify any data."
                      type="success"
                      showIcon
                      icon={<EyeOutlined />}
                    />
                  </>
                )}
              </Space>
            </div>
          </Card>
        </Col>

        {/* Change Password */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <LockOutlined />
                <Title level={4} style={{ margin: 0 }}>
                  Change Password
                </Title>
              </Space>
            }
          >
            <Alert
              message="Password Security"
              description="Use a strong password with at least 8 characters, including uppercase, lowercase, numbers, and special characters."
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleChangePassword}
              autoComplete="off"
            >
              <Form.Item
                name="old_password"
                label="Current Password"
                rules={[{ required: true, message: 'Please enter your current password' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Enter current password"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item
                name="new_password"
                label="New Password"
                rules={[
                  { required: true, message: 'Please enter new password' },
                  { min: 8, message: 'Password must be at least 8 characters' },
                  {
                    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                    message: 'Password must contain uppercase, lowercase, number, and special character',
                  },
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Enter new password"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item
                name="confirm_password"
                label="Confirm New Password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Please confirm new password' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve()
                      }
                      return Promise.reject(new Error('Passwords do not match'))
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Confirm new password"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  Change Password
                </Button>
              </Form.Item>
            </Form>

            <Divider />

            {/* Security Tips */}
            <div>
              <Title level={5}>Password Security Tips</Title>
              <ul style={{ paddingLeft: 20 }}>
                <li>Use a unique password for this account</li>
                <li>Don't share your password with anyone</li>
                <li>Change your password regularly (every 90 days)</li>
                <li>Don't use personal information in passwords</li>
                <li>Use a password manager to generate and store passwords</li>
              </ul>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Session Information */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <Title level={4} style={{ margin: 0 }}>
                  Session Information
                </Title>
              </Space>
            }
          >
            <Descriptions bordered column={2} size="middle">
              <Descriptions.Item label="User ID">{user.UserId}</Descriptions.Item>
              <Descriptions.Item label="Username">{user.Username}</Descriptions.Item>
              <Descriptions.Item label="Current Session Started">
                {dayjs().format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Last Activity">
                {dayjs().format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
