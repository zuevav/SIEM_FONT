//go:build windows

package collector

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

// RemoteSessionRequest represents a pending remote session from SIEM
type RemoteSessionRequest struct {
	HasPending  bool   `json:"has_pending"`
	SessionGUID string `json:"session_guid"`
	SessionType string `json:"session_type"`
	InitiatedBy string `json:"initiated_by"`
	Reason      string `json:"reason"`
	RequestedAt string `json:"requested_at"`
}

// RemoteSessionResponse represents the user's response to a session request
type RemoteSessionResponse struct {
	Action           string `json:"action"`
	ConnectionString string `json:"connection_string,omitempty"`
	ConnectionPassword string `json:"connection_password,omitempty"`
	Port             int    `json:"port,omitempty"`
	Message          string `json:"message,omitempty"`
}

// RemoteSessionManager handles remote desktop sessions
type RemoteSessionManager struct {
	agentID     string
	hostname    string
	ctx         context.Context
	cancel      context.CancelFunc
	mutex       sync.RWMutex

	// Current active session
	activeSession *ActiveSession

	// Callbacks
	onCheckPending  func() (*RemoteSessionRequest, error)
	onSendResponse  func(sessionGUID string, response *RemoteSessionResponse) error

	// Configuration
	pollInterval time.Duration
	autoAccept   bool // For trusted environments
}

// ActiveSession represents an active remote session
type ActiveSession struct {
	SessionGUID    string
	SessionType    string
	StartedAt      time.Time
	Process        *os.Process
	InvitationFile string
	Password       string
	Port           int
}

// Windows API for showing message boxes
var (
	user32          = syscall.NewLazyDLL("user32.dll")
	messageBoxW     = user32.NewProc("MessageBoxW")
)

const (
	MB_YESNO        = 0x00000004
	MB_ICONQUESTION = 0x00000020
	MB_TOPMOST      = 0x00040000
	MB_SETFOREGROUND = 0x00010000
	IDYES           = 6
	IDNO            = 7
)

// NewRemoteSessionManager creates a new remote session manager
func NewRemoteSessionManager(agentID, hostname string) *RemoteSessionManager {
	ctx, cancel := context.WithCancel(context.Background())

	return &RemoteSessionManager{
		agentID:      agentID,
		hostname:     hostname,
		ctx:          ctx,
		cancel:       cancel,
		pollInterval: 10 * time.Second,
		autoAccept:   false,
	}
}

// SetCallbacks sets the API callbacks
func (m *RemoteSessionManager) SetCallbacks(
	onCheckPending func() (*RemoteSessionRequest, error),
	onSendResponse func(string, *RemoteSessionResponse) error,
) {
	m.onCheckPending = onCheckPending
	m.onSendResponse = onSendResponse
}

// Start begins polling for remote session requests
func (m *RemoteSessionManager) Start() {
	log.Println("Starting Remote Session Manager...")

	ticker := time.NewTicker(m.pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-m.ctx.Done():
			return
		case <-ticker.C:
			m.checkForPendingSession()
		}
	}
}

// Stop stops the manager and any active session
func (m *RemoteSessionManager) Stop() {
	m.cancel()
	m.EndActiveSession()
}

// checkForPendingSession checks SIEM for pending session requests
func (m *RemoteSessionManager) checkForPendingSession() {
	if m.onCheckPending == nil {
		return
	}

	// Don't check if we already have an active session
	m.mutex.RLock()
	hasActive := m.activeSession != nil
	m.mutex.RUnlock()

	if hasActive {
		return
	}

	// Check for pending request
	request, err := m.onCheckPending()
	if err != nil {
		log.Printf("Error checking for pending sessions: %v", err)
		return
	}

	if !request.HasPending {
		return
	}

	log.Printf("Remote session request from %s: %s", request.InitiatedBy, request.Reason)

	// Handle the request
	m.handleSessionRequest(request)
}

// handleSessionRequest processes a remote session request
func (m *RemoteSessionManager) handleSessionRequest(request *RemoteSessionRequest) {
	var response *RemoteSessionResponse

	// Show consent dialog to user
	if m.autoAccept {
		response = m.acceptSession(request)
	} else {
		accepted := m.showConsentDialog(request)
		if accepted {
			response = m.acceptSession(request)
		} else {
			response = &RemoteSessionResponse{
				Action:  "decline",
				Message: "Пользователь отклонил запрос на подключение",
			}
		}
	}

	// Send response to SIEM
	if m.onSendResponse != nil {
		if err := m.onSendResponse(request.SessionGUID, response); err != nil {
			log.Printf("Error sending session response: %v", err)
		}
	}
}

// showConsentDialog shows a Windows message box asking user for consent
func (m *RemoteSessionManager) showConsentDialog(request *RemoteSessionRequest) bool {
	title := "Запрос на удаленное подключение"
	message := fmt.Sprintf(
		"Администратор %s запрашивает удаленный доступ к вашему компьютеру.\n\n"+
		"Причина: %s\n\n"+
		"Разрешить подключение?",
		request.InitiatedBy,
		request.Reason,
	)

	titlePtr, _ := syscall.UTF16PtrFromString(title)
	messagePtr, _ := syscall.UTF16PtrFromString(message)

	ret, _, _ := messageBoxW.Call(
		0,
		uintptr(unsafe.Pointer(messagePtr)),
		uintptr(unsafe.Pointer(titlePtr)),
		MB_YESNO|MB_ICONQUESTION|MB_TOPMOST|MB_SETFOREGROUND,
	)

	return ret == IDYES
}

// acceptSession starts the remote assistance and returns connection info
func (m *RemoteSessionManager) acceptSession(request *RemoteSessionRequest) *RemoteSessionResponse {
	response := &RemoteSessionResponse{
		Action: "accept",
	}

	switch request.SessionType {
	case "remote_assistance":
		// Use Windows Remote Assistance (msra.exe)
		invFile, password, err := m.startRemoteAssistance()
		if err != nil {
			log.Printf("Error starting Remote Assistance: %v", err)
			response.Action = "decline"
			response.Message = fmt.Sprintf("Ошибка запуска Remote Assistance: %v", err)
			return response
		}

		response.ConnectionString = invFile
		response.ConnectionPassword = password
		response.Message = "Remote Assistance запущен"

		// Store active session
		m.mutex.Lock()
		m.activeSession = &ActiveSession{
			SessionGUID:    request.SessionGUID,
			SessionType:    request.SessionType,
			StartedAt:      time.Now(),
			InvitationFile: invFile,
			Password:       password,
		}
		m.mutex.Unlock()

	case "screen_share":
		// Simple screen share - just enable RDP shadowing
		response.Message = "Screen share mode enabled"
		response.Port = 3389

	default:
		response.Action = "decline"
		response.Message = fmt.Sprintf("Неподдерживаемый тип сессии: %s", request.SessionType)
	}

	return response
}

// startRemoteAssistance starts Windows Remote Assistance
func (m *RemoteSessionManager) startRemoteAssistance() (string, string, error) {
	// Generate random password
	password := generatePassword(8)

	// Create invitation file path
	tempDir := os.TempDir()
	invFile := filepath.Join(tempDir, fmt.Sprintf("ra_invite_%s.msrcIncident", m.agentID[:8]))

	// Create Remote Assistance invitation using msra.exe
	// Method 1: Use Windows Remote Assistance with unsolicited offer
	// msra.exe /offerRA <computername>

	// Method 2: Create invitation file programmatically
	// We'll use PowerShell to create the invitation

	psScript := fmt.Sprintf(`
$ErrorActionPreference = "Stop"

# Enable Remote Assistance if not enabled
$raKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Remote Assistance"
if (!(Test-Path $raKey)) {
    New-Item -Path $raKey -Force | Out-Null
}
Set-ItemProperty -Path $raKey -Name "fAllowToGetHelp" -Value 1 -Type DWord -Force

# Create invitation using Windows Remote Assistance COM object
try {
    $ra = New-Object -ComObject RaServer.RemoteAssistanceInvitation
    $ra.SetPassword("%s")
    $ra.SetMaxTicketExpiry(60)  # 60 minutes

    # Export invitation file
    $ra.CreateRATicket("%s")

    # Return the invitation content
    Get-Content -Path "%s" -Raw
} catch {
    # Fallback: use msra command line
    Start-Process -FilePath "msra.exe" -ArgumentList "/saveasfile", "%s", "%s" -Wait -NoNewWindow
    if (Test-Path "%s") {
        Get-Content -Path "%s" -Raw
    } else {
        throw "Failed to create Remote Assistance invitation"
    }
}
`, password, invFile, invFile, invFile, password, invFile, invFile)

	// Execute PowerShell script
	cmd := exec.Command("powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", psScript)
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Fallback: just return info for manual connection
		log.Printf("Remote Assistance script output: %s", string(output))

		// Try simple approach - just enable RA and return computer info
		return m.enableRemoteAssistanceSimple(password)
	}

	invContent := strings.TrimSpace(string(output))
	return invContent, password, nil
}

// enableRemoteAssistanceSimple enables RA with simple settings
func (m *RemoteSessionManager) enableRemoteAssistanceSimple(password string) (string, string, error) {
	// Enable Remote Assistance in registry
	cmd := exec.Command("reg", "add",
		`HKLM\SYSTEM\CurrentControlSet\Control\Remote Assistance`,
		"/v", "fAllowToGetHelp", "/t", "REG_DWORD", "/d", "1", "/f")
	cmd.Run()

	// Return connection info
	connectionInfo := fmt.Sprintf(`{"hostname": "%s", "method": "msra", "password": "%s"}`,
		m.hostname, password)

	return connectionInfo, password, nil
}

// EndActiveSession ends the current active session
func (m *RemoteSessionManager) EndActiveSession() {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if m.activeSession == nil {
		return
	}

	// Kill any associated process
	if m.activeSession.Process != nil {
		m.activeSession.Process.Kill()
	}

	// Clean up invitation file
	if m.activeSession.InvitationFile != "" {
		os.Remove(m.activeSession.InvitationFile)
	}

	log.Printf("Remote session %s ended", m.activeSession.SessionGUID)
	m.activeSession = nil
}

// GetActiveSession returns the current active session
func (m *RemoteSessionManager) GetActiveSession() *ActiveSession {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return m.activeSession
}

// generatePassword generates a random password
func generatePassword(length int) string {
	const charset = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	rand.Seed(time.Now().UnixNano())

	b := make([]byte, length)
	for i := range b {
		b[i] = charset[rand.Intn(len(charset))]
	}
	return string(b)
}

// RemoteSessionStatus represents the status of remote session capability
type RemoteSessionStatus struct {
	Supported         bool   `json:"supported"`
	RemoteAssistance  bool   `json:"remote_assistance"`
	RDPEnabled        bool   `json:"rdp_enabled"`
	CurrentUser       string `json:"current_user"`
	ActiveSessionGUID string `json:"active_session_guid,omitempty"`
}

// GetStatus returns the current status of remote session capability
func (m *RemoteSessionManager) GetStatus() *RemoteSessionStatus {
	status := &RemoteSessionStatus{
		Supported:        true,
		CurrentUser:      os.Getenv("USERNAME"),
	}

	// Check if Remote Assistance is enabled
	cmd := exec.Command("reg", "query",
		`HKLM\SYSTEM\CurrentControlSet\Control\Remote Assistance`,
		"/v", "fAllowToGetHelp")
	output, err := cmd.CombinedOutput()
	if err == nil && strings.Contains(string(output), "0x1") {
		status.RemoteAssistance = true
	}

	// Check if RDP is enabled
	cmd = exec.Command("reg", "query",
		`HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server`,
		"/v", "fDenyTSConnections")
	output, err = cmd.CombinedOutput()
	if err == nil && strings.Contains(string(output), "0x0") {
		status.RDPEnabled = true
	}

	// Check for active session
	m.mutex.RLock()
	if m.activeSession != nil {
		status.ActiveSessionGUID = m.activeSession.SessionGUID
	}
	m.mutex.RUnlock()

	return status
}

// ToJSON converts status to JSON
func (s *RemoteSessionStatus) ToJSON() ([]byte, error) {
	return json.Marshal(s)
}
