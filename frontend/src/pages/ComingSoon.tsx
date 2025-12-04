import { Card, Result, Button, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { RocketOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

interface ComingSoonProps {
  title: string
  description?: string
}

export default function ComingSoon({ title, description }: ComingSoonProps) {
  const navigate = useNavigate()

  return (
    <Card>
      <Result
        icon={<RocketOutlined style={{ fontSize: 72, color: '#1890ff' }} />}
        title={<Title level={3}>{title}</Title>}
        subTitle={
          <Text type="secondary">
            {description || 'Этот раздел находится в разработке. Скоро здесь появится новый функционал!'}
          </Text>
        }
        extra={[
          <Button type="primary" key="dashboard" onClick={() => navigate('/')}>
            На главную
          </Button>,
        ]}
      />
    </Card>
  )
}
