package agent

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/siem/agent/internal/collector"
	"github.com/siem/agent/internal/config"
	"github.com/siem/agent/internal/sender"
	"github.com/siem/agent/internal/sysinfo"
)

// Agent represents the SIEM agent
type Agent struct {
	config      *config.Config
	version     string
	agentID     string
	hostname    string
	ctx         context.Context
	cancel      context.CancelFunc
	wg          sync.WaitGroup

	// Components
	eventCollector *collector.EventLogCollector
	inventoryCollector *collector.InventoryCollector
	apiClient      *sender.APIClient

	// Event queue
	eventQueue     chan *collector.Event
	mutex          sync.RWMutex

	// Statistics
	stats          Stats
}

// Stats holds agent statistics
type Stats struct {
	EventsCollected  uint64
	EventsSent       uint64
	EventsFailed     uint64
	LastHeartbeat    time.Time
	LastInventory    time.Time
	Uptime           time.Time
}

// New creates a new agent instance
func New(cfg *config.Config, version string) (*Agent, error) {
	hostname, err := sysinfo.GetHostname()
	if err != nil {
		return nil, fmt.Errorf("failed to get hostname: %w", err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	// Create API client
	apiClient, err := sender.NewAPIClient(cfg.SIEM.APIURL, cfg.Advanced.RetryAttempts)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create API client: %w", err)
	}

	// Create event collector
	eventCollector, err := collector.NewEventLogCollector(&cfg.EventLog, &cfg.Sysmon)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create event collector: %w", err)
	}

	// Create inventory collector
	inventoryCollector := collector.NewInventoryCollector(&cfg.Inventory)

	agent := &Agent{
		config:             cfg,
		version:            version,
		hostname:           hostname,
		ctx:                ctx,
		cancel:             cancel,
		eventCollector:     eventCollector,
		inventoryCollector: inventoryCollector,
		apiClient:          apiClient,
		eventQueue:         make(chan *collector.Event, cfg.SIEM.MaxQueueSize),
		stats: Stats{
			Uptime: time.Now(),
		},
	}

	return agent, nil
}

// Start starts the agent
func (a *Agent) Start() error {
	log.Printf("Starting SIEM Agent v%s", a.version)
	log.Printf("Hostname: %s", a.hostname)
	log.Printf("SIEM API: %s", a.config.SIEM.APIURL)

	// Register agent with SIEM server
	if a.config.SIEM.RegisterOnStartup {
		if err := a.register(); err != nil {
			log.Printf("Warning: Failed to register agent: %v", err)
			log.Printf("Agent will continue without registration")
		} else {
			log.Printf("✓ Agent registered successfully (ID: %s)", a.agentID)
		}
	}

	// Start event collector
	if a.config.EventLog.Enabled {
		a.wg.Add(1)
		go a.collectEvents()
	}

	// Start event sender
	a.wg.Add(1)
	go a.sendEvents()

	// Start heartbeat
	a.wg.Add(1)
	go a.heartbeat()

	// Start inventory scanner
	if a.config.Inventory.Enabled {
		a.wg.Add(1)
		go a.scanInventory()
	}

	log.Println("✓ SIEM Agent started successfully")

	// Wait for shutdown
	a.wg.Wait()
	return nil
}

// Stop stops the agent
func (a *Agent) Stop() error {
	log.Println("Stopping SIEM Agent...")

	// Cancel context
	a.cancel()

	// Wait for goroutines to finish (with timeout)
	done := make(chan struct{})
	go func() {
		a.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Println("✓ Agent stopped gracefully")
	case <-time.After(10 * time.Second):
		log.Println("⚠ Agent stop timeout, forcing shutdown")
	}

	// Close event queue
	close(a.eventQueue)

	return nil
}

// register registers the agent with SIEM server
func (a *Agent) register() error {
	sysInfo, err := sysinfo.Gather()
	if err != nil {
		return fmt.Errorf("failed to gather system info: %w", err)
	}

	registration := &sender.AgentRegistration{
		Hostname:         a.hostname,
		FQDN:             sysInfo.FQDN,
		IPAddress:        sysInfo.IPAddress,
		MACAddress:       sysInfo.MACAddress,
		OSVersion:        sysInfo.OSVersion,
		OSBuild:          sysInfo.OSBuild,
		OSArchitecture:   sysInfo.Architecture,
		Domain:           sysInfo.Domain,
		CPUModel:         sysInfo.CPUModel,
		CPUCores:         sysInfo.CPUCores,
		TotalRAM_MB:      sysInfo.TotalRAM_MB,
		TotalDisk_GB:     sysInfo.TotalDisk_GB,
		AgentVersion:     a.version,
		CriticalityLevel: a.config.Agent.Criticality,
		Location:         a.config.Agent.Location,
		Owner:            a.config.Agent.Owner,
		Tags:             a.config.Agent.Tags,
	}

	resp, err := a.apiClient.RegisterAgent(a.ctx, registration)
	if err != nil {
		return err
	}

	a.agentID = resp.AgentID
	return nil
}

// collectEvents collects events from Windows Event Log
func (a *Agent) collectEvents() {
	defer a.wg.Done()

	log.Println("Starting event collection...")

	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-a.ctx.Done():
			return
		case <-ticker.C:
			events, err := a.eventCollector.Collect()
			if err != nil {
				log.Printf("Error collecting events: %v", err)
				continue
			}

			for _, event := range events {
				// Add agent ID to event
				event.AgentID = a.agentID

				// Send to queue
				select {
				case a.eventQueue <- event:
					a.mutex.Lock()
					a.stats.EventsCollected++
					a.mutex.Unlock()
				default:
					log.Println("Warning: Event queue full, dropping event")
				}
			}
		}
	}
}

// sendEvents sends collected events to SIEM server
func (a *Agent) sendEvents() {
	defer a.wg.Done()

	log.Println("Starting event sender...")

	batch := make([]*collector.Event, 0, a.config.SIEM.BatchSize)
	ticker := time.NewTicker(time.Duration(a.config.SIEM.SendInterval) * time.Second)
	defer ticker.Stop()

	sendBatch := func() {
		if len(batch) == 0 {
			return
		}

		// Convert to API format
		apiEvents := make([]sender.EventData, len(batch))
		for i, event := range batch {
			apiEvents[i] = sender.EventData{
				AgentID:           event.AgentID,
				EventTime:         event.Timestamp,
				SourceType:        event.SourceType,
				EventCode:         event.EventID,
				Severity:          event.Severity,
				Computer:          event.Computer,
				Message:           event.Message,
				SubjectUser:       event.SubjectUser,
				SubjectDomain:     event.SubjectDomain,
				TargetUser:        event.TargetUser,
				ProcessName:       event.ProcessName,
				ProcessCommandLine: event.CommandLine,
				SourceIP:          event.SourceIP,
				DestinationIP:     event.DestinationIP,
				FilePath:          event.FilePath,
				RegistryPath:      event.RegistryPath,
				RawEvent:          event.RawData,
			}
		}

		// Send to SIEM
		if err := a.apiClient.SendEvents(a.ctx, apiEvents); err != nil {
			log.Printf("Error sending events: %v", err)
			a.mutex.Lock()
			a.stats.EventsFailed += uint64(len(batch))
			a.mutex.Unlock()
		} else {
			a.mutex.Lock()
			a.stats.EventsSent += uint64(len(batch))
			a.mutex.Unlock()
			log.Printf("✓ Sent %d events to SIEM", len(batch))
		}

		// Clear batch
		batch = batch[:0]
	}

	for {
		select {
		case <-a.ctx.Done():
			// Send remaining events
			sendBatch()
			return

		case event, ok := <-a.eventQueue:
			if !ok {
				return
			}
			batch = append(batch, event)

			// Send if batch is full
			if len(batch) >= a.config.SIEM.BatchSize {
				sendBatch()
			}

		case <-ticker.C:
			// Send batch periodically
			sendBatch()
		}
	}
}

// heartbeat sends periodic heartbeat to SIEM server
func (a *Agent) heartbeat() {
	defer a.wg.Done()

	log.Println("Starting heartbeat...")

	ticker := time.NewTicker(time.Duration(a.config.SIEM.HeartbeatInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-a.ctx.Done():
			return
		case <-ticker.C:
			if a.agentID == "" {
				continue // Not registered yet
			}

			sysInfo, _ := sysinfo.Gather()

			heartbeat := &sender.Heartbeat{
				AgentID:      a.agentID,
				Status:       "online",
				IPAddress:    sysInfo.IPAddress,
				AgentVersion: a.version,
			}

			if err := a.apiClient.SendHeartbeat(a.ctx, heartbeat); err != nil {
				log.Printf("Error sending heartbeat: %v", err)
			} else {
				a.mutex.Lock()
				a.stats.LastHeartbeat = time.Now()
				a.mutex.Unlock()
			}
		}
	}
}

// scanInventory performs periodic inventory scans
func (a *Agent) scanInventory() {
	defer a.wg.Done()

	log.Println("Starting inventory scanner...")

	// Perform initial full scan
	if err := a.performFullInventoryScan(); err != nil {
		log.Printf("Error performing initial inventory scan: %v", err)
	}

	fullScanTicker := time.NewTicker(time.Duration(a.config.Inventory.FullScanInterval) * time.Second)
	defer fullScanTicker.Stop()

	quickScanTicker := time.NewTicker(time.Duration(a.config.Inventory.QuickScanInterval) * time.Second)
	defer quickScanTicker.Stop()

	for {
		select {
		case <-a.ctx.Done():
			return
		case <-fullScanTicker.C:
			if err := a.performFullInventoryScan(); err != nil {
				log.Printf("Error performing full inventory scan: %v", err)
			}
		case <-quickScanTicker.C:
			// Quick scan - only check for changes
			// TODO: Implement incremental inventory scan
		}
	}
}

// performFullInventoryScan performs a full inventory scan
func (a *Agent) performFullInventoryScan() error {
	if a.agentID == "" {
		return nil // Not registered yet
	}

	log.Println("Performing full inventory scan...")

	// Collect software inventory
	if a.config.Inventory.CollectSoftware {
		software, err := a.inventoryCollector.CollectSoftware()
		if err != nil {
			log.Printf("Error collecting software inventory: %v", err)
		} else if len(software) > 0 {
			if err := a.apiClient.SendSoftwareInventory(a.ctx, a.agentID, software); err != nil {
				log.Printf("Error sending software inventory: %v", err)
			} else {
				log.Printf("✓ Sent software inventory (%d items)", len(software))
			}
		}
	}

	// Collect services inventory
	if a.config.Inventory.CollectServices {
		services, err := a.inventoryCollector.CollectServices()
		if err != nil {
			log.Printf("Error collecting services inventory: %v", err)
		} else if len(services) > 0 {
			if err := a.apiClient.SendServicesInventory(a.ctx, a.agentID, services); err != nil {
				log.Printf("Error sending services inventory: %v", err)
			} else {
				log.Printf("✓ Sent services inventory (%d items)", len(services))
			}
		}
	}

	a.mutex.Lock()
	a.stats.LastInventory = time.Now()
	a.mutex.Unlock()

	return nil
}

// GetStats returns agent statistics
func (a *Agent) GetStats() Stats {
	a.mutex.RLock()
	defer a.mutex.RUnlock()
	return a.stats
}
