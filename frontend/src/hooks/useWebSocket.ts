import { useEffect, useCallback, useRef } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { useAuthStore, useNotificationsStore } from '@/store'
import type { WebSocketMessage, Event, Alert } from '@/types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

interface UseWebSocketOptions {
  onEvent?: (event: Event) => void
  onAlert?: (alert: Alert) => void
  onStatistics?: (stats: any) => void
  enabled?: boolean
}

export function useSiemWebSocket(options: UseWebSocketOptions = {}) {
  const { onEvent, onAlert, onStatistics, enabled = true } = options
  const token = useAuthStore((state) => state.token)
  const addNotification = useNotificationsStore((state) => state.addNotification)

  // Build WebSocket URL with token
  const socketUrl = token ? `${WS_URL}?token=${token}` : null

  const { sendMessage, lastMessage, readyState } = useWebSocket(
    socketUrl,
    {
      shouldReconnect: () => enabled && !!token,
      reconnectAttempts: 10,
      reconnectInterval: (attemptNumber) => Math.min(1000 * 2 ** attemptNumber, 30000),
      onOpen: () => {
        console.log('[WebSocket] Connected')
      },
      onClose: () => {
        console.log('[WebSocket] Disconnected')
      },
      onError: (event) => {
        console.error('[WebSocket] Error:', event)
      },
    },
    enabled && !!token
  )

  // Handle incoming messages
  useEffect(() => {
    if (!lastMessage) return

    try {
      const message: WebSocketMessage = JSON.parse(lastMessage.data)

      switch (message.type) {
        case 'event':
          if (message.action === 'created' && onEvent) {
            onEvent(message.data)
          }
          break

        case 'alert':
          if (message.action === 'created') {
            const alert = message.data
            if (onAlert) {
              onAlert(alert)
            }
            // Show notification for new alerts
            if (alert.Severity >= 3) {
              addNotification({
                type: 'error',
                title: `Новый алерт: ${alert.Title}`,
                message: alert.Description || 'Требуется внимание',
              })
            }
          }
          break

        case 'statistics':
          if (onStatistics) {
            onStatistics(message.data)
          }
          break

        case 'notification':
          addNotification({
            type: message.data.type || 'info',
            title: message.data.title,
            message: message.data.message,
          })
          break

        case 'connection':
          console.log('[WebSocket] Connection info:', message.data)
          break

        default:
          console.log('[WebSocket] Unknown message type:', message.type)
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error)
    }
  }, [lastMessage, onEvent, onAlert, onStatistics, addNotification])

  // Subscribe to specific topics
  const subscribe = useCallback(
    (topics: string[]) => {
      if (readyState === ReadyState.OPEN) {
        sendMessage(
          JSON.stringify({
            action: 'subscribe',
            topics,
          })
        )
      }
    },
    [sendMessage, readyState]
  )

  // Unsubscribe from topics
  const unsubscribe = useCallback(
    (topics: string[]) => {
      if (readyState === ReadyState.OPEN) {
        sendMessage(
          JSON.stringify({
            action: 'unsubscribe',
            topics,
          })
        )
      }
    },
    [sendMessage, readyState]
  )

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Подключение...',
    [ReadyState.OPEN]: 'Подключено',
    [ReadyState.CLOSING]: 'Закрытие...',
    [ReadyState.CLOSED]: 'Отключено',
    [ReadyState.UNINSTANTIATED]: 'Не инициализировано',
  }[readyState]

  return {
    sendMessage,
    subscribe,
    unsubscribe,
    readyState,
    connectionStatus,
    isConnected: readyState === ReadyState.OPEN,
  }
}
