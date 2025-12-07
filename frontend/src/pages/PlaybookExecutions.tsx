/**
 * SOAR Playbook Executions Page
 * View and manage playbook execution history
 */

import React, { useState, useEffect } from 'react'
import {
  Table, Button, Tag, Space, Modal, Typography, Card, Select, Descriptions,
  message, Popconfirm, Timeline
} from 'antd'
import {
  PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, StopOutlined, EyeOutlined, CheckOutlined,
  WarningOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import apiService from '@/services/api'

const { Title, Text } = Typography

interface Execution {
  execution_id: number
  playbook_id: number
  alert_id?: number
  incident_id?: number
  status: string
  started_at: string
  completed_at?: string
  execution_log?: any
}

const PlaybookExecutions: React.FC = () => {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(false)
  const [detailsVisible, setDetailsVisible] = useState(false)
  const [approvalVisible, setApprovalVisible] = useState(false)
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  useEffect(() => {
    loadExecutions()
  }, [pagination.current, statusFilter])

  const loadExecutions = async () => {
    try {
      setLoading(true)
      const response = await apiService.listExecutions({
        page: pagination.current,
        page_size: pagination.pageSize,
        status: statusFilter
      })
      setExecutions(response.items)
      setPagination({ ...pagination, total: response.total })
    } catch (error) {
      console.error('Failed to load executions:', error)
      message.error('Не удалось загрузить выполнения')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (executionId: number, approved: boolean) => {
    try {
      await apiService.approveExecution(executionId, approved)
      message.success(approved ? 'Выполнение одобрено' : 'Выполнение отклонено')
      setApprovalVisible(false)
      loadExecutions()
    } catch (error) {
      console.error('Failed to approve execution:', error)
      message.error('Не удалось обработать запрос')
    }
  }

  const handleCancel = async (executionId: number) => {
    try {
      await apiService.cancelExecution(executionId)
      message.success('Выполнение отменено')
      loadExecutions()
    } catch (error) {
      console.error('Failed to cancel execution:', error)
      message.error('Не удалось отменить выполнение')
    }
  }

  const showDetails = async (execution: Execution) => {
    try {
      const details = await apiService.getExecution(execution.execution_id)
      setSelectedExecution(details)
      setDetailsVisible(true)
    } catch (error) {
      console.error('Failed to load execution details:', error)
      message.error('Не удалось загрузить детали')
    }
  }

  const showApproval = (execution: Execution) => {
    setSelectedExecution(execution)
    setApprovalVisible(true)
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; icon: any; text: string }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: 'Ожидает' },
      pending_approval: { color: 'orange', icon: <WarningOutlined />, text: 'Ждёт одобрения' },
      running: { color: 'blue', icon: <PlayCircleOutlined />, text: 'Выполняется' },
      completed: { color: 'green', icon: <CheckCircleOutlined />, text: 'Завершено' },
      failed: { color: 'red', icon: <CloseCircleOutlined />, text: 'Ошибка' },
      partial: { color: 'orange', icon: <WarningOutlined />, text: 'Частично' },
      cancelled: { color: 'default', icon: <StopOutlined />, text: 'Отменено' }
    }
    const config = statusMap[status] || statusMap.pending
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    )
  }

  const columns: ColumnsType<Execution> = [
    {
      title: 'ID',
      dataIndex: 'execution_id',
      key: 'execution_id',
      width: 80
    },
    {
      title: 'Playbook ID',
      dataIndex: 'playbook_id',
      key: 'playbook_id',
      width: 120
    },
    {
      title: 'Триггер',
      key: 'trigger',
      width: 150,
      render: (_, record: Execution) => (
        <Space direction="vertical" size="small">
          {record.alert_id && <Tag color="red">Alert #{record.alert_id}</Tag>}
          {record.incident_id && <Tag color="orange">Incident #{record.incident_id}</Tag>}
          {!record.alert_id && !record.incident_id && <Tag>Вручную</Tag>}
        </Space>
      )
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: 'Начало',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (time: string) => dayjs(time).format('DD.MM.YYYY HH:mm:ss')
    },
    {
      title: 'Завершение',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (time?: string) => time ? dayjs(time).format('DD.MM.YYYY HH:mm:ss') : '-'
    },
    {
      title: 'Длительность',
      key: 'duration',
      width: 120,
      render: (_, record: Execution) => {
        if (!record.completed_at) return '-'
        const duration = dayjs(record.completed_at).diff(dayjs(record.started_at), 'second')
        return `${duration}s`
      }
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 250,
      fixed: 'right',
      render: (_, record: Execution) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => showDetails(record)}
          >
            Детали
          </Button>
          {record.status === 'pending_approval' && (
            <Button
              size="small"
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => showApproval(record)}
            >
              Одобрить
            </Button>
          )}
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title="Отменить выполнение?"
              onConfirm={() => handleCancel(record.execution_id)}
              okText="Да"
              cancelText="Нет"
            >
              <Button size="small" danger icon={<StopOutlined />}>
                Отменить
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <PlayCircleOutlined /> Выполнения Playbooks
      </Title>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text>Статус:</Text>
          <Select
            style={{ width: 200 }}
            placeholder="Все статусы"
            allowClear
            value={statusFilter}
            onChange={(value) => {
              setStatusFilter(value)
              setPagination({ ...pagination, current: 1 })
            }}
            options={[
              { label: 'Ожидает', value: 'pending' },
              { label: 'Ждёт одобрения', value: 'pending_approval' },
              { label: 'Выполняется', value: 'running' },
              { label: 'Завершено', value: 'completed' },
              { label: 'Ошибка', value: 'failed' },
              { label: 'Частично', value: 'partial' },
              { label: 'Отменено', value: 'cancelled' }
            ]}
          />
        </Space>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={executions}
        loading={loading}
        rowKey="execution_id"
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

      {/* Details Modal */}
      <Modal
        title={`Execution #${selectedExecution?.execution_id}`}
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            Закрыть
          </Button>
        ]}
        width={900}
      >
        {selectedExecution && (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Execution ID">
                {selectedExecution.execution_id}
              </Descriptions.Item>
              <Descriptions.Item label="Playbook ID">
                {selectedExecution.playbook_id}
              </Descriptions.Item>
              <Descriptions.Item label="Alert ID">
                {selectedExecution.alert_id || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Incident ID">
                {selectedExecution.incident_id || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Статус">
                {getStatusTag(selectedExecution.status)}
              </Descriptions.Item>
              <Descriptions.Item label="Начало">
                {dayjs(selectedExecution.started_at).format('DD.MM.YYYY HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Завершение" span={2}>
                {selectedExecution.completed_at
                  ? dayjs(selectedExecution.completed_at).format('DD.MM.YYYY HH:mm:ss')
                  : '-'}
              </Descriptions.Item>
            </Descriptions>

            {selectedExecution.execution_log?.actions && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>Лог выполнения</Title>
                <Timeline
                  items={selectedExecution.execution_log.actions.map((action: any) => ({
                    color: action.status === 'completed' ? 'green' : action.status === 'failed' ? 'red' : 'blue',
                    children: (
                      <div>
                        <Text strong>{action.action_name}</Text>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          Type: {action.action_type} | Status: {action.status}
                        </div>
                        {action.error && (
                          <div style={{ fontSize: '12px', color: '#ff4d4f' }}>
                            Error: {action.error}
                          </div>
                        )}
                      </div>
                    )
                  }))}
                />
              </div>
            )}
          </>
        )}
      </Modal>

      {/* Approval Modal */}
      <Modal
        title="Одобрить выполнение?"
        open={approvalVisible}
        onCancel={() => setApprovalVisible(false)}
        footer={[
          <Button key="reject" danger onClick={() => selectedExecution && handleApprove(selectedExecution.execution_id, false)}>
            Отклонить
          </Button>,
          <Button key="approve" type="primary" onClick={() => selectedExecution && handleApprove(selectedExecution.execution_id, true)}>
            Одобрить
          </Button>
        ]}
      >
        {selectedExecution && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Execution ID">
              {selectedExecution.execution_id}
            </Descriptions.Item>
            <Descriptions.Item label="Playbook ID">
              {selectedExecution.playbook_id}
            </Descriptions.Item>
            {selectedExecution.alert_id && (
              <Descriptions.Item label="Alert ID">
                {selectedExecution.alert_id}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default PlaybookExecutions
