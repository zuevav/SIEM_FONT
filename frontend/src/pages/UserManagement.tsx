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
  Tooltip,
  Typography,
  Badge,
  Alert,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  UserOutlined,
  LockOutlined,
  MailOutlined,
  CrownOutlined,
  EyeOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { User } from '@/types'
import { apiService } from '@/services/api'
import { useAuthStore } from '@/store'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select

// Role colors and labels
const ROLE_CONFIG = {
  admin: { label: 'Admin', color: 'red', icon: <CrownOutlined /> },
  analyst: { label: 'Analyst', color: 'blue', icon: <SafetyOutlined /> },
  viewer: { label: 'Viewer', color: 'green', icon: <EyeOutlined /> },
}

export default function UserManagement() {
  const currentUser = useAuthStore((state) => state.user)
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')

  // Modals
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  // Forms
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  // Check if current user is admin
  const isAdmin = currentUser?.Role === 'admin'

  // Load users
  const loadUsers = async () => {
    setLoading(true)
    try {
      const data = await apiService.getUsers()
      setUsers(data)
    } catch (error) {
      message.error('Failed to load users')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) {
      loadUsers()
    }
  }, [isAdmin])

  // Filter users
  const filteredUsers = users.filter((user) => {
    if (roleFilter && user.Role !== roleFilter) return false
    if (statusFilter === 'active' && !user.IsActive) return false
    if (statusFilter === 'inactive' && user.IsActive) return false
    if (searchText) {
      const search = searchText.toLowerCase()
      return (
        user.Username.toLowerCase().includes(search) ||
        user.FullName.toLowerCase().includes(search) ||
        user.Email?.toLowerCase().includes(search)
      )
    }
    return true
  })

  // Handle create
  const handleCreate = async (values: any) => {
    try {
      await apiService.createUser({
        username: values.username,
        password: values.password,
        full_name: values.full_name,
        email: values.email,
        role: values.role,
      })
      message.success('User created successfully')
      setCreateModalVisible(false)
      createForm.resetFields()
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to create user')
      console.error(error)
    }
  }

  // Handle edit
  const handleEdit = (user: User) => {
    setSelectedUser(user)
    editForm.setFieldsValue({
      username: user.Username,
      full_name: user.FullName,
      email: user.Email,
      role: user.Role,
      is_active: user.IsActive,
    })
    setEditModalVisible(true)
  }

  // Handle update
  const handleUpdate = async (values: any) => {
    if (!selectedUser) return

    try {
      // FIX BUG-015: Use snake_case field names as expected by backend API (UserUpdate schema)
      await apiService.updateUser(selectedUser.UserId, {
        email: values.email,
        role: values.role,
        is_active: values.is_active,
      })
      message.success('User updated successfully')
      setEditModalVisible(false)
      setSelectedUser(null)
      editForm.resetFields()
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to update user')
      console.error(error)
    }
  }

  // Handle delete
  const handleDelete = async (userId: number) => {
    try {
      await apiService.deleteUser(userId)
      message.success('User deleted successfully')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to delete user')
      console.error(error)
    }
  }

  // Handle toggle active status
  const handleToggleActive = async (user: User) => {
    try {
      // FIX BUG-015: Use snake_case field names as expected by backend API
      await apiService.updateUser(user.UserId, {
        is_active: !user.IsActive,
      })
      message.success(`User ${!user.IsActive ? 'activated' : 'deactivated'} successfully`)
      loadUsers()
    } catch (error) {
      message.error('Failed to update user status')
      console.error(error)
    }
  }

  // Table columns
  const columns: ColumnsType<User> = [
    {
      title: 'Status',
      dataIndex: 'IsActive',
      key: 'IsActive',
      width: 80,
      render: (active: boolean, record) => (
        <Tooltip title={active ? 'Active' : 'Inactive'}>
          <Switch
            checked={active}
            onChange={() => handleToggleActive(record)}
            disabled={record.UserId === currentUser?.UserId}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<CloseCircleOutlined />}
          />
        </Tooltip>
      ),
    },
    {
      title: 'Username',
      dataIndex: 'Username',
      key: 'Username',
      width: 150,
      render: (username: string, record) => (
        <Space>
          <UserOutlined />
          <Text strong>{username}</Text>
          {record.UserId === currentUser?.UserId && <Tag color="blue">You</Tag>}
        </Space>
      ),
    },
    {
      title: 'Full Name',
      dataIndex: 'FullName',
      key: 'FullName',
      width: 200,
    },
    {
      title: 'Email',
      dataIndex: 'Email',
      key: 'Email',
      width: 200,
      render: (email?: string) => (
        <Space>
          {email && <MailOutlined />}
          {email || '-'}
        </Space>
      ),
    },
    {
      title: 'Role',
      dataIndex: 'Role',
      key: 'Role',
      width: 120,
      render: (role: string) => {
        const config = ROLE_CONFIG[role as keyof typeof ROLE_CONFIG]
        return (
          <Tag color={config?.color || 'default'} icon={config?.icon}>
            {config?.label || role}
          </Tag>
        )
      },
    },
    {
      title: 'Created At',
      dataIndex: 'CreatedAt',
      key: 'CreatedAt',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Last Login',
      dataIndex: 'LastLogin',
      key: 'LastLogin',
      width: 180,
      render: (date?: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={!isAdmin}
            />
          </Tooltip>
          <Popconfirm
            title="Delete user?"
            description={`Are you sure you want to delete ${record.Username}?`}
            onConfirm={() => handleDelete(record.UserId)}
            okText="Yes"
            cancelText="No"
            disabled={record.UserId === currentUser?.UserId || !isAdmin}
          >
            <Tooltip title={record.UserId === currentUser?.UserId ? 'Cannot delete yourself' : 'Delete'}>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                disabled={record.UserId === currentUser?.UserId || !isAdmin}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // If not admin, show access denied
  if (!isAdmin) {
    return (
      <Card>
        <Alert
          message="Access Denied"
          description="You don't have permission to access user management. Only administrators can manage users."
          type="error"
          showIcon
        />
      </Card>
    )
  }

  return (
    <div>
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              User Management
            </Title>
            <Badge count={filteredUsers.length} showZero color="blue" />
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadUsers}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
              Create User
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            placeholder="Search users..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
          <Select placeholder="Status" value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}>
            <Option value="all">All</Option>
            <Option value="active">Active</Option>
            <Option value="inactive">Inactive</Option>
          </Select>
          <Select placeholder="Role" value={roleFilter} onChange={setRoleFilter} style={{ width: 120 }} allowClear>
            <Option value="admin">Admin</Option>
            <Option value="analyst">Analyst</Option>
            <Option value="viewer">Viewer</Option>
          </Select>
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={filteredUsers}
          rowKey="UserId"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} users`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Create New User"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        onOk={() => createForm.submit()}
        width={600}
        okText="Create"
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            role: 'viewer',
          }}
        >
          <Form.Item
            name="username"
            label="Username"
            rules={[
              { required: true, message: 'Please enter username' },
              { min: 3, message: 'Username must be at least 3 characters' },
              { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Username can only contain letters, numbers, _ and -' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="username" />
          </Form.Item>

          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 8, message: 'Password must be at least 8 characters' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="********" />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="Confirm Password"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Please confirm password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('Passwords do not match'))
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="********" />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter full name' }]}
          >
            <Input placeholder="John Doe" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: 'Please enter a valid email' }]}
          >
            <Input prefix={<MailOutlined />} placeholder="user@example.com" />
          </Form.Item>

          <Form.Item name="role" label="Role" rules={[{ required: true, message: 'Please select role' }]}>
            <Select>
              <Option value="admin">
                <Space>
                  <CrownOutlined />
                  Admin - Full access
                </Space>
              </Option>
              <Option value="analyst">
                <Space>
                  <SafetyOutlined />
                  Analyst - Manage alerts & incidents
                </Space>
              </Option>
              <Option value="viewer">
                <Space>
                  <EyeOutlined />
                  Viewer - Read only
                </Space>
              </Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="Edit User"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          setSelectedUser(null)
          editForm.resetFields()
        }}
        onOk={() => editForm.submit()}
        width={600}
        okText="Update"
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="username"
            label="Username"
            rules={[
              { required: true, message: 'Please enter username' },
              { min: 3, message: 'Username must be at least 3 characters' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="username" disabled />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter full name' }]}
          >
            <Input placeholder="John Doe" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: 'Please enter a valid email' }]}
          >
            <Input prefix={<MailOutlined />} placeholder="user@example.com" />
          </Form.Item>

          <Form.Item name="role" label="Role" rules={[{ required: true, message: 'Please select role' }]}>
            <Select disabled={selectedUser?.UserId === currentUser?.UserId}>
              <Option value="admin">
                <Space>
                  <CrownOutlined />
                  Admin
                </Space>
              </Option>
              <Option value="analyst">
                <Space>
                  <SafetyOutlined />
                  Analyst
                </Space>
              </Option>
              <Option value="viewer">
                <Space>
                  <EyeOutlined />
                  Viewer
                </Space>
              </Option>
            </Select>
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch disabled={selectedUser?.UserId === currentUser?.UserId} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
