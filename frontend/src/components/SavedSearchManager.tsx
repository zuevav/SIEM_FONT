/**
 * Saved Search Manager Component
 * Allows users to save, load, and delete search filters
 */

import React, { useState, useEffect } from 'react'
import { Button, Select, Modal, Form, Input, Switch, Space, message, Popconfirm } from 'antd'
import { SaveOutlined, FolderOpenOutlined, DeleteOutlined, ShareAltOutlined } from '@ant-design/icons'
import apiService from '@/services/api'

const { Option } = Select
const { TextArea } = Input

interface SavedSearch {
  id: number
  name: string
  description?: string
  search_type: string
  filters: Record<string, any>
  user_id: number
  is_shared: boolean
  created_at: string
  updated_at: string
}

interface SavedSearchManagerProps {
  searchType: 'events' | 'alerts' | 'incidents'
  currentFilters: Record<string, any>
  onLoadSearch: (filters: Record<string, any>) => void
}

const SavedSearchManager: React.FC<SavedSearchManagerProps> = ({
  searchType,
  currentFilters,
  onLoadSearch,
}) => {
  const [searches, setSearches] = useState<SavedSearch[]>([])
  const [selectedSearchId, setSelectedSearchId] = useState<number | undefined>()
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    loadSavedSearches()
  }, [searchType])

  const loadSavedSearches = async () => {
    try {
      const response = await apiService.getSavedSearches({
        search_type: searchType,
        include_shared: true,
      })
      setSearches(response.items)
    } catch (error) {
      console.error('Failed to load saved searches:', error)
    }
  }

  const handleLoadSearch = async (searchId: number) => {
    try {
      const search = await apiService.getSavedSearch(searchId)
      setSelectedSearchId(searchId)
      onLoadSearch(search.filters)
      message.success(`Поиск "${search.name}" загружен`)
    } catch (error) {
      message.error('Не удалось загрузить сохраненный поиск')
    }
  }

  const handleSaveSearch = async (values: any) => {
    setLoading(true)
    try {
      await apiService.createSavedSearch({
        name: values.name,
        description: values.description,
        search_type: searchType,
        filters: currentFilters,
        is_shared: values.is_shared || false,
      })

      message.success('Поиск сохранен успешно')
      setSaveModalVisible(false)
      form.resetFields()
      await loadSavedSearches()
    } catch (error: any) {
      if (error.response?.status === 409) {
        message.error('Поиск с таким именем уже существует')
      } else {
        message.error('Не удалось сохранить поиск')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSearch = async (searchId: number) => {
    try {
      await apiService.deleteSavedSearch(searchId)
      message.success('Поиск удален')
      if (selectedSearchId === searchId) {
        setSelectedSearchId(undefined)
      }
      await loadSavedSearches()
    } catch (error: any) {
      if (error.response?.status === 403) {
        message.error('Вы можете удалять только свои поиски')
      } else {
        message.error('Не удалось удалить поиск')
      }
    }
  }

  const handleOpenSaveModal = () => {
    form.resetFields()
    setSaveModalVisible(true)
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <Space>
        <Select
          style={{ width: 250 }}
          placeholder="Выберите сохраненный поиск"
          allowClear
          value={selectedSearchId}
          onChange={handleLoadSearch}
          suffixIcon={<FolderOpenOutlined />}
        >
          {searches.map((search) => (
            <Option key={search.id} value={search.id}>
              {search.name}
              {search.is_shared && <ShareAltOutlined style={{ marginLeft: 8, color: '#1890ff' }} />}
            </Option>
          ))}
        </Select>

        <Button icon={<SaveOutlined />} onClick={handleOpenSaveModal}>
          Сохранить поиск
        </Button>

        {selectedSearchId && (
          <Popconfirm
            title="Удалить этот поиск?"
            description="Это действие нельзя отменить."
            onConfirm={() => handleDeleteSearch(selectedSearchId)}
            okText="Да"
            cancelText="Нет"
          >
            <Button icon={<DeleteOutlined />} danger>
              Удалить
            </Button>
          </Popconfirm>
        )}
      </Space>

      <Modal
        title="Сохранить текущий поиск"
        open={saveModalVisible}
        onOk={() => form.submit()}
        onCancel={() => setSaveModalVisible(false)}
        confirmLoading={loading}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical" onFinish={handleSaveSearch}>
          <Form.Item
            name="name"
            label="Название поиска"
            rules={[{ required: true, message: 'Введите название поиска' }]}
          >
            <Input placeholder="Например: Критические события за последний день" />
          </Form.Item>

          <Form.Item name="description" label="Описание (необязательно)">
            <TextArea rows={3} placeholder="Краткое описание того, что ищет этот запрос" />
          </Form.Item>

          <Form.Item
            name="is_shared"
            label="Поделиться с другими пользователями"
            valuePropName="checked"
            initialValue={false}
          >
            <Switch />
          </Form.Item>

          <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
            <strong>Текущие фильтры:</strong>
            <pre style={{ marginTop: 8, fontSize: 12 }}>
              {JSON.stringify(currentFilters, null, 2)}
            </pre>
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default SavedSearchManager
