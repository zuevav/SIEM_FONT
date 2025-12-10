package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Config represents the agent configuration
type Config struct {
	SIEM            SIEMConfig            `yaml:"siem"`
	EventLog        EventLogConfig        `yaml:"eventlog"`
	Sysmon          SysmonConfig          `yaml:"sysmon"`
	Inventory       InventoryConfig       `yaml:"inventory"`
	SoftwareControl SoftwareControlConfig `yaml:"software_control"`
	Protection      ProtectionConfig      `yaml:"protection"`
	Performance     PerformanceConfig     `yaml:"performance"`
	Logging         LoggingConfig         `yaml:"logging"`
	Agent           AgentConfig           `yaml:"agent"`
	Advanced        AdvancedConfig        `yaml:"advanced"`
}

type SIEMConfig struct {
	APIURL             string `yaml:"api_url"`
	RegisterOnStartup  bool   `yaml:"register_on_startup"`
	HeartbeatInterval  int    `yaml:"heartbeat_interval"`
	BatchSize          int    `yaml:"batch_size"`
	SendInterval       int    `yaml:"send_interval"`
	MaxQueueSize       int    `yaml:"max_queue_size"`
}

type EventLogConfig struct {
	Enabled          bool                `yaml:"enabled"`
	Channels         []EventLogChannel   `yaml:"channels"`
	MinSeverity      int                 `yaml:"min_severity"`
	ExcludeEventIDs  []int               `yaml:"exclude_event_ids"`
}

type EventLogChannel struct {
	Name       string `yaml:"name"`
	Enabled    bool   `yaml:"enabled"`
	MinEventID int    `yaml:"min_event_id"`
	MaxEventID int    `yaml:"max_event_id"`
}

type SysmonConfig struct {
	Enabled          bool  `yaml:"enabled"`
	CheckInstallation bool  `yaml:"check_installation"`
	PriorityEvents   []int `yaml:"priority_events"`
}

type InventoryConfig struct {
	Enabled           bool `yaml:"enabled"`
	FullScanInterval  int  `yaml:"full_scan_interval"`
	QuickScanInterval int  `yaml:"quick_scan_interval"`
	CollectSoftware   bool `yaml:"collect_software"`
	CollectServices   bool `yaml:"collect_services"`
	CollectStartup    bool `yaml:"collect_startup"`
	CollectNetwork    bool `yaml:"collect_network"`
}

// SoftwareControlConfig configures software installation control
type SoftwareControlConfig struct {
	Enabled              bool     `yaml:"enabled"`
	RequireApproval      bool     `yaml:"require_approval"`
	MonitorInstallers    bool     `yaml:"monitor_installers"`
	AllowedExtensions    []string `yaml:"allowed_extensions"`
	BlockedPublishers    []string `yaml:"blocked_publishers"`
	AllowedPublishers    []string `yaml:"allowed_publishers"`
	PollInterval         int      `yaml:"poll_interval"`
	ApprovalTimeout      int      `yaml:"approval_timeout"`
	NotifyOnBlock        bool     `yaml:"notify_on_block"`
	LogAllAttempts       bool     `yaml:"log_all_attempts"`
	WhitelistPaths       []string `yaml:"whitelist_paths"`
	InstallerPatterns    []string `yaml:"installer_patterns"`
}

type PerformanceConfig struct {
	MaxCPUPercent  int  `yaml:"max_cpu_percent"`
	MaxMemoryMB    int  `yaml:"max_memory_mb"`
	WorkerThreads  int  `yaml:"worker_threads"`
	Compression    bool `yaml:"compression"`
}

type LoggingConfig struct {
	Level       string `yaml:"level"`
	File        string `yaml:"file"`
	MaxSizeMB   int    `yaml:"max_size_mb"`
	MaxAgeDays  int    `yaml:"max_age_days"`
	MaxBackups  int    `yaml:"max_backups"`
	Console     bool   `yaml:"console"`
}

type AgentConfig struct {
	Version     string   `yaml:"version"`
	Tags        []string `yaml:"tags"`
	Criticality string   `yaml:"criticality"`
	Location    string   `yaml:"location"`
	Owner       string   `yaml:"owner"`
}

type AdvancedConfig struct {
	RetryAttempts      int  `yaml:"retry_attempts"`
	RetryDelaySeconds  int  `yaml:"retry_delay_seconds"`
	Debug              bool `yaml:"debug"`
	Profiling          bool `yaml:"profiling"`
	ProfilingPort      int  `yaml:"profiling_port"`
}

// ProtectionConfig configures agent self-protection
type ProtectionConfig struct {
	Enabled              bool `yaml:"enabled"`
	ProtectFiles         bool `yaml:"protect_files"`
	ProtectService       bool `yaml:"protect_service"`
	MonitorTampering     bool `yaml:"monitor_tampering"`
	AlertOnTampering     bool `yaml:"alert_on_tampering"`
	SelfHealEnabled      bool `yaml:"self_heal_enabled"`
	WatchdogEnabled      bool `yaml:"watchdog_enabled"`
	PreventDebugger      bool `yaml:"prevent_debugger"`
	IntegrityCheckInterval int `yaml:"integrity_check_interval"`
}

// Load reads and parses the configuration file
func Load(path string) (*Config, error) {
	// Check if file exists
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return nil, fmt.Errorf("config file not found: %s", path)
	}

	// Read file
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	// Parse YAML
	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	// Validate configuration
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return &config, nil
}

// Validate checks if the configuration is valid
func (c *Config) Validate() error {
	// SIEM API URL is required
	if c.SIEM.APIURL == "" {
		return fmt.Errorf("siem.api_url is required")
	}

	// Batch size must be positive
	if c.SIEM.BatchSize <= 0 {
		c.SIEM.BatchSize = 100
	}

	// Send interval must be positive
	if c.SIEM.SendInterval <= 0 {
		c.SIEM.SendInterval = 30
	}

	// Heartbeat interval must be positive
	if c.SIEM.HeartbeatInterval <= 0 {
		c.SIEM.HeartbeatInterval = 60
	}

	// Worker threads must be positive
	if c.Performance.WorkerThreads <= 0 {
		c.Performance.WorkerThreads = 4
	}

	// Log level validation
	validLevels := map[string]bool{
		"debug": true,
		"info":  true,
		"warn":  true,
		"error": true,
	}
	if !validLevels[c.Logging.Level] {
		c.Logging.Level = "info"
	}

	return nil
}

// GetEnabledChannels returns list of enabled event log channels
func (c *EventLogConfig) GetEnabledChannels() []EventLogChannel {
	enabled := make([]EventLogChannel, 0)
	for _, ch := range c.Channels {
		if ch.Enabled {
			enabled = append(enabled, ch)
		}
	}
	return enabled
}

// IsEventIDExcluded checks if an event ID should be excluded
func (c *EventLogConfig) IsEventIDExcluded(eventID int) bool {
	for _, id := range c.ExcludeEventIDs {
		if id == eventID {
			return true
		}
	}
	return false
}

// IsPriorityEvent checks if a Sysmon event is high-priority
func (c *SysmonConfig) IsPriorityEvent(eventID int) bool {
	for _, id := range c.PriorityEvents {
		if id == eventID {
			return true
		}
	}
	return false
}
