package collector

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"siem-agent/internal/config"
)

// ScriptExecutor handles remote script execution from SIEM server
type ScriptExecutor struct {
	config     *config.Config
	httpClient *http.Client
}

// PendingScript represents a script waiting to be executed
type PendingScript struct {
	HasPending    bool              `json:"has_pending"`
	ExecutionGUID string            `json:"execution_guid"`
	ScriptType    string            `json:"script_type"`
	ScriptContent string            `json:"script_content"`
	Parameters    map[string]string `json:"parameters"`
	RequiresAdmin bool              `json:"requires_admin"`
	Timeout       int               `json:"timeout"`
}

// ExecutionResult represents the result of a script execution
type ExecutionResult struct {
	ExitCode    int    `json:"exit_code"`
	Output      string `json:"output"`
	ErrorOutput string `json:"error_output"`
	DurationMs  int64  `json:"duration_ms"`
}

// NewScriptExecutor creates a new script executor
func NewScriptExecutor(cfg *config.Config) *ScriptExecutor {
	return &ScriptExecutor{
		config: cfg,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Start begins the script execution polling loop
func (e *ScriptExecutor) Start(ctx context.Context) {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			e.checkAndExecutePendingScripts()
		}
	}
}

// checkAndExecutePendingScripts polls server for pending scripts and executes them
func (e *ScriptExecutor) checkAndExecutePendingScripts() {
	url := fmt.Sprintf("%s/ad/scripts/executions/pending/%s", e.config.ServerURL, e.config.AgentID)

	resp, err := e.httpClient.Get(url)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return
	}

	var pending PendingScript
	if err := json.Unmarshal(body, &pending); err != nil {
		return
	}

	if !pending.HasPending {
		return
	}

	// Execute the script
	result := e.executeScript(&pending)

	// Report result back to server
	e.reportResult(pending.ExecutionGUID, result)
}

// executeScript executes a script and returns the result
func (e *ScriptExecutor) executeScript(script *PendingScript) *ExecutionResult {
	startTime := time.Now()
	result := &ExecutionResult{}

	// Create temporary script file
	tempDir := os.TempDir()
	var scriptPath string
	var cmd *exec.Cmd

	switch script.ScriptType {
	case "powershell":
		scriptPath = filepath.Join(tempDir, fmt.Sprintf("siem_script_%s.ps1", script.ExecutionGUID[:8]))
		if err := ioutil.WriteFile(scriptPath, []byte(script.ScriptContent), 0600); err != nil {
			result.ErrorOutput = fmt.Sprintf("Failed to write script: %v", err)
			result.ExitCode = -1
			return result
		}

		// Build PowerShell command
		args := []string{
			"-NoProfile",
			"-NonInteractive",
			"-ExecutionPolicy", "Bypass",
			"-File", scriptPath,
		}

		// Add parameters
		for key, value := range script.Parameters {
			args = append(args, fmt.Sprintf("-%s", key), value)
		}

		if script.RequiresAdmin && runtime.GOOS == "windows" {
			cmd = exec.Command("powershell", args...)
		} else {
			cmd = exec.Command("powershell", args...)
		}

	case "batch":
		scriptPath = filepath.Join(tempDir, fmt.Sprintf("siem_script_%s.bat", script.ExecutionGUID[:8]))
		if err := ioutil.WriteFile(scriptPath, []byte(script.ScriptContent), 0600); err != nil {
			result.ErrorOutput = fmt.Sprintf("Failed to write script: %v", err)
			result.ExitCode = -1
			return result
		}

		cmd = exec.Command("cmd", "/C", scriptPath)

	case "python":
		scriptPath = filepath.Join(tempDir, fmt.Sprintf("siem_script_%s.py", script.ExecutionGUID[:8]))
		if err := ioutil.WriteFile(scriptPath, []byte(script.ScriptContent), 0600); err != nil {
			result.ErrorOutput = fmt.Sprintf("Failed to write script: %v", err)
			result.ExitCode = -1
			return result
		}

		cmd = exec.Command("python", scriptPath)

	default:
		result.ErrorOutput = fmt.Sprintf("Unsupported script type: %s", script.ScriptType)
		result.ExitCode = -1
		return result
	}

	// Clean up script file after execution
	defer os.Remove(scriptPath)

	// Set up output buffers
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	// Create context with timeout
	timeout := time.Duration(script.Timeout) * time.Second
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Start the command
	if err := cmd.Start(); err != nil {
		result.ErrorOutput = fmt.Sprintf("Failed to start command: %v", err)
		result.ExitCode = -1
		return result
	}

	// Wait for completion or timeout
	done := make(chan error)
	go func() {
		done <- cmd.Wait()
	}()

	select {
	case <-ctx.Done():
		cmd.Process.Kill()
		result.ErrorOutput = "Script execution timed out"
		result.ExitCode = -2
	case err := <-done:
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				result.ExitCode = exitErr.ExitCode()
			} else {
				result.ExitCode = -1
				result.ErrorOutput = err.Error()
			}
		} else {
			result.ExitCode = 0
		}
	}

	result.Output = truncateOutput(stdout.String(), 50000)
	if stderr.Len() > 0 {
		result.ErrorOutput = truncateOutput(stderr.String(), 10000)
	}
	result.DurationMs = time.Since(startTime).Milliseconds()

	return result
}

// reportResult sends execution result back to SIEM server
func (e *ScriptExecutor) reportResult(executionGUID string, result *ExecutionResult) {
	url := fmt.Sprintf("%s/ad/scripts/executions/%s/result", e.config.ServerURL, executionGUID)

	// Build query parameters
	params := fmt.Sprintf("?exit_code=%d&duration_ms=%d", result.ExitCode, result.DurationMs)
	if result.Output != "" {
		params += "&output=" + encodeURIComponent(result.Output)
	}
	if result.ErrorOutput != "" {
		params += "&error_output=" + encodeURIComponent(result.ErrorOutput)
	}

	resp, err := e.httpClient.Post(url+params, "application/json", nil)
	if err != nil {
		return
	}
	defer resp.Body.Close()
}

// truncateOutput limits output string to maxLen characters
func truncateOutput(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "\n... (truncated)"
}

// encodeURIComponent encodes a string for URL query parameters
func encodeURIComponent(s string) string {
	// Simple URL encoding for common characters
	s = strings.ReplaceAll(s, "%", "%25")
	s = strings.ReplaceAll(s, " ", "%20")
	s = strings.ReplaceAll(s, "\n", "%0A")
	s = strings.ReplaceAll(s, "\r", "%0D")
	s = strings.ReplaceAll(s, "&", "%26")
	s = strings.ReplaceAll(s, "=", "%3D")
	s = strings.ReplaceAll(s, "?", "%3F")
	return s
}
