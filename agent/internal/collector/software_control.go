//go:build windows

package collector

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"siem-agent/internal/config"
)

// SoftwareInstallRequest represents a software installation request
type SoftwareInstallRequest struct {
	RequestID       string    `json:"request_id,omitempty"`
	AgentID         string    `json:"agent_id"`
	UserName        string    `json:"user_name"`
	ComputerName    string    `json:"computer_name"`
	SoftwareName    string    `json:"software_name"`
	SoftwareVersion string    `json:"software_version,omitempty"`
	Publisher       string    `json:"publisher,omitempty"`
	InstallerPath   string    `json:"installer_path"`
	InstallerHash   string    `json:"installer_hash,omitempty"`
	CommandLine     string    `json:"command_line,omitempty"`
	UserComment     string    `json:"user_comment,omitempty"`
	Status          string    `json:"status"`
	RequestedAt     time.Time `json:"requested_at"`
	ReviewedAt      *time.Time `json:"reviewed_at,omitempty"`
	ReviewedBy      string    `json:"reviewed_by,omitempty"`
	AdminComment    string    `json:"admin_comment,omitempty"`
}

// SoftwareControlCollector monitors and controls software installations
type SoftwareControlCollector struct {
	config       *config.SoftwareControlConfig
	agentID      string
	hostname     string
	currentUser  string
	ctx          context.Context
	cancel       context.CancelFunc
	mutex        sync.RWMutex

	// Pending requests waiting for approval
	pendingRequests map[string]*SoftwareInstallRequest

	// Installer patterns compiled as regex
	installerPatterns []*regexp.Regexp

	// Callback for sending requests to SIEM
	onInstallRequest func(*SoftwareInstallRequest) error
	onCheckStatus    func(string) (*SoftwareInstallRequest, error)
}

// NewSoftwareControlCollector creates a new software control collector
func NewSoftwareControlCollector(cfg *config.SoftwareControlConfig, agentID, hostname string) *SoftwareControlCollector {
	ctx, cancel := context.WithCancel(context.Background())

	collector := &SoftwareControlCollector{
		config:          cfg,
		agentID:         agentID,
		hostname:        hostname,
		ctx:             ctx,
		cancel:          cancel,
		pendingRequests: make(map[string]*SoftwareInstallRequest),
	}

	// Get current user
	collector.currentUser = os.Getenv("USERNAME")
	if collector.currentUser == "" {
		collector.currentUser = "SYSTEM"
	}

	// Compile installer patterns
	collector.compilePatterns()

	return collector
}

// compilePatterns compiles installer detection patterns
func (c *SoftwareControlCollector) compilePatterns() {
	defaultPatterns := []string{
		`(?i)setup\.exe$`,
		`(?i)install\.exe$`,
		`(?i)installer\.exe$`,
		`(?i).*_setup\.exe$`,
		`(?i).*_install\.exe$`,
		`(?i).*\.msi$`,
		`(?i).*\.msp$`,
		`(?i)msiexec\.exe`,
	}

	patterns := append(defaultPatterns, c.config.InstallerPatterns...)

	for _, pattern := range patterns {
		re, err := regexp.Compile(pattern)
		if err != nil {
			log.Printf("Warning: Invalid installer pattern %q: %v", pattern, err)
			continue
		}
		c.installerPatterns = append(c.installerPatterns, re)
	}
}

// SetCallbacks sets the callbacks for SIEM communication
func (c *SoftwareControlCollector) SetCallbacks(
	onRequest func(*SoftwareInstallRequest) error,
	onCheck func(string) (*SoftwareInstallRequest, error),
) {
	c.onInstallRequest = onRequest
	c.onCheckStatus = onCheck
}

// IsInstaller checks if a file path matches installer patterns
func (c *SoftwareControlCollector) IsInstaller(filePath string) bool {
	for _, pattern := range c.installerPatterns {
		if pattern.MatchString(filePath) {
			return true
		}
	}
	return false
}

// IsWhitelisted checks if a path is in the whitelist
func (c *SoftwareControlCollector) IsWhitelisted(filePath string) bool {
	normalizedPath := strings.ToLower(filepath.Clean(filePath))

	for _, whitePath := range c.config.WhitelistPaths {
		normalizedWhite := strings.ToLower(filepath.Clean(whitePath))
		if strings.HasPrefix(normalizedPath, normalizedWhite) {
			return true
		}
	}
	return false
}

// CheckInstallationAttempt checks if a process should be allowed to run
// Returns: allowed (bool), request (if pending approval)
func (c *SoftwareControlCollector) CheckInstallationAttempt(
	processPath string,
	commandLine string,
	userName string,
	userComment string,
) (bool, *SoftwareInstallRequest, error) {

	if !c.config.Enabled {
		return true, nil, nil
	}

	// Check if it's an installer
	if !c.IsInstaller(processPath) {
		return true, nil, nil
	}

	// Check whitelist
	if c.IsWhitelisted(processPath) {
		log.Printf("Installer whitelisted: %s", processPath)
		return true, nil, nil
	}

	// Extract software info from path
	softwareName := extractSoftwareName(processPath)

	// Create install request
	request := &SoftwareInstallRequest{
		AgentID:       c.agentID,
		UserName:      userName,
		ComputerName:  c.hostname,
		SoftwareName:  softwareName,
		InstallerPath: processPath,
		CommandLine:   commandLine,
		UserComment:   userComment,
		Status:        "pending",
		RequestedAt:   time.Now(),
	}

	// Log the attempt
	if c.config.LogAllAttempts {
		log.Printf("Software installation attempt detected: %s by %s", softwareName, userName)
	}

	// If approval not required, allow but log
	if !c.config.RequireApproval {
		request.Status = "auto_approved"
		if c.onInstallRequest != nil {
			c.onInstallRequest(request)
		}
		return true, request, nil
	}

	// Send request to SIEM for approval
	if c.onInstallRequest != nil {
		if err := c.onInstallRequest(request); err != nil {
			log.Printf("Error sending install request to SIEM: %v", err)
			// On error, block by default for security
			return false, request, err
		}
	}

	// Store pending request
	c.mutex.Lock()
	c.pendingRequests[request.RequestID] = request
	c.mutex.Unlock()

	// Wait for approval (with timeout)
	approved, err := c.waitForApproval(request)

	// Clean up pending request
	c.mutex.Lock()
	delete(c.pendingRequests, request.RequestID)
	c.mutex.Unlock()

	return approved, request, err
}

// waitForApproval polls SIEM for approval status
func (c *SoftwareControlCollector) waitForApproval(request *SoftwareInstallRequest) (bool, error) {
	if c.onCheckStatus == nil {
		return false, fmt.Errorf("status check callback not configured")
	}

	pollInterval := time.Duration(c.config.PollInterval) * time.Second
	if pollInterval < 5*time.Second {
		pollInterval = 5 * time.Second
	}

	timeout := time.Duration(c.config.ApprovalTimeout) * time.Second
	if timeout < time.Minute {
		timeout = 5 * time.Minute
	}

	deadline := time.Now().Add(timeout)
	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	log.Printf("Waiting for approval of %s (timeout: %v)", request.SoftwareName, timeout)

	for {
		select {
		case <-c.ctx.Done():
			return false, fmt.Errorf("collector stopped")

		case <-ticker.C:
			if time.Now().After(deadline) {
				log.Printf("Approval timeout for %s", request.SoftwareName)
				return false, fmt.Errorf("approval timeout")
			}

			// Check status
			updatedRequest, err := c.onCheckStatus(request.RequestID)
			if err != nil {
				log.Printf("Error checking approval status: %v", err)
				continue
			}

			switch updatedRequest.Status {
			case "approved":
				log.Printf("Installation approved: %s", request.SoftwareName)
				return true, nil
			case "denied":
				log.Printf("Installation denied: %s - %s", request.SoftwareName, updatedRequest.AdminComment)
				return false, nil
			case "pending":
				// Continue waiting
				continue
			default:
				log.Printf("Unknown status: %s", updatedRequest.Status)
				continue
			}
		}
	}
}

// ProcessInstallEvent processes a Windows event that indicates installation activity
func (c *SoftwareControlCollector) ProcessInstallEvent(event *Event) *SoftwareInstallRequest {
	if !c.config.Enabled || !c.config.MonitorInstallers {
		return nil
	}

	// Check if this is an MSI install event
	// Event ID 1033 = MSI installation started
	// Event ID 1034 = MSI installation completed
	// Event ID 11707 = Installation completed successfully
	// Event ID 11708 = Installation failed

	var request *SoftwareInstallRequest

	switch event.EventID {
	case 1033: // MSI installation started
		request = &SoftwareInstallRequest{
			AgentID:       c.agentID,
			UserName:      event.SubjectUser,
			ComputerName:  c.hostname,
			SoftwareName:  extractFromEventMessage(event.Message, "ProductName"),
			Publisher:     extractFromEventMessage(event.Message, "Manufacturer"),
			InstallerPath: event.FilePath,
			Status:        "installing",
			RequestedAt:   event.Timestamp,
		}

	case 11707: // Installation completed successfully
		request = &SoftwareInstallRequest{
			AgentID:       c.agentID,
			UserName:      event.SubjectUser,
			ComputerName:  c.hostname,
			SoftwareName:  extractFromEventMessage(event.Message, "Product"),
			InstallerPath: event.FilePath,
			Status:        "installed",
			RequestedAt:   event.Timestamp,
		}

	case 11708: // Installation failed
		request = &SoftwareInstallRequest{
			AgentID:       c.agentID,
			UserName:      event.SubjectUser,
			ComputerName:  c.hostname,
			SoftwareName:  extractFromEventMessage(event.Message, "Product"),
			InstallerPath: event.FilePath,
			Status:        "failed",
			RequestedAt:   event.Timestamp,
		}
	}

	if request != nil && c.onInstallRequest != nil {
		if err := c.onInstallRequest(request); err != nil {
			log.Printf("Error sending install event to SIEM: %v", err)
		}
	}

	return request
}

// GetPendingRequests returns all pending approval requests
func (c *SoftwareControlCollector) GetPendingRequests() []*SoftwareInstallRequest {
	c.mutex.RLock()
	defer c.mutex.RUnlock()

	requests := make([]*SoftwareInstallRequest, 0, len(c.pendingRequests))
	for _, req := range c.pendingRequests {
		requests = append(requests, req)
	}
	return requests
}

// Stop stops the collector
func (c *SoftwareControlCollector) Stop() {
	c.cancel()
}

// Helper functions

func extractSoftwareName(filePath string) string {
	// Extract software name from file path
	base := filepath.Base(filePath)

	// Remove common installer suffixes
	name := base
	suffixes := []string{
		"_setup.exe", "_install.exe", "_installer.exe",
		"Setup.exe", "Install.exe", "Installer.exe",
		".msi", ".msp", ".exe",
	}

	for _, suffix := range suffixes {
		if strings.HasSuffix(strings.ToLower(name), strings.ToLower(suffix)) {
			name = name[:len(name)-len(suffix)]
			break
		}
	}

	// Clean up version numbers and underscores
	name = strings.ReplaceAll(name, "_", " ")
	name = strings.ReplaceAll(name, "-", " ")

	if name == "" {
		name = base
	}

	return strings.TrimSpace(name)
}

func extractFromEventMessage(message, key string) string {
	// Simple extraction from event message
	// Format: "Key: Value" or "Key=Value"

	patterns := []string{
		key + ": ",
		key + "=",
		key + " = ",
	}

	for _, pattern := range patterns {
		if idx := strings.Index(message, pattern); idx != -1 {
			start := idx + len(pattern)
			end := strings.IndexAny(message[start:], "\n\r,;")
			if end == -1 {
				end = len(message) - start
			}
			return strings.TrimSpace(message[start : start+end])
		}
	}

	return ""
}

// UserPrompt represents a prompt shown to user for installation approval
type UserPrompt struct {
	Title       string `json:"title"`
	Message     string `json:"message"`
	SoftwareName string `json:"software_name"`
	RequestID   string `json:"request_id"`
}

// CreateUserPrompt creates a prompt to show the user
func (c *SoftwareControlCollector) CreateUserPrompt(request *SoftwareInstallRequest) *UserPrompt {
	return &UserPrompt{
		Title:        "Запрос на установку ПО",
		Message:      fmt.Sprintf("Вы пытаетесь установить %s. Запрос отправлен администратору на согласование. Пожалуйста, дождитесь ответа или введите комментарий.", request.SoftwareName),
		SoftwareName: request.SoftwareName,
		RequestID:    request.RequestID,
	}
}

// ToJSON converts request to JSON
func (r *SoftwareInstallRequest) ToJSON() ([]byte, error) {
	return json.Marshal(r)
}
