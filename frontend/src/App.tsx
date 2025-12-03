import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import './App.css'

function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <div className="app">
        <h1>SIEM System</h1>
        <p>Frontend в разработке...</p>
        <p>Версия: 0.9.0 (Beta)</p>
      </div>
    </ConfigProvider>
  )
}

export default App
