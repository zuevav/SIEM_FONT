import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'
import { apiService } from '@/services/api'

// ============================================================================
// Auth Store
// ============================================================================

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loadUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiService.login({ username, password })
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Ошибка входа',
            isLoading: false,
          })
          throw error
        }
      },

      logout: async () => {
        try {
          await apiService.logout()
        } finally {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          })
        }
      },

      loadUser: async () => {
        const token = apiService.getToken()
        if (!token) {
          set({ isAuthenticated: false })
          return
        }

        set({ isLoading: true })
        try {
          const user = await apiService.getCurrentUser()
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'siem-auth',
      partialize: (state) => ({
        token: state.token,
      }),
    }
  )
)

// ============================================================================
// Dashboard Store
// ============================================================================

interface DashboardState {
  refreshInterval: number
  autoRefresh: boolean

  setRefreshInterval: (interval: number) => void
  setAutoRefresh: (enabled: boolean) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  refreshInterval: 30000, // 30 seconds
  autoRefresh: true,

  setRefreshInterval: (interval) => set({ refreshInterval: interval }),
  setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
}))

// ============================================================================
// Notifications Store
// ============================================================================

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: Date
  read: boolean
}

interface NotificationsState {
  notifications: Notification[]
  unreadCount: number

  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  removeNotification: (id: string) => void
  clearAll: () => void
}

export const useNotificationsStore = create<NotificationsState>((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (notification) => {
    const newNotification: Notification = {
      ...notification,
      id: `notif-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      read: false,
    }
    set((state) => ({
      notifications: [newNotification, ...state.notifications].slice(0, 50), // Keep last 50
      unreadCount: state.unreadCount + 1,
    }))
  },

  markAsRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  removeNotification: (id) =>
    set((state) => {
      const notification = state.notifications.find((n) => n.id === id)
      return {
        notifications: state.notifications.filter((n) => n.id !== id),
        unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
      }
    }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),
}))

// ============================================================================
// Theme Store
// ============================================================================

interface ThemeState {
  isDark: boolean
  toggleTheme: () => void
  setTheme: (dark: boolean) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      isDark: true, // Default dark theme for SIEM
      toggleTheme: () => set((state) => ({ isDark: !state.isDark })),
      setTheme: (dark) => set({ isDark: dark }),
    }),
    {
      name: 'siem-theme',
    }
  )
)
