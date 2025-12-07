/**
 * Documentation Page
 * Displays system documentation files from docs/ folder
 */

import React, { useState, useEffect } from 'react'
import { Card, List, Typography, Spin, Alert, Divider, Space } from 'antd'
import { FileTextOutlined, BookOutlined } from '@ant-design/icons'
import apiService from '@/services/api'

const { Title, Paragraph, Text } = Typography

interface Doc {
  filename: string
  title: string
  path: string
}

const Documentation: React.FC = () => {
  const [docs, setDocs] = useState<Doc[]>([])
  const [selectedDoc, setSelectedDoc] = useState<{ filename: string; content: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDocsList()
  }, [])

  const loadDocsList = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiService.listDocumentation()
      setDocs(response.docs)
    } catch (err: any) {
      console.error('Failed to load documentation list:', err)
      setError('Не удалось загрузить список документации')
    } finally {
      setLoading(false)
    }
  }

  const loadDocument = async (filename: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiService.getDocumentation(filename)
      setSelectedDoc({ filename: response.filename, content: response.content })
    } catch (err: any) {
      console.error('Failed to load document:', err)
      setError('Не удалось загрузить документ')
    } finally {
      setLoading(false)
    }
  }

  const renderMarkdown = (content: string) => {
    // Simple markdown rendering - converts basic markdown to JSX
    // For a production app, use a library like react-markdown
    return (
      <div
        style={{
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          fontSize: '14px',
          lineHeight: '1.6',
          padding: '20px',
          backgroundColor: '#f5f5f5',
          borderRadius: '4px',
          maxHeight: '70vh',
          overflow: 'auto',
        }}
      >
        {content}
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <BookOutlined /> Документация
      </Title>
      <Paragraph>
        Руководства по установке, настройке и использованию SIEM системы
      </Paragraph>

      <Divider />

      {error && (
        <Alert
          message="Ошибка"
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <div style={{ display: 'flex', gap: '24px' }}>
        {/* Document List */}
        <Card
          title="Доступные документы"
          style={{ width: '350px', height: 'fit-content' }}
          loading={loading && !selectedDoc}
        >
          <List
            dataSource={docs}
            renderItem={(doc) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => loadDocument(doc.filename)}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ fontSize: '20px', color: '#1890ff' }} />}
                  title={doc.title}
                  description={
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {doc.filename}
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        </Card>

        {/* Document Content */}
        <Card
          title={
            selectedDoc ? (
              <Space>
                <FileTextOutlined />
                <span>{selectedDoc.filename}</span>
              </Space>
            ) : (
              'Выберите документ'
            )
          }
          style={{ flex: 1 }}
        >
          {loading && selectedDoc && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Spin size="large" />
            </div>
          )}

          {!loading && !selectedDoc && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <FileTextOutlined style={{ fontSize: '64px', color: '#d9d9d9' }} />
              <Paragraph type="secondary" style={{ marginTop: 16 }}>
                Выберите документ из списка слева для просмотра
              </Paragraph>
            </div>
          )}

          {!loading && selectedDoc && renderMarkdown(selectedDoc.content)}
        </Card>
      </div>
    </div>
  )
}

export default Documentation
