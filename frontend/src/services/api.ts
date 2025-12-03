/**
 * API Service for SIEM Backend
 * Uses axios for HTTP requests with automatic JWT token handling
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'
import type {
  LoginRequest,
  LoginResponse,
  User,
  Event,
  EventFilter,
  EventStatistics,
  Alert,
  AlertFilter,
  Incident,
  IncidentFilter,
  Agent,
  AgentStatistics,
  DashboardStats,
  PaginatedResponse,
  APIResponse,
} from '@/types'

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'
const TOKEN_KEY = 'siem_token'

class APIService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor - add JWT token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          this.clearToken()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // ============================================================================
  // Token Management
  // ============================================================================

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  }

  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token)
  }

  clearToken(): void {
    localStorage.removeItem(TOKEN_KEY)
  }

  // ============================================================================
  // Authentication API
  // ============================================================================

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', credentials)
    const { access_token } = response.data
    this.setToken(access_token)
    return response.data
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } finally {
      this.clearToken()
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me')
    return response.data
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.client.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  // ============================================================================
  // Events API
  // ============================================================================

  async getEvents(filter: EventFilter = {}): Promise<PaginatedResponse<Event>> {
    const response = await this.client.get<PaginatedResponse<Event>>('/events', {
      params: filter,
    })
    return response.data
  }

  async getEvent(eventId: number): Promise<Event> {
    const response = await this.client.get<Event>(`/events/${eventId}`)
    return response.data
  }

  async getEventStatistics(): Promise<EventStatistics> {
    const response = await this.client.get<EventStatistics>('/events/stats/dashboard')
    return response.data
  }

  async exportEvents(filter: EventFilter = {}): Promise<Blob> {
    const response = await this.client.post('/events/export', filter, {
      responseType: 'blob',
    })
    return response.data
  }

  // ============================================================================
  // Alerts API
  // ============================================================================

  async getAlerts(filter: AlertFilter = {}): Promise<PaginatedResponse<Alert>> {
    const response = await this.client.get<PaginatedResponse<Alert>>('/alerts', {
      params: filter,
    })
    return response.data
  }

  async getAlert(alertId: number): Promise<Alert> {
    const response = await this.client.get<Alert>(`/alerts/${alertId}`)
    return response.data
  }

  async acknowledgeAlert(alertId: number): Promise<Alert> {
    const response = await this.client.post<Alert>(`/alerts/${alertId}/acknowledge`)
    return response.data
  }

  async resolveAlert(alertId: number, resolution: 'resolved' | 'false_positive', comment?: string): Promise<Alert> {
    const response = await this.client.post<Alert>(`/alerts/${alertId}/resolve`, {
      resolution,
      comment,
    })
    return response.data
  }

  async assignAlert(alertId: number, userId: number): Promise<Alert> {
    const response = await this.client.post<Alert>(`/alerts/${alertId}/assign`, {
      user_id: userId,
    })
    return response.data
  }

  async addAlertComment(alertId: number, comment: string): Promise<Alert> {
    const response = await this.client.post<Alert>(`/alerts/${alertId}/comment`, {
      comment,
    })
    return response.data
  }

  // ============================================================================
  // Incidents API
  // ============================================================================

  async getIncidents(filter: IncidentFilter = {}): Promise<PaginatedResponse<Incident>> {
    const response = await this.client.get<PaginatedResponse<Incident>>('/incidents', {
      params: filter,
    })
    return response.data
  }

  async getIncident(incidentId: number): Promise<Incident> {
    const response = await this.client.get<Incident>(`/incidents/${incidentId}`)
    return response.data
  }

  async createIncident(data: {
    title: string
    description?: string
    severity: number
    priority: number
    alert_ids?: number[]
  }): Promise<Incident> {
    const response = await this.client.post<Incident>('/incidents', data)
    return response.data
  }

  async updateIncident(incidentId: number, data: Partial<Incident>): Promise<Incident> {
    const response = await this.client.patch<Incident>(`/incidents/${incidentId}`, data)
    return response.data
  }

  async addIncidentWorkLog(incidentId: number, entry: string): Promise<Incident> {
    const response = await this.client.post<Incident>(`/incidents/${incidentId}/worklog`, {
      entry,
    })
    return response.data
  }

  async containIncident(incidentId: number, actions: string): Promise<Incident> {
    const response = await this.client.post<Incident>(`/incidents/${incidentId}/containment`, {
      actions,
    })
    return response.data
  }

  async remediateIncident(incidentId: number, actions: string): Promise<Incident> {
    const response = await this.client.post<Incident>(`/incidents/${incidentId}/remediation`, {
      actions,
    })
    return response.data
  }

  async closeIncident(incidentId: number, lessonsLearned?: string): Promise<Incident> {
    const response = await this.client.post<Incident>(`/incidents/${incidentId}/close`, {
      lessons_learned: lessonsLearned,
    })
    return response.data
  }

  async getIncidentTimeline(incidentId: number): Promise<any[]> {
    const response = await this.client.get(`/incidents/${incidentId}/timeline`)
    return response.data
  }

  // ============================================================================
  // Agents API
  // ============================================================================

  async getAgents(params?: { status?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<Agent>> {
    const response = await this.client.get<PaginatedResponse<Agent>>('/agents', {
      params,
    })
    return response.data
  }

  async getAgent(agentId: string): Promise<Agent> {
    const response = await this.client.get<Agent>(`/agents/${agentId}`)
    return response.data
  }

  async getAgentStatistics(): Promise<AgentStatistics> {
    const response = await this.client.get<AgentStatistics>('/agents/stats/overview')
    return response.data
  }

  async deleteAgent(agentId: string): Promise<void> {
    await this.client.delete(`/agents/${agentId}`)
  }

  // ============================================================================
  // Dashboard API
  // ============================================================================

  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.client.get<DashboardStats>('/events/stats/dashboard')
    return response.data
  }

  // ============================================================================
  // Users API (Admin only)
  // ============================================================================

  async getUsers(): Promise<User[]> {
    const response = await this.client.get<User[]>('/auth/users')
    return response.data
  }

  async createUser(data: {
    username: string
    password: string
    full_name: string
    email?: string
    role: string
  }): Promise<User> {
    const response = await this.client.post<User>('/auth/users', data)
    return response.data
  }

  async updateUser(userId: number, data: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>(`/auth/users/${userId}`, data)
    return response.data
  }

  async deleteUser(userId: number): Promise<void> {
    await this.client.delete(`/auth/users/${userId}`)
  }
}

// Export singleton instance
export const apiService = new APIService()
export default apiService
