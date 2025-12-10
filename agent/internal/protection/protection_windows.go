// +build windows

package protection

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/svc/mgr"
)

var (
	modadvapi32            = windows.NewLazySystemDLL("advapi32.dll")
	procSetServiceObjectSecurity = modadvapi32.NewProc("SetServiceObjectSecurityW")
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

// ProtectionManager handles agent self-protection
type ProtectionManager struct {
	config       *ProtectionConfig
	agentPath    string
	stopChan     chan struct{}
	alertHandler func(alertType, message string)
	fileHashes   map[string]string
}

// NewProtectionManager creates a new protection manager
func NewProtectionManager(config *ProtectionConfig, agentPath string) *ProtectionManager {
	return &ProtectionManager{
		config:     config,
		agentPath:  agentPath,
		stopChan:   make(chan struct{}),
		fileHashes: make(map[string]string),
	}
}

// SetAlertHandler sets the callback for alerts
func (pm *ProtectionManager) SetAlertHandler(handler func(alertType, message string)) {
	pm.alertHandler = handler
}

// Start starts the protection manager
func (pm *ProtectionManager) Start() error {
	if !pm.config.Enabled {
		return nil
	}

	log.Println("Starting protection manager...")

	// Apply file protection
	if pm.config.ProtectFiles {
		if err := pm.ApplyFileProtection(); err != nil {
			log.Printf("Warning: Could not apply file protection: %v", err)
		}
	}

	// Apply service protection
	if pm.config.ProtectService {
		if err := pm.ApplyServiceProtection("SIEMAgent"); err != nil {
			log.Printf("Warning: Could not apply service protection: %v", err)
		}
	}

	// Calculate initial file hashes for integrity monitoring
	if pm.config.MonitorTampering {
		pm.calculateFileHashes()
		go pm.monitorIntegrity()
	}

	log.Println("Protection manager started")
	return nil
}

// Stop stops the protection manager
func (pm *ProtectionManager) Stop() {
	close(pm.stopChan)
}

// ApplyFileProtection sets restrictive ACLs on agent files
func (pm *ProtectionManager) ApplyFileProtection() error {
	log.Println("Applying file protection...")

	// Files to protect
	filesToProtect := []string{
		filepath.Join(pm.agentPath, "siem-agent.exe"),
		filepath.Join(pm.agentPath, "config.yaml"),
		filepath.Join(pm.agentPath, "agent_id"),
	}

	for _, file := range filesToProtect {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			continue
		}

		if err := setRestrictiveACL(file); err != nil {
			log.Printf("Warning: Could not protect %s: %v", file, err)
		} else {
			log.Printf("Protected: %s", file)
		}
	}

	// Protect the entire directory
	if err := setRestrictiveACL(pm.agentPath); err != nil {
		log.Printf("Warning: Could not protect directory %s: %v", pm.agentPath, err)
	}

	return nil
}

// setRestrictiveACL sets ACL that only allows SYSTEM and Administrators
func setRestrictiveACL(path string) error {
	// Get SYSTEM SID
	systemSID, err := windows.CreateWellKnownSid(windows.WinLocalSystemSid)
	if err != nil {
		return fmt.Errorf("failed to create SYSTEM SID: %w", err)
	}

	// Get Administrators SID
	adminSID, err := windows.CreateWellKnownSid(windows.WinBuiltinAdministratorsSid)
	if err != nil {
		return fmt.Errorf("failed to create Administrators SID: %w", err)
	}

	// Create DACL with only SYSTEM and Administrators having full control
	// Everyone else is denied
	entries := []windows.EXPLICIT_ACCESS{
		{
			AccessPermissions: windows.GENERIC_ALL,
			AccessMode:        windows.SET_ACCESS,
			Inheritance:       windows.SUB_CONTAINERS_AND_OBJECTS_INHERIT,
			Trustee: windows.TRUSTEE{
				TrusteeForm:  windows.TRUSTEE_IS_SID,
				TrusteeType:  windows.TRUSTEE_IS_WELL_KNOWN_GROUP,
				TrusteeValue: windows.TrusteeValueFromSID(systemSID),
			},
		},
		{
			AccessPermissions: windows.GENERIC_ALL,
			AccessMode:        windows.SET_ACCESS,
			Inheritance:       windows.SUB_CONTAINERS_AND_OBJECTS_INHERIT,
			Trustee: windows.TRUSTEE{
				TrusteeForm:  windows.TRUSTEE_IS_SID,
				TrusteeType:  windows.TRUSTEE_IS_WELL_KNOWN_GROUP,
				TrusteeValue: windows.TrusteeValueFromSID(adminSID),
			},
		},
	}

	acl, err := windows.ACLFromEntries(entries, nil)
	if err != nil {
		return fmt.Errorf("failed to create ACL: %w", err)
	}

	// Apply the new DACL
	err = windows.SetNamedSecurityInfo(
		path,
		windows.SE_FILE_OBJECT,
		windows.DACL_SECURITY_INFORMATION|windows.PROTECTED_DACL_SECURITY_INFORMATION,
		nil,
		nil,
		acl,
		nil,
	)
	if err != nil {
		return fmt.Errorf("failed to set security info: %w", err)
	}

	return nil
}

// ApplyServiceProtection restricts who can control the service
func (pm *ProtectionManager) ApplyServiceProtection(serviceName string) error {
	log.Printf("Applying service protection to %s...", serviceName)

	m, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect to SCM: %w", err)
	}
	defer m.Disconnect()

	s, err := m.OpenService(serviceName)
	if err != nil {
		return fmt.Errorf("failed to open service: %w", err)
	}
	defer s.Close()

	// Create restrictive security descriptor
	// D: - DACL
	// (A;;CCLCSWRPWPDTLOCRRC;;;SY) - Allow SYSTEM: all service permissions
	// (A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA) - Allow Administrators: all permissions
	// (A;;CCLCSWLOCRRC;;;IU) - Allow Interactive Users: query status only
	// (A;;CCLCSWLOCRRC;;;SU) - Allow Service Users: query status only
	sdString := "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)"

	sd, err := windows.SecurityDescriptorFromString(sdString)
	if err != nil {
		return fmt.Errorf("failed to create security descriptor: %w", err)
	}

	// Get the DACL from the security descriptor
	dacl, _, err := sd.DACL()
	if err != nil {
		return fmt.Errorf("failed to get DACL: %w", err)
	}

	// Apply to service
	err = windows.SetSecurityInfo(
		windows.Handle(s.Handle),
		windows.SE_SERVICE,
		windows.DACL_SECURITY_INFORMATION,
		nil,
		nil,
		dacl,
		nil,
	)
	if err != nil {
		return fmt.Errorf("failed to set service security: %w", err)
	}

	log.Printf("Service protection applied to %s", serviceName)
	return nil
}

// calculateFileHashes calculates hashes of protected files
func (pm *ProtectionManager) calculateFileHashes() {
	files := []string{
		filepath.Join(pm.agentPath, "siem-agent.exe"),
		filepath.Join(pm.agentPath, "config.yaml"),
	}

	for _, file := range files {
		hash, err := calculateSHA256(file)
		if err != nil {
			continue
		}
		pm.fileHashes[file] = hash
	}
}

// monitorIntegrity monitors for file tampering
func (pm *ProtectionManager) monitorIntegrity() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-pm.stopChan:
			return
		case <-ticker.C:
			pm.checkIntegrity()
		}
	}
}

// checkIntegrity checks file integrity
func (pm *ProtectionManager) checkIntegrity() {
	for file, expectedHash := range pm.fileHashes {
		currentHash, err := calculateSHA256(file)
		if err != nil {
			// File might have been deleted
			pm.sendAlert("file_deleted", fmt.Sprintf("Protected file deleted: %s", file))
			continue
		}

		if currentHash != expectedHash {
			pm.sendAlert("file_modified", fmt.Sprintf("Protected file modified: %s", file))

			// Update hash to avoid repeated alerts
			pm.fileHashes[file] = currentHash

			// Self-heal if enabled
			if pm.config.SelfHealEnabled {
				pm.attemptSelfHeal(file)
			}
		}
	}

	// Check if agent service is running
	if pm.config.MonitorTampering {
		pm.checkServiceStatus()
	}
}

// checkServiceStatus checks if the agent service is running
func (pm *ProtectionManager) checkServiceStatus() {
	m, err := mgr.Connect()
	if err != nil {
		return
	}
	defer m.Disconnect()

	s, err := m.OpenService("SIEMAgent")
	if err != nil {
		pm.sendAlert("service_not_found", "SIEM Agent service not found")
		return
	}
	defer s.Close()

	status, err := s.Query()
	if err != nil {
		return
	}

	if status.State != 4 { // SERVICE_RUNNING = 4
		pm.sendAlert("service_stopped", "SIEM Agent service is not running")
	}
}

// attemptSelfHeal attempts to restore modified files
func (pm *ProtectionManager) attemptSelfHeal(file string) {
	log.Printf("Attempting self-heal for %s", file)
	// TODO: Implement restore from backup or re-download
}

// sendAlert sends a tampering alert
func (pm *ProtectionManager) sendAlert(alertType, message string) {
	log.Printf("PROTECTION ALERT [%s]: %s", alertType, message)

	if pm.alertHandler != nil {
		pm.alertHandler(alertType, message)
	}
}

// calculateSHA256 calculates SHA256 hash of a file
func calculateSHA256(filePath string) (string, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return "", err
	}

	// Use Windows CryptoAPI for SHA256
	var hProv uintptr
	var hHash uintptr

	// Constants
	const (
		PROV_RSA_AES        = 24
		CRYPT_VERIFYCONTEXT = 0xF0000000
		CALG_SHA_256        = 0x0000800c
		HP_HASHVAL          = 0x0002
	)

	advapi32 := syscall.MustLoadDLL("advapi32.dll")
	cryptAcquireContext := advapi32.MustFindProc("CryptAcquireContextW")
	cryptCreateHash := advapi32.MustFindProc("CryptCreateHash")
	cryptHashData := advapi32.MustFindProc("CryptHashData")
	cryptGetHashParam := advapi32.MustFindProc("CryptGetHashParam")
	cryptDestroyHash := advapi32.MustFindProc("CryptDestroyHash")
	cryptReleaseContext := advapi32.MustFindProc("CryptReleaseContext")

	ret, _, _ := cryptAcquireContext.Call(
		uintptr(unsafe.Pointer(&hProv)),
		0,
		0,
		PROV_RSA_AES,
		CRYPT_VERIFYCONTEXT,
	)
	if ret == 0 {
		return "", fmt.Errorf("CryptAcquireContext failed")
	}
	defer cryptReleaseContext.Call(hProv, 0)

	ret, _, _ = cryptCreateHash.Call(hProv, CALG_SHA_256, 0, 0, uintptr(unsafe.Pointer(&hHash)))
	if ret == 0 {
		return "", fmt.Errorf("CryptCreateHash failed")
	}
	defer cryptDestroyHash.Call(hHash)

	ret, _, _ = cryptHashData.Call(hHash, uintptr(unsafe.Pointer(&data[0])), uintptr(len(data)), 0)
	if ret == 0 {
		return "", fmt.Errorf("CryptHashData failed")
	}

	hashSize := uint32(32) // SHA256 = 32 bytes
	hash := make([]byte, hashSize)

	ret, _, _ = cryptGetHashParam.Call(hHash, HP_HASHVAL, uintptr(unsafe.Pointer(&hash[0])), uintptr(unsafe.Pointer(&hashSize)), 0)
	if ret == 0 {
		return "", fmt.Errorf("CryptGetHashParam failed")
	}

	return fmt.Sprintf("%x", hash), nil
}

// HideProcess attempts to hide the agent process (limited effectiveness)
func HideProcess() error {
	// This is a basic implementation - real hiding would require kernel driver
	// For now, just set process priority to below normal to be less noticeable
	handle, err := windows.GetCurrentProcess()
	if err != nil {
		return err
	}

	// Set below normal priority
	return windows.SetPriorityClass(handle, windows.BELOW_NORMAL_PRIORITY_CLASS)
}

// PreventDebugger attempts to detect and prevent debugging
func PreventDebugger() bool {
	// Check if debugger is present
	kernel32 := syscall.MustLoadDLL("kernel32.dll")
	isDebuggerPresent := kernel32.MustFindProc("IsDebuggerPresent")

	ret, _, _ := isDebuggerPresent.Call()
	if ret != 0 {
		return true // Debugger detected
	}

	// Check for remote debugger
	var isRemoteDebugger bool
	ntdll := syscall.MustLoadDLL("ntdll.dll")
	checkRemoteDebuggerPresent := kernel32.MustFindProc("CheckRemoteDebuggerPresent")

	handle, _ := windows.GetCurrentProcess()
	checkRemoteDebuggerPresent.Call(
		uintptr(handle),
		uintptr(unsafe.Pointer(&isRemoteDebugger)),
	)

	_ = ntdll // Silence unused warning
	return isRemoteDebugger
}

// MonitorParentProcess monitors if parent process changes unexpectedly
func MonitorParentProcess() (uint32, error) {
	handle, err := windows.GetCurrentProcess()
	if err != nil {
		return 0, err
	}

	var pbi windows.PROCESS_BASIC_INFORMATION
	var returnLength uint32

	ntdll := syscall.MustLoadDLL("ntdll.dll")
	ntQueryInformationProcess := ntdll.MustFindProc("NtQueryInformationProcess")

	ret, _, _ := ntQueryInformationProcess.Call(
		uintptr(handle),
		0, // ProcessBasicInformation
		uintptr(unsafe.Pointer(&pbi)),
		unsafe.Sizeof(pbi),
		uintptr(unsafe.Pointer(&returnLength)),
	)

	if ret != 0 {
		return 0, fmt.Errorf("NtQueryInformationProcess failed: %x", ret)
	}

	return uint32(pbi.InheritedFromUniqueProcessId), nil
}
