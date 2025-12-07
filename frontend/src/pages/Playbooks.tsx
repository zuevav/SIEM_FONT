/**
 * SOAR Playbooks Management Page
 * Create, edit, and manage automated response playbooks
 */

import React, { useState, useEffect } from 'react'
import {
  Table, Button, Tag, Space, Modal, Form, Input, Switch, Select,
  message, Popconfirm, Typography, Card, Statistic, Row, Col, Divider
} from 'antd'
import {
  PlayCircleOutlined, PlusOutlined, EditOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
  RobotOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import apiService from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input

interface Playbook {
  playbook_id: number
  name: string
  description?: string
  trigger_on_severity?: number[]
  trigger_on_mitre_tactic?: string[]
  action_ids?: number[]
  requires_approval: boolean
  is_enabled: boolean
  execution_count: number
  success_count: number
  failure_count: number
  created_at: string
  updated_at?: string
}

interface PlaybookStats {
  total_playbooks: number
  enabled_playbooks: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  pending_approvals: number
  avg_execution_time_seconds?: number
}

const Playbooks: React.FC = () => {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([])
  const [stats, setStats] = useState<PlaybookStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingPlaybook, setEditingPlaybook] = useState<Playbook | null>(null)
  const [form] = Form.useForm()
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  useEffect(() => {
    loadPlaybooks()
    loadStats()
  }, [pagination.current])

  const loadPlaybooks = async () => {
    try {
      setLoading(true)
      const response = await apiService.listPlaybooks({
        page: pagination.current,
        page_size: pagination.pageSize
      })
      setPlaybooks(response.items)
      setPagination({ ...pagination, total: response.total })
    } catch (error) {
      console.error('Failed to load playbooks:', error)
      message.error('Не удалось загрузить playbooks')
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const response = await apiService.getPlaybookStats()
      setStats(response)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const handleCreate = () => {
    setEditingPlaybook(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (playbook: Playbook) => {
    setEditingPlaybook(playbook)
    form.setFieldsValue(playbook)
    setModalVisible(true)
  }

  const handleDelete = async (playbookId: number) => {
    try {
      await apiService.deletePlaybook(playbookId)
      message.success('Playbook удалён')
      loadPlaybooks()
      loadStats()
    } catch (error) {
      console.error('Failed to delete playbook:', error)
      message.error('Не удалось удалить playbook')
    }
  }

  const handleExecute = async (playbookId: number) => {
    try {
      await apiService.executePlaybook({ playbook_id: playbookId })
      message.success('Playbook запущен')
      loadPlaybooks()
    } catch (error) {
      console.error('Failed to execute playbook:', error)
      message.error('Не удалось запустить playbook')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingPlaybook) {
        await apiService.updatePlaybook(editingPlaybook.playbook_id, values)
        message.success('Playbook обновлён')
      } else {
        await apiService.createPlaybook(values)
        message.success('Playbook создан')
      }
      setModalVisible(false)
      loadPlaybooks()
      loadStats()
    } catch (error) {
      console.error('Failed to save playbook:', error)
      message.error('Не удалось сохранить playbook')
    }
  }

  const columns: ColumnsType<Playbook> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      render: (text: string, record: Playbook) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.description}
            </Text>
          )}
        </div>
      )
    },
    {
      title: 'Триггеры',
      key: 'triggers',
      width: 200,
      render: (_, record: Playbook) => (
        <Space direction="vertical" size="small">
          {record.trigger_on_severity && record.trigger_on_severity.length > 0 && (
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>Severity: </Text>
              {record.trigger_on_severity.map((sev) => (
                <Tag key={sev} color={sev >= 4 ? 'red' : sev >= 3 ? 'orange' : 'blue'}>
                  {sev}
                </Tag>
              ))}
            </div>
          )}
          {record.trigger_on_mitre_tactic && record.trigger_on_mitre_tactic.length > 0 && (
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>MITRE: </Text>
              {record.trigger_on_mitre_tactic.slice(0, 2).map((tactic) => (
                <Tag key={tactic} color="purple">
                  {tactic}
                </Tag>
              ))}
              {record.trigger_on_mitre_tactic.length > 2 && (
                <Tag>+{record.trigger_on_mitre_tactic.length - 2}</Tag>
              )}
            </div>
          )}
        </Space>
      )
    },
    {
      title: 'Действия',
      dataIndex: 'action_ids',
      key: 'action_ids',
      width: 100,
      render: (actions: number[]) => (
        <Tag color="cyan">{actions?.length || 0} действий</Tag>
      )
    },
    {
      title: 'Статистика',
      key: 'stats',
      width: 150,
      render: (_, record: Playbook) => (
        <Space direction="vertical" size="small">
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            <Text style={{ marginLeft: 8, fontSize: '12px' }}>
              {record.success_count} / {record.execution_count}
            </Text>
          </div>
          {record.failure_count > 0 && (
            <div>
              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
              <Text style={{ marginLeft: 8, fontSize: '12px' }}>{record.failure_count}</Text>
            </div>
          )}
        </Space>
      )
    },
    {
      title: 'Статус',
      key: 'status',
      width: 120,
      render: (_, record: Playbook) => (
        <Space direction="vertical" size="small">
          <Tag color={record.is_enabled ? 'green' : 'default'}>
            {record.is_enabled ? 'Включен' : 'Отключен'}
          </Tag>
          {record.requires_approval && (
            <Tag color="orange" icon={<ClockCircleOutlined />}>
              Требует одобрения
            </Tag>
          )}
        </Space>
      )
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record: Playbook) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.playbook_id)}
            disabled={!record.is_enabled}
          >
            Запустить
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Удалить playbook?"
            onConfirm={() => handleDelete(record.playbook_id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <RobotOutlined /> SOAR Playbooks
      </Title>

      {/* Statistics Cards */}
      {stats && (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Всего Playbooks"
                  value={stats.total_playbooks}
                  prefix={<RobotOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Активных"
                  value={stats.enabled_playbooks}
                  valueStyle={{ color: '#3f8600' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Успешных выполнений"
                  value={stats.successful_executions}
                  suffix={`/ ${stats.total_executions}`}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Ожидают одобрения"
                  value={stats.pending_approvals}
                  valueStyle={{ color: stats.pending_approvals > 0 ? '#fa8c16' : undefined }}
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Divider />
        </>
      )}

      {/* Actions */}
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          Создать Playbook
        </Button>
      </div>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={playbooks}
        loading={loading}
        rowKey="playbook_id"
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `Всего: ${total}`,
          onChange: (page, pageSize) => {
            setPagination({ ...pagination, current: page, pageSize: pageSize || 20 })
          }
        }}
        scroll={{ x: 1200 }}
      />

      {/* Create/Edit Modal */}
      <Modal
        title={editingPlaybook ? 'Редактировать Playbook' : 'Создать Playbook'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input placeholder="Например: Block malicious IP" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Описание"
          >
            <TextArea rows={3} placeholder="Описание playbook" />
          </Form.Item>

          <Form.Item
            name="trigger_on_severity"
            label="Триггер: Severity (уровни критичности)"
          >
            <Select
              mode="multiple"
              placeholder="Выберите уровни"
              options={[
                { label: '1 - Low', value: 1 },
                { label: '2 - Medium', value: 2 },
                { label: '3 - High', value: 3 },
                { label: '4 - Critical', value: 4 },
                { label: '5 - Emergency', value: 5 }
              ]}
            />
          </Form.Item>

          <Form.Item
            name="trigger_on_mitre_tactic"
            label="Триггер: MITRE ATT&CK Tactics"
          >
            <Select
              mode="tags"
              placeholder="Введите тактики (Initial Access, Execution, ...)"
            />
          </Form.Item>

          <Form.Item
            name="action_ids"
            label="Action IDs"
            tooltip="ID действий через запятую (создайте действия на странице Actions)"
          >
            <Select
              mode="tags"
              placeholder="Введите ID действий"
            />
          </Form.Item>

          <Form.Item
            name="requires_approval"
            label="Требует одобрения"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="is_enabled"
            label="Включен"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Playbooks
