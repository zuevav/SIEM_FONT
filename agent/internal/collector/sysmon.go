package collector

import (
	"encoding/xml"
	"strconv"
	"strings"
	"time"
)

// SysmonEvent represents a Sysmon event with enhanced parsing
type SysmonEvent struct {
	EventID int
	*Event
}

// ParseSysmonEvent enhances event with Sysmon-specific parsing
func ParseSysmonEvent(event *Event) *Event {
	if event.SourceType != "Sysmon" {
		return event
	}

	// Parse based on Sysmon event ID
	switch event.EventCode {
	case 1: // Process creation
		parseSysmonProcessCreate(event)
	case 3: // Network connection
		parseSysmonNetworkConnect(event)
	case 5: // Process terminated
		parseSysmonProcessTerminate(event)
	case 7: // Image loaded
		parseSysmonImageLoad(event)
	case 8: // CreateRemoteThread
		parseSysmonCreateRemoteThread(event)
	case 10: // ProcessAccess
		parseSysmonProcessAccess(event)
	case 11: // FileCreate
		parseSysmonFileCreate(event)
	case 12, 13, 14: // Registry operations
		parseSysmonRegistry(event)
	case 15: // FileCreateStreamHash
		parseSysmonFileStream(event)
	case 17, 18: // Pipe operations
		parseSysmonPipe(event)
	case 19, 20, 21: // WMI operations
		parseSysmonWMI(event)
	case 22: // DNS query
		parseSysmonDNS(event)
	case 23: // File delete
		parseSysmonFileDelete(event)
	}

	return event
}

// parseSysmonProcessCreate parses Sysmon Event ID 1 (Process Creation)
func parseSysmonProcessCreate(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.ProcessCommandLine = event.EventData["CommandLine"]
	event.FileHash = event.EventData["Hashes"] // Format: SHA256=..., MD5=...

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	if ppid, err := strconv.Atoi(event.EventData["ParentProcessId"]); err == nil {
		event.ParentProcessID = ppid
	}

	event.ParentProcessName = extractFileName(event.EventData["ParentImage"])
	event.SubjectUser = event.EventData["User"]

	// Split domain\user
	if strings.Contains(event.SubjectUser, "\\") {
		parts := strings.SplitN(event.SubjectUser, "\\", 2)
		event.SubjectDomain = parts[0]
		event.SubjectUser = parts[1]
	}

	// Parse SHA256 from Hashes field
	if hashes := event.EventData["Hashes"]; hashes != "" {
		event.FileHash = extractSHA256(hashes)
	}

	event.Message = "Process created: " + event.ProcessName
	if event.ProcessCommandLine != "" {
		event.Message += " (" + event.ProcessCommandLine + ")"
	}
}

// parseSysmonNetworkConnect parses Sysmon Event ID 3 (Network Connection)
func parseSysmonNetworkConnect(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.SubjectUser = event.EventData["User"]

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	event.Protocol = event.EventData["Protocol"]
	event.SourceIP = event.EventData["SourceIp"]
	event.DestinationIP = event.EventData["DestinationIp"]
	event.SourceHostname = event.EventData["SourceHostname"]

	if port, err := strconv.Atoi(event.EventData["SourcePort"]); err == nil {
		event.SourcePort = port
	}
	if port, err := strconv.Atoi(event.EventData["DestinationPort"]); err == nil {
		event.DestinationPort = port
	}

	event.Message = "Network connection: " + event.ProcessName + " -> " +
		event.DestinationIP + ":" + strconv.Itoa(event.DestinationPort) +
		" (" + event.Protocol + ")"
}

// parseSysmonProcessTerminate parses Sysmon Event ID 5 (Process Terminated)
func parseSysmonProcessTerminate(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	event.Message = "Process terminated: " + event.ProcessName
}

// parseSysmonImageLoad parses Sysmon Event ID 7 (Image Loaded)
func parseSysmonImageLoad(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.FilePath = event.EventData["ImageLoaded"]

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	// Parse SHA256 from Hashes field
	if hashes := event.EventData["Hashes"]; hashes != "" {
		event.FileHash = extractSHA256(hashes)
	}

	event.Message = "Image loaded: " + event.FilePath + " by " + event.ProcessName
}

// parseSysmonCreateRemoteThread parses Sysmon Event ID 8 (CreateRemoteThread)
func parseSysmonCreateRemoteThread(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["SourceImage"]
	event.ProcessName = extractFileName(event.ProcessPath)

	if pid, err := strconv.Atoi(event.EventData["SourceProcessId"]); err == nil {
		event.ProcessID = pid
	}

	targetProcess := extractFileName(event.EventData["TargetImage"])
	event.Message = "Remote thread created: " + event.ProcessName + " -> " + targetProcess
}

// parseSysmonProcessAccess parses Sysmon Event ID 10 (Process Access)
func parseSysmonProcessAccess(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["SourceImage"]
	event.ProcessName = extractFileName(event.ProcessPath)

	if pid, err := strconv.Atoi(event.EventData["SourceProcessId"]); err == nil {
		event.ProcessID = pid
	}

	targetProcess := extractFileName(event.EventData["TargetImage"])
	event.AccessMask = event.EventData["GrantedAccess"]

	event.Message = "Process access: " + event.ProcessName + " -> " + targetProcess +
		" (Access: " + event.AccessMask + ")"
}

// parseSysmonFileCreate parses Sysmon Event ID 11 (File Created)
func parseSysmonFileCreate(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.FilePath = event.EventData["TargetFilename"]

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	event.Message = "File created: " + event.FilePath + " by " + event.ProcessName
}

// parseSysmonRegistry parses Sysmon Event IDs 12, 13, 14 (Registry operations)
func parseSysmonRegistry(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.RegistryPath = event.EventData["TargetObject"]

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	action := "modified"
	switch event.EventCode {
	case 12:
		action = "created/deleted"
	case 13:
		action = "set value"
		event.RegistryValue = event.EventData["Details"]
	case 14:
		action = "renamed"
	}

	event.Message = "Registry " + action + ": " + event.RegistryPath + " by " + event.ProcessName
}

// parseSysmonFileStream parses Sysmon Event ID 15 (File Stream)
func parseSysmonFileStream(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.FilePath = event.EventData["TargetFilename"]

	if hashes := event.EventData["Hash"]; hashes != "" {
		event.FileHash = extractSHA256(hashes)
	}

	event.Message = "File stream created: " + event.FilePath
}

// parseSysmonPipe parses Sysmon Event IDs 17, 18 (Pipe operations)
func parseSysmonPipe(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	pipeName := event.EventData["PipeName"]
	action := "created"
	if event.EventCode == 18 {
		action = "connected"
	}

	event.Message = "Pipe " + action + ": " + pipeName + " by " + event.ProcessName
}

// parseSysmonWMI parses Sysmon Event IDs 19, 20, 21 (WMI operations)
func parseSysmonWMI(event *Event) {
	if event.EventData == nil {
		return
	}

	action := "event filter"
	switch event.EventCode {
	case 20:
		action = "consumer"
	case 21:
		action = "consumer filter"
	}

	event.Message = "WMI " + action + " activity detected"
}

// parseSysmonDNS parses Sysmon Event ID 22 (DNS Query)
func parseSysmonDNS(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	queryName := event.EventData["QueryName"]
	queryResults := event.EventData["QueryResults"]

	event.Message = "DNS query: " + queryName + " by " + event.ProcessName
	if queryResults != "" {
		event.Message += " -> " + queryResults
	}
}

// parseSysmonFileDelete parses Sysmon Event ID 23 (File Delete)
func parseSysmonFileDelete(event *Event) {
	if event.EventData == nil {
		return
	}

	event.ProcessPath = event.EventData["Image"]
	event.ProcessName = extractFileName(event.ProcessPath)
	event.FilePath = event.EventData["TargetFilename"]

	if pid, err := strconv.Atoi(event.EventData["ProcessId"]); err == nil {
		event.ProcessID = pid
	}

	// Parse SHA256 from Hashes field
	if hashes := event.EventData["Hashes"]; hashes != "" {
		event.FileHash = extractSHA256(hashes)
	}

	event.Message = "File deleted: " + event.FilePath + " by " + event.ProcessName
}

// extractFileName extracts filename from full path
func extractFileName(path string) string {
	if path == "" {
		return ""
	}

	// Handle both forward and backslashes
	path = strings.ReplaceAll(path, "/", "\\")

	parts := strings.Split(path, "\\")
	return parts[len(parts)-1]
}

// extractSHA256 extracts SHA256 hash from Sysmon Hashes field
// Format: "SHA256=...,MD5=...,SHA1=..." or just "SHA256=..."
func extractSHA256(hashes string) string {
	if hashes == "" {
		return ""
	}

	// Split by comma
	parts := strings.Split(hashes, ",")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if strings.HasPrefix(strings.ToUpper(part), "SHA256=") {
			return strings.TrimPrefix(part, "SHA256=")
		}
	}

	// If only one hash provided, assume it's SHA256
	if !strings.Contains(hashes, "=") {
		return hashes
	}

	return ""
}
