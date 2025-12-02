package collector

import (
	"time"
)

// Event represents a normalized security event
type Event struct {
	// Agent identification
	AgentID   string `json:"agent_id"`
	Computer  string `json:"computer"`
	FQDN      string `json:"fqdn,omitempty"`
	IPAddress string `json:"ip_address,omitempty"`

	// Event metadata
	SourceType      string    `json:"source_type"`       // "Windows Security", "Sysmon", "PowerShell"
	EventCode       int       `json:"event_code"`        // Windows Event ID
	EventTime       time.Time `json:"event_time"`        // When event occurred
	RecordID        int64     `json:"record_id"`         // Event record ID
	Channel         string    `json:"channel"`           // Event log channel
	Provider        string    `json:"provider"`          // Event provider
	Severity        int       `json:"severity"`          // 1-5 (1=Info, 5=Critical)
	Message         string    `json:"message,omitempty"` // Event message
	RawXML          string    `json:"raw_xml,omitempty"` // Original XML

	// User information
	SubjectUser     string `json:"subject_user,omitempty"`      // User who performed action
	SubjectDomain   string `json:"subject_domain,omitempty"`    // User's domain
	SubjectLogonID  string `json:"subject_logon_id,omitempty"`  // Logon session ID
	TargetUser      string `json:"target_user,omitempty"`       // Target user (if different)
	TargetDomain    string `json:"target_domain,omitempty"`     // Target domain
	TargetLogonID   string `json:"target_logon_id,omitempty"`   // Target logon ID

	// Process information
	ProcessID          int    `json:"process_id,omitempty"`
	ProcessName        string `json:"process_name,omitempty"`
	ProcessPath        string `json:"process_path,omitempty"`
	ProcessCommandLine string `json:"process_command_line,omitempty"`
	ParentProcessID    int    `json:"parent_process_id,omitempty"`
	ParentProcessName  string `json:"parent_process_name,omitempty"`

	// Network information
	SourceIP        string `json:"source_ip,omitempty"`
	SourcePort      int    `json:"source_port,omitempty"`
	SourceHostname  string `json:"source_hostname,omitempty"`
	DestinationIP   string `json:"destination_ip,omitempty"`
	DestinationPort int    `json:"destination_port,omitempty"`
	Protocol        string `json:"protocol,omitempty"`

	// File/Registry information
	FilePath        string `json:"file_path,omitempty"`
	FileHash        string `json:"file_hash,omitempty"`         // SHA256
	RegistryPath    string `json:"registry_path,omitempty"`
	RegistryValue   string `json:"registry_value,omitempty"`
	ObjectType      string `json:"object_type,omitempty"`       // File, Registry, etc.
	AccessMask      string `json:"access_mask,omitempty"`       // Permissions

	// Authentication information
	LogonType       int    `json:"logon_type,omitempty"`        // Windows logon type (2, 3, 10, etc.)
	AuthPackage     string `json:"auth_package,omitempty"`      // NTLM, Kerberos, etc.
	WorkstationName string `json:"workstation_name,omitempty"`  // Source workstation
	FailureReason   string `json:"failure_reason,omitempty"`    // For failed logons

	// Service information
	ServiceName    string `json:"service_name,omitempty"`
	ServiceType    string `json:"service_type,omitempty"`
	ServiceAccount string `json:"service_account,omitempty"`

	// Additional fields
	EventData      map[string]string `json:"event_data,omitempty"`       // Additional event-specific data
	TaskCategory   string            `json:"task_category,omitempty"`    // Event task category
	Keywords       []string          `json:"keywords,omitempty"`         // Event keywords
	CollectedAt    time.Time         `json:"collected_at"`               // When agent collected event
}

// InventoryItem represents a software or service inventory item
type InventoryItem struct {
	AgentID     string    `json:"agent_id"`
	Computer    string    `json:"computer"`
	Type        string    `json:"type"`         // "software" or "service"
	Name        string    `json:"name"`
	Version     string    `json:"version,omitempty"`
	Vendor      string    `json:"vendor,omitempty"`
	InstallDate string    `json:"install_date,omitempty"`
	InstallPath string    `json:"install_path,omitempty"`
	Status      string    `json:"status,omitempty"`       // For services: Running, Stopped
	StartType   string    `json:"start_type,omitempty"`   // For services: Automatic, Manual, Disabled
	Description string    `json:"description,omitempty"`
	CollectedAt time.Time `json:"collected_at"`
}

// HeartbeatData represents agent heartbeat information
type HeartbeatData struct {
	AgentID         string    `json:"agent_id"`
	Hostname        string    `json:"hostname"`
	IPAddress       string    `json:"ip_address"`
	Status          string    `json:"status"` // "online"
	Version         string    `json:"version"`
	EventsCollected int64     `json:"events_collected"`
	EventsSent      int64     `json:"events_sent"`
	LastError       string    `json:"last_error,omitempty"`
	Uptime          int64     `json:"uptime"` // seconds
	Timestamp       time.Time `json:"timestamp"`
}

// RegistrationData represents agent registration information
type RegistrationData struct {
	AgentID      string            `json:"agent_id"`
	Hostname     string            `json:"hostname"`
	FQDN         string            `json:"fqdn,omitempty"`
	IPAddress    string            `json:"ip_address"`
	MACAddress   string            `json:"mac_address,omitempty"`
	OSVersion    string            `json:"os_version"`
	OSBuild      string            `json:"os_build,omitempty"`
	Architecture string            `json:"architecture"`
	Domain       string            `json:"domain,omitempty"`
	CPUModel     string            `json:"cpu_model,omitempty"`
	CPUCores     int               `json:"cpu_cores,omitempty"`
	TotalRAM_MB  int               `json:"total_ram_mb,omitempty"`
	TotalDisk_GB int               `json:"total_disk_gb,omitempty"`
	AgentVersion string            `json:"agent_version"`
	Config       map[string]string `json:"config,omitempty"`
}

// SeverityFromWindowsLevel converts Windows event level to our 1-5 severity scale
func SeverityFromWindowsLevel(level int) int {
	switch level {
	case 1: // Critical
		return 5
	case 2: // Error
		return 4
	case 3: // Warning
		return 3
	case 4: // Information
		return 1
	case 5: // Verbose
		return 1
	default:
		return 2
	}
}

// IsHighPriority checks if event should be sent immediately
func (e *Event) IsHighPriority() bool {
	// Critical severity
	if e.Severity >= 4 {
		return true
	}

	// Security-critical events
	securityEvents := []int{
		4624, 4625, 4648, 4672, 4720, 4722, 4724, 4728, 4732, 4735, 4738, 4740, 4756, 4768, 4769, 4771,
		1102, 1100, 4657, 4663, 4688, 4697, 4698, 4699, 4700, 4701, 4702, 5140, 5142, 5145,
	}

	for _, id := range securityEvents {
		if e.EventCode == id {
			return true
		}
	}

	// Sysmon critical events
	if e.SourceType == "Sysmon" {
		sysmonEvents := []int{1, 3, 7, 8, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22}
		for _, id := range sysmonEvents {
			if e.EventCode == id {
				return true
			}
		}
	}

	return false
}
