//go:build windows

package collector

import (
	"fmt"
	"log"
	"strings"
	"time"

	"golang.org/x/sys/windows/registry"
	"golang.org/x/sys/windows/svc/mgr"
)

// InventoryCollector collects software and service inventory
type InventoryCollector struct {
	agentID  string
	hostname string
}

// NewInventoryCollector creates a new inventory collector
func NewInventoryCollector(agentID, hostname string) *InventoryCollector {
	return &InventoryCollector{
		agentID:  agentID,
		hostname: hostname,
	}
}

// CollectAll collects both software and services inventory
func (c *InventoryCollector) CollectAll() ([]*InventoryItem, error) {
	var items []*InventoryItem

	// Collect software
	software, err := c.CollectSoftware()
	if err != nil {
		log.Printf("Warning: Failed to collect software inventory: %v", err)
	} else {
		items = append(items, software...)
	}

	// Collect services
	services, err := c.CollectServices()
	if err != nil {
		log.Printf("Warning: Failed to collect services inventory: %v", err)
	} else {
		items = append(items, services...)
	}

	log.Printf("Collected %d inventory items (%d software, %d services)",
		len(items), len(software), len(services))

	return items, nil
}

// CollectSoftware collects installed software from registry
func (c *InventoryCollector) CollectSoftware() ([]*InventoryItem, error) {
	var items []*InventoryItem
	now := time.Now()

	// Check both 32-bit and 64-bit registry locations
	registryPaths := []struct {
		key  registry.Key
		path string
	}{
		// 64-bit software
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`},
		// 32-bit software on 64-bit Windows
		{registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall`},
		// Current user software
		{registry.CURRENT_USER, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`},
	}

	for _, regPath := range registryPaths {
		k, err := registry.OpenKey(regPath.key, regPath.path, registry.ENUMERATE_SUB_KEYS)
		if err != nil {
			continue // Key might not exist
		}

		subkeys, err := k.ReadSubKeyNames(-1)
		k.Close()
		if err != nil {
			continue
		}

		for _, subkey := range subkeys {
			item := c.readSoftwareKey(regPath.key, regPath.path+"\\"+subkey, now)
			if item != nil {
				items = append(items, item)
			}
		}
	}

	return items, nil
}

// readSoftwareKey reads software information from a registry key
func (c *InventoryCollector) readSoftwareKey(rootKey registry.Key, path string, collectedAt time.Time) *InventoryItem {
	k, err := registry.OpenKey(rootKey, path, registry.QUERY_VALUE)
	if err != nil {
		return nil
	}
	defer k.Close()

	// DisplayName is required
	displayName, _, err := k.GetStringValue("DisplayName")
	if err != nil || displayName == "" {
		return nil
	}

	// Skip Windows updates and system components
	if strings.Contains(displayName, "KB") || strings.Contains(displayName, "Update for") {
		return nil
	}

	systemComponent, _, _ := k.GetIntegerValue("SystemComponent")
	if systemComponent == 1 {
		return nil
	}

	item := &InventoryItem{
		AgentID:     c.agentID,
		Computer:    c.hostname,
		Type:        "software",
		Name:        displayName,
		CollectedAt: collectedAt,
	}

	// Optional fields
	if version, _, err := k.GetStringValue("DisplayVersion"); err == nil {
		item.Version = version
	}

	if publisher, _, err := k.GetStringValue("Publisher"); err == nil {
		item.Vendor = publisher
	}

	if installDate, _, err := k.GetStringValue("InstallDate"); err == nil {
		item.InstallDate = formatInstallDate(installDate)
	}

	if installLocation, _, err := k.GetStringValue("InstallLocation"); err == nil {
		item.InstallPath = installLocation
	}

	return item
}

// CollectServices collects Windows services
func (c *InventoryCollector) CollectServices() ([]*InventoryItem, error) {
	var items []*InventoryItem
	now := time.Now()

	// Connect to service control manager
	m, err := mgr.Connect()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to service manager: %w", err)
	}
	defer m.Disconnect()

	// List all services
	services, err := m.ListServices()
	if err != nil {
		return nil, fmt.Errorf("failed to list services: %w", err)
	}

	for _, serviceName := range services {
		item := c.readService(m, serviceName, now)
		if item != nil {
			items = append(items, item)
		}
	}

	return items, nil
}

// readService reads service information
func (c *InventoryCollector) readService(m *mgr.Mgr, serviceName string, collectedAt time.Time) *InventoryItem {
	s, err := m.OpenService(serviceName)
	if err != nil {
		return nil
	}
	defer s.Close()

	// Get service config
	cfg, err := s.Config()
	if err != nil {
		return nil
	}

	// Get service status
	status, err := s.Query()
	if err != nil {
		return nil
	}

	item := &InventoryItem{
		AgentID:     c.agentID,
		Computer:    c.hostname,
		Type:        "service",
		Name:        serviceName,
		Description: cfg.DisplayName,
		InstallPath: cfg.BinaryPathName,
		Status:      getServiceStatus(status.State),
		StartType:   getServiceStartType(cfg.StartType),
		CollectedAt: collectedAt,
	}

	// Service account
	if cfg.ServiceStartName != "" {
		item.Vendor = cfg.ServiceStartName // Reuse Vendor field for service account
	}

	return item
}

// getServiceStatus converts service state to string
func getServiceStatus(state uint32) string {
	switch state {
	case 1: // SERVICE_STOPPED
		return "Stopped"
	case 2: // SERVICE_START_PENDING
		return "Starting"
	case 3: // SERVICE_STOP_PENDING
		return "Stopping"
	case 4: // SERVICE_RUNNING
		return "Running"
	case 5: // SERVICE_CONTINUE_PENDING
		return "Continuing"
	case 6: // SERVICE_PAUSE_PENDING
		return "Pausing"
	case 7: // SERVICE_PAUSED
		return "Paused"
	default:
		return "Unknown"
	}
}

// getServiceStartType converts start type to string
func getServiceStartType(startType uint32) string {
	switch startType {
	case 0: // SERVICE_BOOT_START
		return "Boot"
	case 1: // SERVICE_SYSTEM_START
		return "System"
	case 2: // SERVICE_AUTO_START
		return "Automatic"
	case 3: // SERVICE_DEMAND_START
		return "Manual"
	case 4: // SERVICE_DISABLED
		return "Disabled"
	default:
		return "Unknown"
	}
}

// formatInstallDate formats install date from registry format (YYYYMMDD) to ISO format
func formatInstallDate(installDate string) string {
	if len(installDate) != 8 {
		return installDate
	}

	// YYYYMMDD -> YYYY-MM-DD
	return installDate[0:4] + "-" + installDate[4:6] + "-" + installDate[6:8]
}
