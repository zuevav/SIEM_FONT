/**
 * API Types for SIEM Frontend
 */

// ============================================================================
// Auth & User Types
// ============================================================================

export interface User {
  UserId: number
  Username: string
  FullName: string
  Email?: string
  Role: 'admin' | 'analyst' | 'viewer'
  IsActive: boolean
  CreatedAt: string
  LastLogin?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// ============================================================================
// Event Types
// ============================================================================

export interface Event {
  EventId: number
  EventGuid: string
  AgentId?: string
  Computer: string
  FQDN?: string
  IPAddress?: string
  SourceType: string
  EventCode: number
  EventTime: string
  RecordID?: number
  Channel?: string
  Provider?: string
  Severity: number
  Message?: string

  // User information
  SubjectUser?: string
  SubjectDomain?: string
  TargetUser?: string

  // Process information
  ProcessID?: number
  ProcessName?: string
  ProcessPath?: string
  ProcessCommandLine?: string
  ParentProcessID?: number
  ParentProcessName?: string

  // Network information
  SourceIP?: string
  SourcePort?: number
  DestinationIP?: string
  DestinationPort?: number
  Protocol?: string

  // File/Registry
  FilePath?: string
  FileHash?: string
  RegistryPath?: string

  // AI Analysis
  AIProcessed?: boolean
  AIIsAttack?: boolean
  AIScore?: number
  AICategory?: string
  AIDescription?: string
  AIConfidence?: number

  CollectedAt: string
}

export interface EventFilter {
  event_code?: number[]
  severity?: number[]
  computer?: string
  source_type?: string
  start_time?: string
  end_time?: string
  search?: string
  ai_is_attack?: boolean
  ai_score_min?: number
  limit?: number
  offset?: number
}

export interface EventStatistics {
  total_24h: number
  total_7d: number
  by_severity: Record<number, number>
  by_source: Record<string, number>
  top_computers: Array<{ computer: string; count: number }>
}

// ============================================================================
// Alert Types
// ============================================================================

export interface Alert {
  AlertId: number
  AlertGuid: string
  RuleId?: number
  RuleName?: string
  Title: string
  Description?: string
  Severity: number
  Status: 'new' | 'acknowledged' | 'in_progress' | 'resolved' | 'false_positive'
  Priority: number

  // Assignment
  AssignedToUserId?: number
  AssignedToUser?: string
  AssignedAt?: string

  // Timing
  FirstSeenAt: string
  LastSeenAt: string
  AcknowledgedAt?: string
  ResolvedAt?: string

  // Details
  SourceIP?: string
  DestinationIP?: string
  Computer?: string
  ProcessName?: string

  // Counts
  EventCount?: number
  AffectedAssets?: number

  // MITRE ATT&CK
  MitreAttackTactics?: string
  MitreAttackTechniques?: string

  // AI Analysis
  AIAnalysis?: string
  AIRecommendations?: string

  // Comments
  Comments?: string

  CreatedAt: string
}

export interface AlertFilter {
  status?: string[]
  severity?: number[]
  priority?: number[]
  assigned_to?: number
  start_date?: string
  end_date?: string
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// Incident Types
// ============================================================================

export interface Incident {
  IncidentId: number
  IncidentGuid: string
  Title: string
  Description?: string
  Severity: number
  Status: 'open' | 'investigating' | 'contained' | 'remediated' | 'closed'
  Priority: number

  // Assignment
  AssignedToUserId?: number
  AssignedToUser?: string
  AssignedAt?: string

  // Timing
  DetectedAt: string
  StartedAt?: string
  ContainedAt?: string
  RemediatedAt?: string
  ClosedAt?: string

  // Counts
  AlertCount?: number
  EventCount?: number
  AffectedAssets?: number

  // Classification
  IncidentCategory?: string
  IncidentType?: string
  OperationalRiskCategory?: string

  // Impact
  EstimatedDamage_RUB?: number
  ActualDamage_RUB?: number

  // MITRE ATT&CK
  MitreAttackChain?: string

  // CBR Compliance
  IsReportable?: boolean
  IsReportedToCBR?: boolean
  CBRReportDate?: string
  CBRIncidentNumber?: string

  // AI Analysis
  AIRootCause?: string
  AIImpactAssessment?: string
  AIRecommendations?: string

  // Work Log
  WorkLog?: string
  ContainmentActions?: string
  RemediationActions?: string
  LessonsLearned?: string

  CreatedAt: string
  CreatedByUserId: number
  CreatedByUser?: string
}

export interface IncidentFilter {
  status?: string[]
  severity?: number[]
  priority?: number[]
  assigned_to?: number
  start_date?: string
  end_date?: string
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// Agent Types
// ============================================================================

export interface Agent {
  AgentId: string
  Hostname: string
  FQDN?: string
  IPAddress?: string
  MACAddress?: string
  OSVersion?: string
  OSBuild?: string
  Architecture?: string
  Domain?: string
  AgentVersion?: string
  Status: 'online' | 'offline' | 'error'
  LastSeen?: string
  RegisteredAt: string

  // System Info
  CPUModel?: string
  CPUCores?: number
  TotalRAM_MB?: number
  TotalDisk_GB?: number

  // Statistics
  EventsCollected?: number
  LastEventTime?: string
}

export interface AgentStatistics {
  total: number
  online: number
  offline: number
  error: number
  by_os: Record<string, number>
}

// ============================================================================
// Network Device Types
// ============================================================================

export interface NetworkDevice {
  DeviceId?: string
  Name: string
  IP: string
  Type: 'printer' | 'switch' | 'router' | 'firewall' | 'ups'
  Status: 'online' | 'offline' | 'warning' | 'error'
  LastSeen?: string

  // Device-specific metrics
  Metrics?: {
    cpu_usage?: number
    memory_usage?: number
    toner_level?: number
    battery_charge?: number
    load_percent?: number
    interfaces_up?: number
    interfaces_down?: number
  }
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStats {
  events: {
    total_24h: number
    total_7d: number
    rate_per_hour: number
  }
  alerts: {
    new: number
    acknowledged: number
    total_open: number
  }
  incidents: {
    open: number
    investigating: number
    total_this_month: number
  }
  agents: {
    online: number
    offline: number
    total: number
  }
}

export interface TimeSeriesData {
  timestamp: string
  value: number
  label?: string
}

// ============================================================================
// WebSocket Types
// ============================================================================

export interface WebSocketMessage {
  type: 'connection' | 'event' | 'alert' | 'incident' | 'agent' | 'statistics' | 'notification'
  action?: 'created' | 'updated' | 'deleted'
  data: any
  timestamp: string
}

// ============================================================================
// Pagination Types
// ============================================================================

export interface PaginationParams {
  page: number
  pageSize: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ============================================================================
// API Response Types
// ============================================================================

export interface APIResponse<T = any> {
  success: boolean
  message?: string
  data?: T
  error?: string
}

export interface APIError {
  detail: string | Array<{ msg: string; type: string }>
}
