package collector

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"siem-agent/internal/config"
)

// AppStoreClient handles client-side app store operations
type AppStoreClient struct {
	config     *config.Config
	httpClient *http.Client
}

// StoreApp represents an app from the store
type StoreApp struct {
	AppID          int    `json:"app_id"`
	AppGUID        string `json:"app_guid"`
	Name           string `json:"name"`
	DisplayName    string `json:"display_name"`
	Description    string `json:"description"`
	Publisher      string `json:"publisher"`
	Version        string `json:"version"`
	Category       string `json:"category"`
	AppType        string `json:"app_type"`
	IconURL        string `json:"icon_url"`
	IsFeatured     bool   `json:"is_featured"`
	RequiresReboot bool   `json:"requires_reboot"`
	CanInstall     bool   `json:"can_install"`
	RequestStatus  string `json:"request_status"`
	RequestID      int    `json:"request_id"`
}

// InstallRequest represents a request to install an app
type InstallRequest struct {
	AppID           int    `json:"app_id"`
	AgentID         string `json:"agent_id"`
	ComputerName    string `json:"computer_name"`
	UserName        string `json:"user_name"`
	UserDisplayName string `json:"user_display_name"`
	UserDepartment  string `json:"user_department"`
	RequestReason   string `json:"request_reason"`
}

// InstallRequestResponse represents the response after creating an install request
type InstallRequestResponse struct {
	RequestID   int         `json:"request_id"`
	RequestGUID string      `json:"request_guid"`
	Status      string      `json:"status"`
	CanInstall  bool        `json:"can_install"`
	Message     string      `json:"message"`
	InstallInfo *InstallInfo `json:"install_info"`
}

// InstallInfo contains information needed to install an app
type InstallInfo struct {
	InstallerType     string `json:"installer_type"`
	InstallerURL      string `json:"installer_url"`
	InstallerPath     string `json:"installer_path"`
	SilentInstallArgs string `json:"silent_install_args"`
}

// NewAppStoreClient creates a new app store client
func NewAppStoreClient(cfg *config.Config) *AppStoreClient {
	return &AppStoreClient{
		config: cfg,
		httpClient: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// GetApps retrieves available apps from the store
func (c *AppStoreClient) GetApps(category string) ([]StoreApp, error) {
	url := fmt.Sprintf("%s/ad/appstore/apps/client?agent_id=%s", c.config.ServerURL, c.config.AgentID)
	if category != "" {
		url += "&category=" + category
	}

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch apps: %v", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	var apps []StoreApp
	if err := json.Unmarshal(body, &apps); err != nil {
		return nil, fmt.Errorf("failed to parse apps: %v", err)
	}

	return apps, nil
}

// RequestInstall creates a request to install an app
func (c *AppStoreClient) RequestInstall(appID int, userName, displayName, department, reason string) (*InstallRequestResponse, error) {
	url := fmt.Sprintf("%s/ad/appstore/requests", c.config.ServerURL)

	hostname, _ := os.Hostname()

	request := InstallRequest{
		AppID:           appID,
		AgentID:         c.config.AgentID,
		ComputerName:    hostname,
		UserName:        userName,
		UserDisplayName: displayName,
		UserDepartment:  department,
		RequestReason:   reason,
	}

	jsonData, err := json.Marshal(request)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	var response InstallRequestResponse
	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response: %v", err)
	}

	return &response, nil
}

// CheckRequestStatus checks the status of an install request
func (c *AppStoreClient) CheckRequestStatus(requestID int) (*InstallRequestResponse, error) {
	url := fmt.Sprintf("%s/ad/appstore/requests/%d/status", c.config.ServerURL, requestID)

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to check status: %v", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	var response InstallRequestResponse
	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response: %v", err)
	}

	return &response, nil
}

// InstallApp downloads and installs an app
func (c *AppStoreClient) InstallApp(requestID int, installInfo *InstallInfo) error {
	// Determine installer source
	var installerPath string
	var cleanup bool

	if installInfo.InstallerPath != "" {
		// Use UNC path directly
		installerPath = installInfo.InstallerPath
		cleanup = false
	} else if installInfo.InstallerURL != "" {
		// Download from URL
		tempDir := os.TempDir()
		installerPath = filepath.Join(tempDir, fmt.Sprintf("siem_app_%d.%s", requestID, installInfo.InstallerType))
		cleanup = true

		if err := c.downloadFile(installInfo.InstallerURL, installerPath); err != nil {
			return fmt.Errorf("failed to download installer: %v", err)
		}
	} else {
		return fmt.Errorf("no installer source specified")
	}

	if cleanup {
		defer os.Remove(installerPath)
	}

	// Execute installer
	var cmd *exec.Cmd
	args := installInfo.SilentInstallArgs

	switch installInfo.InstallerType {
	case "msi":
		cmdArgs := []string{"/i", installerPath, "/qn", "/norestart"}
		if args != "" {
			cmdArgs = append(cmdArgs, args)
		}
		cmd = exec.Command("msiexec", cmdArgs...)

	case "exe":
		cmdArgs := []string{}
		if args != "" {
			cmdArgs = append(cmdArgs, args)
		}
		cmd = exec.Command(installerPath, cmdArgs...)

	case "msix":
		cmd = exec.Command("powershell", "-Command", fmt.Sprintf("Add-AppxPackage -Path '%s'", installerPath))

	case "script":
		cmd = exec.Command("powershell", "-ExecutionPolicy", "Bypass", "-File", installerPath)

	default:
		return fmt.Errorf("unsupported installer type: %s", installInfo.InstallerType)
	}

	// Set up output capture
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	// Execute with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start installer: %v", err)
	}

	done := make(chan error)
	go func() {
		done <- cmd.Wait()
	}()

	var exitCode int
	var output string

	select {
	case <-ctx.Done():
		cmd.Process.Kill()
		exitCode = -2
		output = "Installation timed out"
	case err := <-done:
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				exitCode = exitErr.ExitCode()
			} else {
				exitCode = -1
			}
		}
		output = stdout.String()
		if stderr.Len() > 0 {
			output += "\nErrors:\n" + stderr.String()
		}
	}

	// Report installation result
	c.reportInstallation(requestID, exitCode, output)

	if exitCode != 0 {
		return fmt.Errorf("installation failed with exit code %d: %s", exitCode, output)
	}

	return nil
}

// downloadFile downloads a file from URL to local path
func (c *AppStoreClient) downloadFile(url, destPath string) error {
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download failed with status: %d", resp.StatusCode)
	}

	out, err := os.Create(destPath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

// reportInstallation reports the installation result to the server
func (c *AppStoreClient) reportInstallation(requestID int, exitCode int, output string) {
	url := fmt.Sprintf("%s/ad/appstore/requests/%d/installed?exit_code=%d",
		c.config.ServerURL, requestID, exitCode)

	if output != "" {
		// Truncate output if too long
		if len(output) > 5000 {
			output = output[:5000] + "... (truncated)"
		}
		url += "&output=" + encodeURIComponent(output)
	}

	resp, err := c.httpClient.Post(url, "application/json", nil)
	if err != nil {
		return
	}
	defer resp.Body.Close()
}

// PollForApproval polls server for approval status and installs when approved
func (c *AppStoreClient) PollForApproval(ctx context.Context, requestID int, onApproved func(*InstallInfo) error) error {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			status, err := c.CheckRequestStatus(requestID)
			if err != nil {
				continue
			}

			switch status.Status {
			case "approved":
				if status.InstallInfo != nil {
					return onApproved(status.InstallInfo)
				}
			case "denied":
				return fmt.Errorf("installation request was denied: %s", status.Message)
			case "installed":
				return nil
			case "failed":
				return fmt.Errorf("installation failed")
			}
		}
	}
}
