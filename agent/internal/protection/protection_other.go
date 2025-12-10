// +build !windows

package protection

import (
	"log"
)

// ProtectionConfig holds protection settings
type ProtectionConfig struct {
	Enabled             bool
	ProtectFiles        bool
	ProtectService      bool
	MonitorTampering    bool
	AlertOnTampering    bool
	SelfHealEnabled     bool
	WatchdogEnabled     bool
}

// ProtectionManager handles agent self-protection (stub for non-Windows)
type ProtectionManager struct {
	config       *ProtectionConfig
	agentPath    string
	alertHandler func(alertType, message string)
}

// NewProtectionManager creates a new protection manager
func NewProtectionManager(config *ProtectionConfig, agentPath string) *ProtectionManager {
	return &ProtectionManager{
		config:    config,
		agentPath: agentPath,
	}
}

// SetAlertHandler sets the callback for alerts
func (pm *ProtectionManager) SetAlertHandler(handler func(alertType, message string)) {
	pm.alertHandler = handler
}

// Start starts the protection manager
func (pm *ProtectionManager) Start() error {
	log.Println("Protection manager: Not implemented on this platform")
	return nil
}

// Stop stops the protection manager
func (pm *ProtectionManager) Stop() {}

// ApplyFileProtection is a no-op on non-Windows
func (pm *ProtectionManager) ApplyFileProtection() error {
	return nil
}

// ApplyServiceProtection is a no-op on non-Windows
func (pm *ProtectionManager) ApplyServiceProtection(serviceName string) error {
	return nil
}

// HideProcess is a no-op on non-Windows
func HideProcess() error {
	return nil
}

// PreventDebugger is a no-op on non-Windows
func PreventDebugger() bool {
	return false
}

// MonitorParentProcess is a no-op on non-Windows
func MonitorParentProcess() (uint32, error) {
	return 0, nil
}
