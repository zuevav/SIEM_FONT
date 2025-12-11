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
  DetectionRule,
  DetectionRuleFilter,
  DetectionRuleCreate,
  DetectionRuleUpdate,
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
    const response = await this.client.get<any>('/events', {
      params: filter,
    })
    // Backend returns { events: [], total, limit, offset }
    // Transform to PaginatedResponse format { items: [], total, page, page_size, total_pages }
    const data = response.data
    return {
      items: data.events || [],
      total: data.total || 0,
      page: Math.floor((data.offset || 0) / (data.limit || 100)) + 1,
      page_size: data.limit || 100,
      total_pages: Math.ceil((data.total || 0) / (data.limit || 100)),
    }
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
  // Detection Rules API
  // ============================================================================

  async getDetectionRules(filter: DetectionRuleFilter = {}): Promise<{ rules: DetectionRule[]; total: number; limit: number; offset: number }> {
    const response = await this.client.get<{ rules: DetectionRule[]; total: number; limit: number; offset: number }>('/alerts/rules', {
      params: filter,
    })
    return response.data
  }

  async getDetectionRule(ruleId: number): Promise<DetectionRule> {
    const response = await this.client.get<DetectionRule>(`/alerts/rules/${ruleId}`)
    return response.data
  }

  async createDetectionRule(data: DetectionRuleCreate): Promise<DetectionRule> {
    const response = await this.client.post<DetectionRule>('/alerts/rules', data)
    return response.data
  }

  async updateDetectionRule(ruleId: number, data: DetectionRuleUpdate): Promise<DetectionRule> {
    const response = await this.client.patch<DetectionRule>(`/alerts/rules/${ruleId}`, data)
    return response.data
  }

  async deleteDetectionRule(ruleId: number): Promise<void> {
    await this.client.delete(`/alerts/rules/${ruleId}`)
  }

  async toggleDetectionRule(ruleId: number, enabled: boolean): Promise<DetectionRule> {
    const response = await this.client.patch<DetectionRule>(`/alerts/rules/${ruleId}`, {
      is_enabled: enabled,
    })
    return response.data
  }

  // ============================================================================
  // Alerts API
  // ============================================================================

  async getAlerts(filter: AlertFilter = {}): Promise<PaginatedResponse<Alert>> {
    const response = await this.client.get<any>('/alerts', {
      params: filter,
    })
    // Backend returns { alerts: [], total, limit, offset }
    // Transform to PaginatedResponse format { items: [], total, page, page_size, total_pages }
    const data = response.data
    return {
      items: data.alerts || [],
      total: data.total || 0,
      page: Math.floor((data.offset || 0) / (data.limit || 100)) + 1,
      page_size: data.limit || 100,
      total_pages: Math.ceil((data.total || 0) / (data.limit || 100)),
    }
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
    const response = await this.client.get<any>('/incidents', {
      params: filter,
    })
    // Backend returns { incidents: [], total, limit, offset }
    // Transform to PaginatedResponse format { items: [], total, page, page_size, total_pages }
    const data = response.data
    return {
      items: data.incidents || [],
      total: data.total || 0,
      page: Math.floor((data.offset || 0) / (data.limit || 100)) + 1,
      page_size: data.limit || 100,
      total_pages: Math.ceil((data.total || 0) / (data.limit || 100)),
    }
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

  async analyzeIncidentWithAI(incidentId: number): Promise<{ success: boolean; analysis: any }> {
    const response = await this.client.post(`/incidents/${incidentId}/ai-analysis`)
    return response.data
  }

  async getIncidentAIAnalysis(incidentId: number): Promise<{ ai_processed: boolean; analysis?: any }> {
    const response = await this.client.get(`/incidents/${incidentId}/ai-analysis`)
    return response.data
  }

  // ============================================================================
  // Agents API
  // ============================================================================

  async getAgents(params?: { status?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<Agent>> {
    const response = await this.client.get<any>('/agents', {
      params,
    })
    // Backend returns { agents: [], total, limit, offset }
    // Transform to PaginatedResponse format { items: [], total, page, page_size, total_pages }
    const data = response.data
    return {
      items: data.agents || [],
      total: data.total || 0,
      page: Math.floor((data.offset || 0) / (data.limit || 100)) + 1,
      page_size: data.limit || 100,
      total_pages: Math.ceil((data.total || 0) / (data.limit || 100)),
    }
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
    const response = await this.client.get<DashboardStats>('/dashboard/stats')
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

  // ============================================================================
  // Settings API
  // ============================================================================

  async getSettings(): Promise<any> {
    const response = await this.client.get('/settings')
    return response.data
  }

  async updateSettings(data: any): Promise<any> {
    const response = await this.client.post('/settings', data)
    return response.data
  }

  async testFreeScoutConnection(url: string, apiKey: string): Promise<{ success: boolean; mailbox_name?: string; error?: string }> {
    const response = await this.client.post('/settings/test-freescout', { url, api_key: apiKey })
    return response.data
  }

  async testEmailSettings(data: any): Promise<{ success: boolean }> {
    const response = await this.client.post('/settings/test-email', data)
    return response.data
  }

  async testADConnection(server: string, baseDn: string, bindUser: string, bindPassword: string): Promise<{
    success: boolean
    message: string
    server_type?: string
    domain_info?: string
    user_count?: number
    error?: string
  }> {
    const response = await this.client.post('/settings/test-ad', {
      server,
      base_dn: baseDn,
      bind_user: bindUser,
      bind_password: bindPassword
    })
    return response.data
  }

  // ============================================================================
  // System Update API
  // ============================================================================

  async getSystemInfo(): Promise<{
    version: string
    git_branch: string
    git_commit: string
    docker_compose_version: string
    last_update: string
    update_available: boolean
  }> {
    const response = await this.client.get('/system/info')
    return response.data
  }

  async checkSystemUpdates(): Promise<{
    update_available: boolean
    current_version: string
    latest_version: string
    changelog?: string[]
  }> {
    const response = await this.client.get('/system/check-updates')
    return response.data
  }

  async startSystemUpdate(): Promise<{ success: boolean }> {
    const response = await this.client.post('/system/update')
    return response.data
  }

  // ============================================================================
  // FreeScout Integration API
  // ============================================================================

  async createFreeScoutTicket(alertId: number): Promise<{ ticket_number: number; ticket_url: string }> {
    const response = await this.client.post(`/integrations/freescout/create-ticket`, { alert_id: alertId })
    return response.data
  }

  // ============================================================================
  // Saved Searches API
  // ============================================================================

  async getSavedSearches(params?: {
    search_type?: 'events' | 'alerts' | 'incidents'
    include_shared?: boolean
  }): Promise<{
    total: number
    items: Array<{
      id: number
      name: string
      description?: string
      search_type: string
      filters: Record<string, any>
      user_id: number
      is_shared: boolean
      created_at: string
      updated_at: string
    }>
  }> {
    const response = await this.client.get('/searches', { params })
    return response.data
  }

  async getSavedSearch(searchId: number): Promise<{
    id: number
    name: string
    description?: string
    search_type: string
    filters: Record<string, any>
    user_id: number
    is_shared: boolean
    created_at: string
    updated_at: string
    username?: string
  }> {
    const response = await this.client.get(`/searches/${searchId}`)
    return response.data
  }

  async createSavedSearch(data: {
    name: string
    description?: string
    search_type: 'events' | 'alerts' | 'incidents'
    filters: Record<string, any>
    is_shared?: boolean
  }): Promise<{
    id: number
    name: string
    description?: string
    search_type: string
    filters: Record<string, any>
    user_id: number
    is_shared: boolean
    created_at: string
    updated_at: string
  }> {
    const response = await this.client.post('/searches', data)
    return response.data
  }

  async updateSavedSearch(
    searchId: number,
    data: {
      name?: string
      description?: string
      search_type?: 'events' | 'alerts' | 'incidents'
      filters?: Record<string, any>
      is_shared?: boolean
    }
  ): Promise<{
    id: number
    name: string
    description?: string
    search_type: string
    filters: Record<string, any>
    user_id: number
    is_shared: boolean
    created_at: string
    updated_at: string
  }> {
    const response = await this.client.put(`/searches/${searchId}`, data)
    return response.data
  }

  async deleteSavedSearch(searchId: number): Promise<void> {
    await this.client.delete(`/searches/${searchId}`)
  }

  // ============================================================================
  // Documentation API
  // ============================================================================

  async listDocumentation(): Promise<{
    docs: Array<{
      filename: string
      title: string
      path: string
    }>
    total: number
  }> {
    const response = await this.client.get('/docs/list')
    return response.data
  }

  async getDocumentation(filename: string): Promise<{
    filename: string
    content: string
    size: number
  }> {
    const response = await this.client.get(`/docs/${filename}`)
    return response.data
  }

  // ============================================================================
  // SOAR Playbooks API
  // ============================================================================

  async listPlaybooks(params?: {
    page?: number
    page_size?: number
    enabled_only?: boolean
  }): Promise<{
    items: Array<any>
    total: number
    page: number
    page_size: number
  }> {
    const response = await this.client.get('/soar/playbooks', { params })
    return response.data
  }

  async getPlaybook(playbookId: number): Promise<any> {
    const response = await this.client.get(`/soar/playbooks/${playbookId}`)
    return response.data
  }

  async createPlaybook(data: {
    name: string
    description?: string
    trigger_on_severity?: number[]
    trigger_on_mitre_tactic?: string[]
    action_ids?: number[]
    requires_approval?: boolean
    is_enabled?: boolean
  }): Promise<any> {
    const response = await this.client.post('/soar/playbooks', data)
    return response.data
  }

  async updatePlaybook(playbookId: number, data: any): Promise<any> {
    const response = await this.client.put(`/soar/playbooks/${playbookId}`, data)
    return response.data
  }

  async deletePlaybook(playbookId: number): Promise<void> {
    await this.client.delete(`/soar/playbooks/${playbookId}`)
  }

  async listActions(params?: {
    page?: number
    page_size?: number
  }): Promise<{
    items: Array<any>
    total: number
    page: number
    page_size: number
  }> {
    const response = await this.client.get('/soar/actions', { params })
    return response.data
  }

  async getAction(actionId: number): Promise<any> {
    const response = await this.client.get(`/soar/actions/${actionId}`)
    return response.data
  }

  async createAction(data: {
    name: string
    action_type: string
    config: Record<string, any>
    timeout_seconds?: number
    retry_count?: number
  }): Promise<any> {
    const response = await this.client.post('/soar/actions', data)
    return response.data
  }

  async updateAction(actionId: number, data: any): Promise<any> {
    const response = await this.client.put(`/soar/actions/${actionId}`, data)
    return response.data
  }

  async deleteAction(actionId: number): Promise<void> {
    await this.client.delete(`/soar/actions/${actionId}`)
  }

  async listExecutions(params?: {
    page?: number
    page_size?: number
    playbook_id?: number
    status?: string
  }): Promise<{
    items: Array<any>
    total: number
    page: number
    page_size: number
  }> {
    const response = await this.client.get('/soar/executions', { params })
    return response.data
  }

  async getExecution(executionId: number): Promise<any> {
    const response = await this.client.get(`/soar/executions/${executionId}`)
    return response.data
  }

  async executePlaybook(data: {
    playbook_id: number
    alert_id?: number
    incident_id?: number
  }): Promise<any> {
    const response = await this.client.post('/soar/executions', data)
    return response.data
  }

  async approveExecution(executionId: number, approved: boolean, comment?: string): Promise<any> {
    const response = await this.client.post(`/soar/executions/${executionId}/approve`, {
      approved,
      comment
    })
    return response.data
  }

  async cancelExecution(executionId: number): Promise<any> {
    const response = await this.client.delete(`/soar/executions/${executionId}/cancel`)
    return response.data
  }

  async getPlaybookStats(): Promise<{
    total_playbooks: number
    enabled_playbooks: number
    total_executions: number
    successful_executions: number
    failed_executions: number
    pending_approvals: number
    avg_execution_time_seconds?: number
  }> {
    const response = await this.client.get('/soar/stats')
    return response.data
  }

  // ============================================================================
  // FIM (File Integrity Monitoring) API
  // ============================================================================

  async listFIMEvents(params?: {
    start_time?: string
    end_time?: string
    last_hours?: number
    event_type?: string
    file_path?: string
    registry_key?: string
    process_name?: string
    agent_id?: string
    hostname?: string
    limit?: number
    offset?: number
  }): Promise<{
    events: Array<{
      event_id: number
      event_time: string
      event_code: number
      event_type: string
      hostname: string
      agent_id: string
      file_path?: string
      process_name?: string
      target_user?: string
      message: string
      severity: number
      category?: string
      file_hash?: string
      registry_key?: string
      registry_value?: string
      event_type_detail?: string
      details?: string
      new_name?: string
    }>
    total: number
    limit: number
    offset: number
    has_more: boolean
  }> {
    const response = await this.client.get('/fim/events', { params })
    return response.data
  }

  async getFIMEvent(eventId: number): Promise<{
    event_id: number
    event_time: string
    event_code: number
    event_type: string
    hostname: string
    agent_id: string
    source_type: string
    provider: string
    severity: number
    category?: string
    message: string
    file_path?: string
    file_hash?: string
    registry_key?: string
    registry_value?: string
    registry_details?: string
    event_type_detail?: string
    target_object?: string
    new_name?: string
    process_name?: string
    process_id?: number
    process_command_line?: string
    target_user?: string
    subject_user?: string
    event_data: any
    raw_xml?: string
  }> {
    const response = await this.client.get(`/fim/events/${eventId}`)
    return response.data
  }

  async getFIMStatistics(hours: number = 24): Promise<{
    time_window_hours: number
    total_fim_events: number
    critical_changes: number
    events_by_type: Record<string, number>
    events_by_severity: Record<string, number>
    top_file_paths: Array<{ path: string; count: number }>
    top_processes: Array<{ name: string; count: number }>
  }> {
    const response = await this.client.get('/fim/statistics', { params: { hours } })
    return response.data
  }
}

// Export singleton instance
export const apiService = new APIService()
export default apiService
